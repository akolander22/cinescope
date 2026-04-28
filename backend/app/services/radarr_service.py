"""
Radarr Service — sends approved films from the queue to Radarr.

LEARNING NOTE: Radarr has a well-documented REST API. We use `httpx` 
(async HTTP client) instead of `requests` because we're in an async app.
Using `requests` in an async context would block the event loop.

Radarr API docs: https://radarr.video/docs/api/
Key endpoint we care about: POST /api/v3/movie

YOUR TASK later: After the Plex sync is working, come back here and
implement `add_to_radarr()`. The docstring tells you exactly what to send.
"""

import httpx
import logging
from typing import Optional

from app.core.config import settings
from app.models.film import Film

logger = logging.getLogger(__name__)

# Radarr quality profile ID — 1 is usually "Any" which is a safe default.
# You can GET /api/v3/qualityprofile to see yours.
DEFAULT_QUALITY_PROFILE_ID = 1

# Root folder where Radarr will put downloaded movies.
# This should match what's configured in Radarr's settings.
DEFAULT_ROOT_FOLDER = "/movies"


async def add_to_radarr(film: Film) -> dict:
    """
    Adds a film to Radarr's wanted list.
    
    LEARNING NOTE: Radarr needs a TMDB ID to identify the film.
    This is why we store tmdb_id in our Film model — it's the lingua franca
    between Plex, Radarr, and Sonarr.
    
    YOUR TASK: Implement this function using httpx.AsyncClient.
    
    What to POST to {RADARR_URL}/api/v3/movie with header X-Api-Key:
    {
        "tmdbId": film.tmdb_id,
        "title": film.title,
        "year": film.year,
        "qualityProfileId": DEFAULT_QUALITY_PROFILE_ID,
        "rootFolderPath": DEFAULT_ROOT_FOLDER,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }
    
    Handle these cases:
    - film.tmdb_id is None → raise ValueError("Film has no TMDB ID")
    - HTTP 201 → success, return {"success": True, "radarr_id": response["id"]}
    - HTTP 400 with "already exists" → return {"success": False, "reason": "already_in_radarr"}
    - Other errors → log and raise
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.RADARR_URL}/api/v3/movie",
                headers={"X-Api-Key": settings.RADARR_API_KEY},
                json={
                    "tmdbId": film.tmdb_id,
                    "title": film.title,
                    "year": film.year,
                    "qualityProfileId": DEFAULT_QUALITY_PROFILE_ID,
                    "rootFolderPath": DEFAULT_ROOT_FOLDER,
                    "monitored": True,
                    "addOptions": {"searchForMovie": True}
                },
                timeout=10.0,
            )
            if response.status_code == 201:
                return {"success": True, "radarr_id": response.json().get("id")}
            elif response.status_code == 400 and "already exists" in response.text:
                return {"success": False, "reason": "already_in_radarr"}
            else:
                logger.error(f"Failed to add to Radarr: {response.status_code} {response.text}")
                response.raise_for_status()
    except Exception as e:
        logger.error(f"Error adding film '{film.title}' to Radarr: {e}")
        raise


async def check_radarr_connection() -> bool:
    """
    Pings Radarr to verify the connection and API key work.
    Useful for the /health endpoint and the Sources config UI.
    """
    if not settings.RADARR_API_KEY:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.RADARR_URL}/api/v3/system/status",
                headers={"X-Api-Key": settings.RADARR_API_KEY},
                timeout=5.0,
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Radarr connection check failed: {e}")
        return False


async def get_radarr_movies() -> list[dict]:
    """
    Fetches all movies currently in Radarr.
    Useful for cross-referencing so we don't suggest films already in Radarr.
    
    LEARNING NOTE: This is fully implemented so you can see a complete
    httpx example before you write your own in add_to_radarr().
    """
    if not settings.RADARR_API_KEY:
        return []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.RADARR_URL}/api/v3/movie",
                headers={"X-Api-Key": settings.RADARR_API_KEY},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Radarr movies: {e}")
        return []
