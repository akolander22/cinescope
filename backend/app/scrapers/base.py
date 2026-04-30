"""
Discovery Scrapers — TMDB API based

TMDB API docs: https://developer.themoviedb.org/docs
We use the Read Access Token (Bearer auth) instead of scraping HTML.
This is far more reliable than scraping and gives us clean structured data
including TMDB IDs that match perfectly with Plex and Radarr.
"""

import httpx
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"


class BaseScraper(ABC):
    """
    Abstract base class for all discovery scrapers.
    Returns a list of film dicts with this shape:
    {
        "title": str,
        "year": int | None,
        "imdb_id": str | None,
        "tmdb_id": int | None,
        "score": float,       # 0-100
        "notes": str,
        "tags": list[str],
        "overview": str | None,
        "poster_path": str | None,
        "tmdb_score": float | None,
    }
    """
    source_type: str = ""

    @abstractmethod
    async def fetch(self) -> list[dict]:
        ...

    async def _tmdb_get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """
        Authenticated GET to TMDB API.
        Uses Bearer token auth — much cleaner than API key in query params.
        """
        if not settings.TMDB_API_TOKEN:
            logger.error("TMDB_API_TOKEN not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{TMDB_BASE}{endpoint}",
                    headers={
                        "Authorization": f"Bearer {settings.TMDB_API_TOKEN}",
                        "Accept": "application/json",
                    },
                    params=params or {},
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching TMDB {endpoint}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} from TMDB {endpoint}")
        except Exception as e:
            logger.error(f"TMDB request failed: {e}")
        return None

    def _parse_movie(self, movie: dict, rank: int, notes: str, tags: list[str]) -> dict:
        """
        Converts a raw TMDB movie dict into our standard film dict shape.
        TMDB vote_average is 0-10, we convert to 0-100.
        """
        year = None
        release = movie.get("release_date", "")
        if release and len(release) >= 4:
            try:
                year = int(release[:4])
            except ValueError:
                pass

        return {
            "title": movie.get("title", ""),
            "year": year,
            "tmdb_id": movie.get("id"),
            "imdb_id": None,  # Not in list endpoints, fetched separately if needed
            "score": round(min(movie.get("vote_average", 0) * 10, 100), 1),
            "overview": movie.get("overview", ""),
            "poster_path": movie.get("poster_path", ""),
            "tmdb_score": movie.get("vote_average"),
            "notes": notes,
            "tags": tags,
        }


class TMDBTrendingScraper(BaseScraper):
    """Films trending on TMDB this week."""
    source_type = "tmdb_trending"

    async def fetch(self) -> list[dict]:
        data = await self._tmdb_get("/trending/movie/week")
        if not data:
            return []

        films = []
        for i, movie in enumerate(data.get("results", [])[:25]):
            films.append(self._parse_movie(
                movie,
                rank=i + 1,
                notes=f"Trending #{i+1} on TMDB this week",
                tags=["TMDB Trending"],
            ))

        logger.info(f"TMDB Trending: found {len(films)} films")
        return films


class TMDBUpcomingScraper(BaseScraper):
    """Upcoming releases from TMDB."""
    source_type = "tmdb_upcoming"

    async def fetch(self) -> list[dict]:
        data = await self._tmdb_get("/movie/upcoming", {"region": "US"})
        if not data:
            return []

        films = []
        for i, movie in enumerate(data.get("results", [])[:25]):
            films.append(self._parse_movie(
                movie,
                rank=i + 1,
                notes=f"Upcoming release — {movie.get('release_date', 'TBD')}",
                tags=["Upcoming"],
            ))

        logger.info(f"TMDB Upcoming: found {len(films)} films")
        return films


class TMDBTopRatedScraper(BaseScraper):
    """Top rated films on TMDB — good for filling gaps in your library."""
    source_type = "tmdb_top_rated"

    async def fetch(self) -> list[dict]:
        data = await self._tmdb_get("/movie/top_rated")
        if not data:
            return []

        films = []
        for i, movie in enumerate(data.get("results", [])[:25]):
            films.append(self._parse_movie(
                movie,
                rank=i + 1,
                notes=f"TMDB Top Rated #{i+1} — {movie.get('vote_count', 0):,} votes",
                tags=["Top Rated"],
            ))

        logger.info(f"TMDB Top Rated: found {len(films)} films")
        return films


SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "tmdb_trending": TMDBTrendingScraper,
    "tmdb_upcoming": TMDBUpcomingScraper,
    "tmdb_top_rated": TMDBTopRatedScraper,
}


def get_scraper(source_type: str) -> Optional[BaseScraper]:
    scraper_class = SCRAPER_REGISTRY.get(source_type)
    if not scraper_class:
        logger.warning(f"No scraper registered for source_type='{source_type}'")
        return None
    return scraper_class()