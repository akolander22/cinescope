"""
Discovery Scrapers

LEARNING NOTE: We use an abstract base class (BaseScraper) to enforce
a consistent interface across all scrapers. Every scraper MUST implement
`fetch()` — if it doesn't, Python raises a TypeError at runtime.

This is the "Strategy pattern": the scheduler doesn't care which scraper
it's running, it just calls scraper.fetch() and gets back a list of dicts.

We use `httpx` for async HTTP and `beautifulsoup4` for HTML parsing.
"""

import httpx
import logging
from abc import ABC, abstractmethod
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Base class — all scrapers inherit from this
# ─────────────────────────────────────────────────────────────

class BaseScraper(ABC):
    """
    Abstract base class for all discovery scrapers.
    
    Each scraper returns a list of film dicts with this shape:
    {
        "title": str,
        "year": int | None,
        "imdb_id": str | None,    # "tt1234567"
        "tmdb_id": int | None,
        "score": float,           # 0-100, normalized from source
        "notes": str,             # Human-readable blurb
        "tags": list[str],        # e.g. ["Festival Pick", "A24"]
    }
    """

    source_type: str = ""  # Must be set by subclass, matches Source.source_type in DB

    @abstractmethod
    async def fetch(self) -> list[dict]:
        """Fetch films from this source. Must be implemented by subclass."""
        ...

    async def _get(self, url: str, headers: dict = None) -> Optional[str]:
        """
        Shared HTTP GET helper with error handling and a browser User-Agent.
        
        LEARNING NOTE: Many sites block requests with the default Python 
        user-agent. We pretend to be Chrome. For more serious scraping
        you'd rotate user agents or use a headless browser.
        """
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if headers:
            default_headers.update(headers)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url, headers=default_headers)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} fetching {url}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Letterboxd scraper (implemented — study this one)
# ─────────────────────────────────────────────────────────────

class LetterboxdScraper(BaseScraper):
    """
    Scrapes Letterboxd's popular films list.
    
    LEARNING NOTE: Letterboxd doesn't have a public API, so we scrape HTML.
    BeautifulSoup parses the HTML and lets us query it like a DOM.
    This is the most fragile approach — if Letterboxd changes their HTML
    structure, the scraper breaks. That's normal for web scraping.
    
    Study this implementation, then use it as a template for IMDbScraper below.
    """

    source_type = "letterboxd"
    URL = "https://letterboxd.com/films/popular/"

    async def fetch(self) -> list[dict]:
        html = await self._get(self.URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        films = []

        # Letterboxd renders films as <li class="poster-container"> elements
        # Each contains a <div data-film-name="..." data-film-year="...">
        poster_containers = soup.select("li.poster-container")
        
        for i, container in enumerate(poster_containers[:25]):  # Top 25
            film_div = container.select_one("div[data-film-name]")
            if not film_div:
                continue

            title = film_div.get("data-film-name", "").strip()
            year_str = film_div.get("data-film-year", "")
            
            if not title:
                continue

            try:
                year = int(year_str) if year_str else None
            except ValueError:
                year = None

            # Score = inverted rank (position 1 = score 100, position 25 = score 76)
            score = max(100 - i * (100 / 25), 50)

            films.append({
                "title": title,
                "year": year,
                "imdb_id": None,  # Letterboxd doesn't expose this in list view
                "tmdb_id": None,
                "score": round(score, 1),
                "notes": f"Ranked #{i+1} on Letterboxd Popular",
                "tags": ["Letterboxd Popular"],
            })

        logger.info(f"Letterboxd: found {len(films)} films")
        return films


# ─────────────────────────────────────────────────────────────
# IMDb scraper — scrapes the "Most Popular Movies" list
# ─────────────────────────────────────────────────────────────

class IMDbTrendingScraper(BaseScraper):
    """
    Scrapes IMDb's popularity chart or "Most Popular Movies" list.
    """

    source_type = "imdb"
    URL = "https://www.imdb.com/chart/moviemeter/"

    async def fetch(self) -> list[dict]:
        page = await self._get(self.URL)
        if not page:
            return []

        soup = BeautifulSoup(page, "html.parser")
        films = []

        # Find the film list elements
        film_items = soup.select("li.ipc-metadata-list-summary-item")
        
        for i, item in enumerate(film_items[:25]):  # Top 25
            # Extract title
            title_elem = item.select_one("h3.ipc-title__text")
            title = title_elem.get_text().strip() if title_elem else None

            if not title:
                continue

            # Extract year
            year_elem = item.select_one("span.ipc-title-year")
            year_str = year_elem.get_text().strip() if year_elem else None
            try:
                year = int(year_str) if year_str else None
            except ValueError:
                year = None

            # Extract IMDb ID from the href attribute
            imdb_link = item.select_one("a[href*='/title/']")
            imdb_id = None
            if imdb_link:
                href = imdb_link.get("href", "")
                if href.startswith("/title/"):
                    imdb_id = href.split("/")[3]

            # Score = inverted rank (position 1 = score 100, position 25 = score 76)
            score = max(100 - i * (100 / 25), 50)

            films.append({
                "title": title,
                "year": year,
                "imdb_id": imdb_id,
                "tmdb_id": None,
                "score": round(score, 1),
                "notes": f"Ranked #{i+1} on IMDb Trending",
                "tags": ["IMDb Trending"],
            })

        logger.info(f"IMDb: found {len(films)} films")
        return films


# ─────────────────────────────────────────────────────────────
# Metacritic scraper — stubbed, implement after IMDb
# ─────────────────────────────────────────────────────────────

class MetacriticScraper(BaseScraper):
    """
    Gets high-scoring new releases from Metacritic.
    Metacritic scores are Metascores (0-100) from professional critics.
    These are already 0-100 so no normalization needed.
    
    YOUR TASK (Phase 2): Implement after IMDb scraper is working.
    URL to scrape: https://www.metacritic.com/browse/movies/score/metascore/year/
    """

    source_type = "metacritic"

    async def fetch(self) -> list[dict]:
        page = await self._get("https://www.metacritic.com/browse/movies/score/metascore/year/")
        if not page:
            return []   
        
        films = []



# ─────────────────────────────────────────────────────────────
# Scraper registry — maps source_type strings to scraper classes
# ─────────────────────────────────────────────────────────────

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "letterboxd": LetterboxdScraper,
    "imdb": IMDbTrendingScraper,
    "metacritic": MetacriticScraper,
}


def get_scraper(source_type: str) -> Optional[BaseScraper]:
    """Returns an instantiated scraper for the given source_type, or None."""
    scraper_class = SCRAPER_REGISTRY.get(source_type)
    if not scraper_class:
        logger.warning(f"No scraper registered for source_type='{source_type}'")
        return None
    return scraper_class()
