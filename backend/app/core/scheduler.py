"""
Scheduler — runs discovery scraping in the background on a timer.

LEARNING NOTE: APScheduler lets you run functions on a schedule inside
your running Python process — no separate cron job needed. We use the
AsyncIOScheduler so jobs run in the same event loop as FastAPI.

The scheduler is started in main.py's lifespan() function.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

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

    scheduler.add_job(
        run_discovery,
        trigger=IntervalTrigger(hours=settings.DISCOVERY_INTERVAL_HOURS),
        id="discovery",
        name="Film Discovery",
        replace_existing=True,
        # Run once immediately on startup so you don't wait 6 hours for first results
        # Remove `next_run_time` if you don't want that behavior
        # next_run_time=datetime.now(),  # Uncomment to run immediately on start
    )

    scheduler.start()
    logger.info(
        f"Scheduler started — discovery runs every {settings.DISCOVERY_INTERVAL_HOURS}h"
    )


def stop_scheduler():
    """Gracefully stops the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
