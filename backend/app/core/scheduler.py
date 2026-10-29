"""
Scheduler — runs discovery scraping in the background on a timer.

LEARNING NOTE: APScheduler lets you run functions on a schedule inside
your running Python process — no separate cron job needed. We use the
AsyncIOScheduler so jobs run in the same event loop as FastAPI.

The scheduler is started in main.py's lifespan() function.
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler():
    """
    Registers all background jobs and starts the scheduler.
    Called once at app startup from main.py.
    """
    # Import here to avoid circular imports
    from app.services.discovery_service import run_discovery
    from app.services.metadata_service import backfill_metadata
    from app.services.plex_service import run_plex_sync

    scheduler.add_job(
        run_discovery,
        trigger=IntervalTrigger(hours=settings.DISCOVERY_INTERVAL_HOURS),
        id="discovery",
        name="Film Discovery",
        replace_existing=True,
        next_run_time=datetime.now(),
    )

    # Posters/overviews for films saved without them. Starts a few minutes after
    # boot so the first discovery run goes first, then repeats weekly.
    scheduler.add_job(
        backfill_metadata,
        trigger=IntervalTrigger(weeks=1),
        id="metadata_backfill",
        name="TMDB Metadata Backfill",
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(minutes=3),
    )

    if settings.PLEX_SYNC_ENABLED and settings.PLEX_TOKEN:
        scheduler.add_job(
            run_plex_sync,
            trigger=CronTrigger(hour=settings.PLEX_SYNC_HOUR, minute=0),
            id="plex_sync",
            name="Plex Library Sync",
            replace_existing=True,
        )
        logger.info(f"Plex sync scheduled nightly at {settings.PLEX_SYNC_HOUR:02d}:00")

    scheduler.start()
    logger.info(
        f"Scheduler started — discovery runs every {settings.DISCOVERY_INTERVAL_HOURS}h"
    )


def stop_scheduler():
    """Gracefully stops the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
