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

import logging
from typing import Optional
from plexapi.server import PlexServer
from plexapi.exceptions import Unauthorized, NotFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
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


async def sync_plex_library(db: AsyncSession) -> dict:
    """
    Pulls all movies from your Plex library and upserts them into our DB.
    
    "Upsert" = insert if new, update if already exists.
    We match on plex_key (Plex's internal ID) to avoid duplicates.

    Returns a summary dict with counts so the API can report back.
    
    YOUR TASK: This function is stubbed out below. 
    Using the plexapi docs and the Film model above, implement the body:
    
    1. Call get_plex_server() — handle None case
    2. Get the movie library section by name (settings.PLEX_MOVIE_LIBRARY)  
    3. Iterate over all movies with section.all()
    4. For each Plex movie, check if a Film with that plex_key already exists in DB
    5. If it exists → update title/year (it might have been corrected in Plex)
    6. If it doesn't exist → create a new Film with status=FilmStatus.owned, in_plex=True
    7. Commit and return {"synced": count, "new": new_count, "updated": updated_count}
    
    HINTS:
    - A Plex movie object has: .title, .year, .ratingKey, .summary, .duration
    - .genres returns a list of Genre objects — do [g.tag for g in movie.genres]
    - .guids returns external IDs — look for "imdb://" and "tmdb://" prefixes
    - Use `await db.execute(select(Film).where(Film.plex_key == str(movie.ratingKey)))`
      then `.scalar_one_or_none()` to check existence
    """
    # TODO: Implement this function
    # Remove the raise and write your implementation
    raise NotImplementedError("YOUR TASK: Implement sync_plex_library() — see docstring above")


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
