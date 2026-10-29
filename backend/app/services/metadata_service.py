"""
Metadata Service — fills in posters, overviews and TMDB scores for films
that were saved without them.

Discovery used to drop the TMDB fields, and Plex sync never fetched them, so
most films have no poster. This backfill looks each one up on TMDB: by TMDB ID
when we have it, otherwise by title + year search.

LEARNING NOTE: It commits in batches so a crash halfway through keeps the
work done so far, and sleeps between calls to stay under TMDB's rate limit.
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy import select, or_

from app.db.database import AsyncSessionLocal
from app.models.film import Film
from app.scrapers.base import tmdb_get
from app.core.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
REQUEST_DELAY = 0.1  # seconds between TMDB calls


async def _find_tmdb_id(film: Film):
    params = {"query": film.title}
    if film.year:
        params["year"] = film.year
    data = await tmdb_get("/search/movie", params)
    results = (data or {}).get("results") or []
    return results[0]["id"] if results else None


def apply_tmdb_details(film: Film, details: dict) -> None:
    """Copies TMDB /movie/{id} fields onto a film without overwriting real data."""
    film.tmdb_id = film.tmdb_id or details.get("id")
    film.poster_path = film.poster_path or details.get("poster_path")
    film.overview = film.overview or details.get("overview")
    if details.get("vote_average") is not None:
        film.tmdb_score = details["vote_average"]
    if not film.genre and details.get("genres"):
        film.genre = ",".join(g["name"] for g in details["genres"])
    film.runtime_minutes = film.runtime_minutes or details.get("runtime")
    if not film.imdb_id and details.get("imdb_id"):
        film.imdb_id = details["imdb_id"]


async def _id_taken(db, film: Film, column, value) -> bool:
    """tmdb_id and imdb_id are unique, so check another row doesn't hold the value."""
    if not value:
        return False
    return (await db.execute(select(Film.id).where(Film.id != film.id, column == value))).first() is not None


async def backfill_metadata(limit: Optional[int] = None) -> dict:
    """Looks up every film missing a poster or overview. Returns counts."""
    if not settings.TMDB_API_TOKEN:
        logger.warning("TMDB_API_TOKEN not set — skipping metadata backfill")
        return {"checked": 0, "updated": 0, "not_found": 0}

    checked = updated = not_found = 0
    async with AsyncSessionLocal() as db:
        query = select(Film).where(or_(Film.poster_path == None, Film.poster_path == ""))  # noqa: E711
        if limit:
            query = query.limit(limit)
        films = (await db.execute(query)).scalars().all()
        logger.info(f"🖼  Metadata backfill: {len(films)} films missing posters")

        for film in films:
            checked += 1
            tmdb_id = film.tmdb_id or await _find_tmdb_id(film)
            details = await tmdb_get(f"/movie/{tmdb_id}") if tmdb_id else None

            if details and not film.tmdb_id and await _id_taken(db, film, Film.tmdb_id, details.get("id")):
                details = None  # search matched a film we already have under another row
            if details:
                if await _id_taken(db, film, Film.imdb_id, details.get("imdb_id")):
                    details = {**details, "imdb_id": None}
                apply_tmdb_details(film, details)
                updated += 1
            else:
                not_found += 1

            if checked % BATCH_SIZE == 0:
                await db.commit()
                logger.info(f"  backfill: {checked}/{len(films)} checked, {updated} updated")
            await asyncio.sleep(REQUEST_DELAY)

        await db.commit()

    logger.info(f"✅ Metadata backfill done: {updated} updated, {not_found} not found")
    return {"checked": checked, "updated": updated, "not_found": not_found}
