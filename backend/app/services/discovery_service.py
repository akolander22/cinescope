"""
Discovery Service — orchestrates all scrapers and saves results to DB.

This is the "glue" between scrapers (which fetch raw data) and the DB
(which stores structured records). It also handles deduplication and
scoring so the same film from 3 sources merges into one suggestion.

LEARNING NOTE: Services are where business logic lives. Routes handle
HTTP in/out. Models define data shape. Services do the actual work.
This separation makes code easier to test and reuse.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.film import Film, FilmStatus
from app.models.source import Source, Suggestion
from app.scrapers.base import get_scraper

logger = logging.getLogger(__name__)


async def run_discovery():
    """
    Main entry point called by the scheduler.
    Opens its own DB session (since scheduler runs outside request context).
    """
    logger.info("🔍 Starting discovery run...")
    async with AsyncSessionLocal() as db:
        try:
            await _run_discovery_with_db(db)
            await db.commit()
            logger.info("✅ Discovery run complete")
        except Exception as e:
            await db.rollback()
            logger.error(f"Discovery run failed: {e}", exc_info=True)


async def _run_discovery_with_db(db: AsyncSession):
    """Fetches active sources and runs each scraper."""
    # Get all active sources from DB
    result = await db.execute(select(Source).where(Source.is_active == True))  # noqa: E712
    active_sources = result.scalars().all()

    if not active_sources:
        logger.warning("No active sources configured — add some in the Sources tab")
        return

    for source in active_sources:
        logger.info(f"Running scraper for: {source.name}")
        await _scrape_source(db, source)


async def _scrape_source(db: AsyncSession, source: Source):
    """Runs a single scraper and saves/merges its results."""
    scraper = get_scraper(source.source_type)
    if not scraper:
        return

    try:
        raw_films = await scraper.fetch()
    except NotImplementedError:
        logger.info(f"Scraper for '{source.source_type}' not yet implemented — skipping")
        return
    except Exception as e:
        logger.error(f"Scraper {source.source_type} failed: {e}")
        return

    new_count = 0
    for film_data in raw_films:
        was_new = await _upsert_suggestion(db, source, film_data)
        if was_new:
            new_count += 1

    logger.info(f"  {source.name}: {len(raw_films)} found, {new_count} new")


async def _upsert_suggestion(db: AsyncSession, source: Source, film_data: dict) -> bool:
    """
    Finds or creates a Film, then creates a Suggestion linking it to the source.
    Returns True if this was a brand-new film (not seen before).
    
    LEARNING NOTE: This function demonstrates a key pattern — look up by
    a unique identifier (title+year when we don't have TMDB ID yet), 
    create if missing, then create the relationship record.
    
    In production you'd enrich with a TMDB API call here to get the real
    TMDB ID, poster, and metadata before saving.
    """
    title = film_data.get("title", "").strip()
    year = film_data.get("year")

    if not title:
        return False

    # Check if we already have this film (match on tmdb_id if available, else title+year)
    film = None
    tmdb_id = film_data.get("tmdb_id")
    imdb_id = film_data.get("imdb_id")

    if tmdb_id:
        result = await db.execute(select(Film).where(Film.tmdb_id == tmdb_id))
        film = result.scalar_one_or_none()
    elif imdb_id:
        result = await db.execute(select(Film).where(Film.imdb_id == imdb_id))
        film = result.scalar_one_or_none()
    
    if not film and title:
        # Fallback: match by title + year
        query = select(Film).where(Film.title == title)
        if year:
            query = query.where(Film.year == year)
        result = await db.execute(query)
        film = result.scalar_one_or_none()

    is_new = film is None

    if is_new:
        film = Film(
            title=title,
            year=year,
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            status=FilmStatus.suggested,
            in_plex=False,
        )
        db.add(film)
        await db.flush()  # Gets the auto-generated film.id without committing

    # Check if this source already has a suggestion for this film
    existing_suggestion = await db.execute(
        select(Suggestion).where(
            Suggestion.film_id == film.id,
            Suggestion.source_id == source.id,
        )
    )
    if existing_suggestion.scalar_one_or_none():
        return False  # Already suggested by this source

    # Create the suggestion
    tags = ",".join(film_data.get("tags", []))
    suggestion = Suggestion(
        film_id=film.id,
        source_id=source.id,
        raw_score=film_data.get("score", 0),
        composite_score=film_data.get("score", 0),  # TODO: weight by source reputation
        tags=tags,
        notes=film_data.get("notes", ""),
    )
    db.add(suggestion)

    return is_new


async def seed_default_sources(db: AsyncSession):
    """
    Seeds the DB with default sources if none exist.
    Called once on first startup.
    
    YOUR TASK: This is implemented — but add more sources here as you
    build more scrapers. Match source_type to SCRAPER_REGISTRY keys.
    """
    result = await db.execute(select(Source))
    if result.scalars().first():
        return  # Sources already seeded

    defaults = [
        Source(
            name="Letterboxd Popular",
            source_type="letterboxd",
            url="https://letterboxd.com/films/popular/",
            is_active=True,
            interval_hours=6,
            description="Most popular films on Letterboxd right now",
        ),
        Source(
            name="IMDb Trending",
            source_type="imdb",
            url="https://www.imdb.com/chart/moviemeter/",
            is_active=False,  # Off until you implement the scraper
            interval_hours=12,
            description="IMDb MovieMeter — popularity-ranked films",
        ),
        Source(
            name="Metacritic New Releases",
            source_type="metacritic",
            url="https://www.metacritic.com/browse/movies/score/metascore/year/",
            is_active=False,
            interval_hours=24,
            description="Critically acclaimed new releases",
        ),
    ]

    for source in defaults:
        db.add(source)
    
    await db.commit()
    logger.info(f"Seeded {len(defaults)} default sources")
