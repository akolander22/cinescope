"""
Library Routes — /api/library

LEARNING NOTE: FastAPI routes use type annotations for automatic
validation and documentation. If you declare `db: AsyncSession = Depends(get_db)`,
FastAPI automatically injects the DB session. If validation fails
(wrong type, missing field), FastAPI returns a 422 automatically.

Visit http://localhost:8000/docs when running — FastAPI generates
interactive Swagger docs from your routes automatically.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.film import Film, FilmStatus
from app.core.config import settings
from app.services.plex_service import run_plex_sync, sync_state, get_library_stats
from app.services.metadata_service import backfill_metadata

router = APIRouter()

# Keep a reference to running tasks so they aren't garbage-collected mid-sync
_background_tasks: set = set()


# ── Response schemas (Pydantic models) ──────────────────────
# LEARNING NOTE: These define what the API returns. Pydantic validates
# that your DB objects match the shape before sending to client.

class FilmOut(BaseModel):
    id: int
    title: str
    year: Optional[int]
    genre: Optional[str]
    overview: Optional[str]
    poster_path: Optional[str]
    status: str
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    in_plex: bool
    tmdb_score: Optional[float]

    class Config:
        from_attributes = True  # Allows creating from SQLAlchemy models


# ── Routes ──────────────────────────────────────────────────

@router.get("/", response_model=list[FilmOut])
async def get_library(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    """Returns all films currently in your Plex library."""
    result = await db.execute(
        select(Film)
        .where(Film.in_plex == True)  # noqa: E712
        .order_by(Film.title)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """High-level library stats for the dashboard."""
    return await get_library_stats(db)


@router.post("/sync", status_code=202)
async def trigger_sync():
    """
    Starts a Plex library sync and returns immediately.

    LEARNING NOTE: The sync reads Plex in a worker thread and runs as its own
    asyncio task, so the API stays responsive while it works. Poll
    GET /api/library/sync/status to see when it finishes.
    """
    if sync_state["running"]:
        return {"started": False, "running": True}
    if not settings.PLEX_TOKEN:
        raise HTTPException(status_code=400, detail="PLEX_TOKEN not configured")
    task = asyncio.create_task(run_plex_sync())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"started": True, "running": True}


@router.get("/sync/status")
async def get_sync_status():
    """Whether a sync is running, and the result of the last one."""
    return sync_state


@router.post("/backfill-metadata")
async def trigger_backfill(background_tasks: BackgroundTasks):
    """Looks up posters, overviews and TMDB scores for films missing them."""
    background_tasks.add_task(backfill_metadata)
    return {"started": True}


@router.get("/{film_id}", response_model=FilmOut)
async def get_film(film_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single film by its CineScope ID."""
    film = await db.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    return film
