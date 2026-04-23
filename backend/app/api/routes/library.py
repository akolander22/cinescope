"""
Library Routes — /api/library

LEARNING NOTE: FastAPI routes use type annotations for automatic
validation and documentation. If you declare `db: AsyncSession = Depends(get_db)`,
FastAPI automatically injects the DB session. If validation fails
(wrong type, missing field), FastAPI returns a 422 automatically.

Visit http://localhost:8000/docs when running — FastAPI generates
interactive Swagger docs from your routes automatically.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.film import Film, FilmStatus
from app.services.plex_service import sync_plex_library, get_library_stats

router = APIRouter()


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


class SyncResult(BaseModel):
    synced: int
    new: int
    updated: int
    message: str


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


@router.post("/sync", response_model=SyncResult)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers a Plex library sync.
    
    LEARNING NOTE: We use BackgroundTasks to run the sync after the HTTP
    response is sent. This way the client gets an immediate "sync started"
    response rather than waiting potentially minutes for Plex to respond.
    
    For a large library, you'd want to report progress via WebSockets or
    polling a /sync/status endpoint — good Phase 2 feature.
    
    YOUR TASK: Once you implement sync_plex_library(), uncomment the 
    background_tasks line and remove the NotImplementedError handling.
    """
    try:
        # Once implemented, this runs in the background:
        # background_tasks.add_task(sync_plex_library, db)
        result = await sync_plex_library(db)
        return SyncResult(
            **result,
            message=f"Sync complete — {result['new']} new films added"
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Plex sync not yet implemented — see services/plex_service.py"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{film_id}", response_model=FilmOut)
async def get_film(film_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single film by its CineScope ID."""
    film = await db.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    return film
