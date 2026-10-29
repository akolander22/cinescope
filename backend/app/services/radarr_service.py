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

# Keys in app_settings for the profile and folder chosen on the Sources page
QUALITY_PROFILE_KEY = "radarr_quality_profile_id"
ROOT_FOLDER_KEY = "radarr_root_folder"


async def _radarr_get(path: str) -> list[dict]:
    if not settings.RADARR_API_KEY:
        raise ValueError("Radarr is not configured (RADARR_API_KEY is empty)")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.RADARR_URL}/api/v3/{path}",
            headers={"X-Api-Key": settings.RADARR_API_KEY},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def get_quality_profiles() -> list[dict]:
    """Radarr's quality profiles as [{id, name}]."""
    return [{"id": p["id"], "name": p["name"]} for p in await _radarr_get("qualityprofile")]


async def get_root_folders() -> list[dict]:
    """Radarr's root folders as [{path, free_space}]."""
    return [
        {"path": f["path"], "free_space": f.get("freeSpace")}
        for f in await _radarr_get("rootfolder")
    ]


async def resolve_radarr_target(profile_id: Optional[int], root_folder: Optional[str]) -> tuple[int, str]:
    """
    Uses the saved profile/folder when they still exist in Radarr, otherwise
    falls back to Radarr's first one, so nothing is hard-coded.
    """
    profiles = await get_quality_profiles()
    folders = await get_root_folders()
    if not profiles or not folders:
        raise ValueError("Radarr has no quality profiles or root folders configured")

    profile_ids = {p["id"] for p in profiles}
    folder_paths = {f["path"] for f in folders}
    chosen_profile = profile_id if profile_id in profile_ids else profiles[0]["id"]
    chosen_folder = root_folder if root_folder in folder_paths else folders[0]["path"]
    return chosen_profile, chosen_folder


async def add_to_radarr(film: Film, quality_profile_id: int, root_folder: str) -> dict:
    """
    Adds a film to Radarr's wanted list.

    LEARNING NOTE: Radarr needs a TMDB ID to identify the film.
    This is why we store tmdb_id in our Film model — it's the lingua franca
    between Plex, Radarr, and Sonarr.

    Returns {"success": True, "radarr_id": ...} on 201, or
    {"success": False, "reason": "already_in_radarr"}. Raises ValueError when
    the film has no TMDB ID; other HTTP errors are logged and raised.
    """
    if not film.tmdb_id:
        raise ValueError(f"'{film.title}' has no TMDB ID, so Radarr can't identify it")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.RADARR_URL}/api/v3/movie",
                headers={"X-Api-Key": settings.RADARR_API_KEY},
                json={
                    "tmdbId": film.tmdb_id,
                    "title": film.title,
                    "year": film.year,
                    "qualityProfileId": quality_profile_id,
                    "rootFolderPath": root_folder,
                    "monitored": True,
                    "addOptions": {"searchForMovie": True}
                },
                timeout=10.0,
            )
            if response.status_code == 201:
                return {"success": True, "radarr_id": response.json().get("id")}
            elif response.status_code == 400 and "already" in response.text.lower():
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
