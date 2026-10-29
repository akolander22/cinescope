"""
Plex Service — syncs your Plex movie library into CineScope's database.

LEARNING NOTE: We use the `plexapi` library which wraps Plex's HTTP API.
Plex has a full REST API — plexapi is just a nice Python wrapper around it.
You could make the raw requests yourself with httpx, but plexapi saves effort.

YOUR TASK: After reading this file, look up PlexServer in plexapi's docs:
https://python-plexapi.readthedocs.io/en/latest/
Try to understand what `server.library.section()` returns and why we
iterate `.all()` on it.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from plexapi.server import PlexServer
from plexapi.exceptions import Unauthorized, NotFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.film import Film, FilmStatus

logger = logging.getLogger(__name__)


def get_plex_server() -> Optional[PlexServer]:
    """
    Creates a PlexServer connection. Returns None if config is missing.
    
    LEARNING NOTE: We return None instead of raising an exception here
    because we want the app to start even if Plex isn't configured yet.
    Route handlers check for None and return a helpful error.
    """
    if not settings.PLEX_TOKEN:
        logger.warning("PLEX_TOKEN not configured — Plex sync disabled")
        return None
    
    try:
        server = PlexServer(settings.PLEX_URL, settings.PLEX_TOKEN)
        logger.info(f"Connected to Plex: {server.friendlyName}")
        return server
    except Unauthorized:
        logger.error("Plex auth failed — check your PLEX_TOKEN")
        return None
    except Exception as e:
        logger.error(f"Could not connect to Plex at {settings.PLEX_URL}: {e}")
        return None


# ── Sync state ───────────────────────────────────────────────
# One sync at a time. The API reads this for GET /api/library/sync/status.
sync_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "last_result": None,
    "error": None,
}
_sync_lock = asyncio.Lock()


def _fetch_plex_movies() -> list[dict]:
    """
    Reads the whole Plex movie library. Runs in a worker thread.

    LEARNING NOTE: plexapi uses `requests`, which blocks. Calling it directly
    from an async function freezes the event loop, so every other request
    waits until Plex answers. asyncio.to_thread runs this in a thread instead.
    """
    server = get_plex_server()
    if not server:
        raise ValueError("Plex server not available")

    section = server.library.section(settings.PLEX_MOVIE_LIBRARY)
    if not section:
        raise ValueError("Plex movie library not found")

    movies = []
    for plex_movie in section.all():
        tmdb_id, imdb_id = _extract_external_ids(plex_movie)
        movies.append({
            "plex_key": str(plex_movie.ratingKey),
            "title": plex_movie.title,
            "year": plex_movie.year,
            "tmdb_id": tmdb_id,
            "imdb_id": imdb_id,
        })
    return movies


async def sync_plex_library(db: AsyncSession, movies: Optional[list[dict]] = None) -> dict:
    """
    Pulls all movies from your Plex library and upserts them into our DB.

    "Upsert" = insert if new, update if already exists.
    We match on plex_key (Plex's internal ID), then IMDb ID, then TMDB ID.
    Films we had marked in_plex that Plex no longer lists are marked as
    removed (in_plex = False, status = dismissed so they aren't re-suggested).

    `movies` can be passed in (tests do this); otherwise Plex is read in a thread.
    Returns a summary dict with counts so the API can report back.
    """
    if movies is None:
        movies = await asyncio.to_thread(_fetch_plex_movies)

    new_count = 0
    updated_count = 0
    seen_keys = set()

    for movie in movies:
        seen_keys.add(movie["plex_key"])
        tmdb_id, imdb_id = movie["tmdb_id"], movie["imdb_id"]

        result = await db.execute(select(Film).where(Film.plex_key == movie["plex_key"]))
        existing_film = result.scalar_one_or_none()

        if not existing_film and imdb_id:
            result = await db.execute(select(Film).where(Film.imdb_id == imdb_id))
            existing_film = result.scalar_one_or_none()

        if not existing_film and tmdb_id:
            result = await db.execute(select(Film).where(Film.tmdb_id == tmdb_id))
            existing_film = result.scalar_one_or_none()

        if existing_film:
            existing_film.title = movie["title"]
            existing_film.year = movie["year"]
            existing_film.imdb_id = imdb_id or existing_film.imdb_id
            existing_film.tmdb_id = tmdb_id or existing_film.tmdb_id
            existing_film.in_plex = True
            existing_film.plex_key = movie["plex_key"]
            # A suggested/queued/added film that is now in Plex is owned
            existing_film.status = FilmStatus.owned
            updated_count += 1
        else:
            db.add(Film(
                title=movie["title"],
                year=movie["year"],
                plex_key=movie["plex_key"],
                in_plex=True,
                status=FilmStatus.owned,
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
            ))
            new_count += 1

    # An empty result is far more likely a Plex hiccup than an empty library,
    # so only mark films as removed when Plex returned something
    removed_count = 0
    if movies:
        result = await db.execute(select(Film).where(Film.in_plex == True))  # noqa: E712
        for film in result.scalars().all():
            if film.plex_key not in seen_keys:
                film.in_plex = False
                film.status = FilmStatus.dismissed
                removed_count += 1

    await db.commit()
    return {"synced": len(movies), "new": new_count, "updated": updated_count, "removed": removed_count}


async def run_plex_sync() -> dict:
    """
    Scheduler/API entry point: opens its own session and records progress in
    sync_state. Returns the summary, or {"skipped": True} if one is running.
    """
    if _sync_lock.locked():
        return {"skipped": True}

    async with _sync_lock:
        sync_state.update(running=True, started_at=datetime.now(timezone.utc), error=None)
        try:
            async with AsyncSessionLocal() as db:
                result = await sync_plex_library(db)
            sync_state["last_result"] = result
            logger.info(f"✅ Plex sync: {result}")
            return result
        except Exception as e:
            sync_state["error"] = str(e)
            logger.error(f"Plex sync failed: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            sync_state.update(running=False, finished_at=datetime.now(timezone.utc))


def _extract_external_ids(plex_movie) -> tuple[Optional[int], Optional[str]]:
    """
    Extracts TMDB and IMDB IDs from a Plex movie's guids list.
    
    Plex stores these as strings like "tmdb://123456" and "imdb://tt1234567".
    We need to parse out just the numeric/string part.
    
    LEARNING NOTE: This is already implemented as a helper for you to study.
    Notice how we iterate and check prefixes — this is a common pattern when
    dealing with external APIs that return IDs in inconsistent formats.
    """
    tmdb_id = None
    imdb_id = None

    for guid in plex_movie.guids:
        guid_str = str(guid.id)
        if guid_str.startswith("tmdb://"):
            try:
                tmdb_id = int(guid_str.replace("tmdb://", ""))
            except ValueError:
                pass
        elif guid_str.startswith("imdb://"):
            imdb_id = guid_str.replace("imdb://", "")

    return tmdb_id, imdb_id


async def get_library_stats(db: AsyncSession) -> dict:
    """Returns high-level counts for the library dashboard."""
    total = await db.execute(select(Film).where(Film.in_plex == True))  # noqa: E712
    total_count = len(total.scalars().all())
    return {
        "total_films": total_count,
        "source": settings.PLEX_URL,
        "library_name": settings.PLEX_MOVIE_LIBRARY,
    }
