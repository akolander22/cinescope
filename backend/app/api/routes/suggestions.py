"""
Suggestions Routes — /api/suggestions

The "inbox" of discovered films waiting for user action.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.film import Film, FilmStatus
from app.models.source import Suggestion

router = APIRouter()


class SuggestionOut(BaseModel):
    id: int
    film_id: int
    title: str
    year: Optional[int]
    genre: Optional[str]
    overview: Optional[str]
    poster_path: Optional[str]
    tmdb_score: Optional[float]
    composite_score: Optional[float]
    tags: Optional[str]
    notes: Optional[str]
    source_name: str
    status: str
    discovered_at: datetime

    class Config:
        from_attributes = True


class ActionRequest(BaseModel):
    action: str  # "queue" | "dismiss"


@router.get("/", response_model=list[SuggestionOut])
async def get_suggestions(
    db: AsyncSession = Depends(get_db),
    min_score: float = 0,
    limit: int = 50,
):
    """
    Returns unactioned suggestions (films pending your review).
    
    LEARNING NOTE: `selectinload` eagerly loads the related film and source
    objects in a single extra query — avoids the "N+1 query problem" where
    you'd fire a separate DB query for each row to get related data.
    """
    result = await db.execute(
        select(Suggestion)
        .join(Suggestion.film)
        .options(selectinload(Suggestion.film), selectinload(Suggestion.source))
        .where(
            Suggestion.user_action == None,  # noqa: E711
            Suggestion.composite_score >= min_score,
            # Hide films you already own, queued, dismissed or sent to Radarr
            Film.status == FilmStatus.suggested,
        )
        .order_by(Suggestion.composite_score.desc())
        .limit(limit)
    )
    suggestions = result.scalars().all()

    # Flatten into response shape
    return [
        SuggestionOut(
            id=s.id,
            film_id=s.film_id,
            title=s.film.title,
            year=s.film.year,
            genre=s.film.genre,
            overview=s.film.overview,
            poster_path=s.film.poster_path,
            tmdb_score=s.film.tmdb_score,
            composite_score=s.composite_score,
            tags=s.tags,
            notes=s.notes,
            source_name=s.source.name,
            status=s.film.status,
            discovered_at=s.discovered_at,
        )
        for s in suggestions
        if s.film and s.source
    ]


@router.post("/{suggestion_id}/action")
async def action_suggestion(
    suggestion_id: int,
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Records a user action (queue/dismiss) on a suggestion and moves the film
    to queued or dismissed.

    LEARNING NOTE: Async SQLAlchemy can't lazy-load `suggestion.film` — touching
    an unloaded relationship raises MissingGreenlet — so the film is loaded up
    front with selectinload.
    """
    if body.action not in ("queue", "dismiss"):
        raise HTTPException(status_code=400, detail="action must be 'queue' or 'dismiss'")

    result = await db.execute(
        select(Suggestion)
        .options(selectinload(Suggestion.film))
        .where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    now = datetime.now(timezone.utc)
    user_action = "queued" if body.action == "queue" else "dismissed"

    # Mark every pending suggestion for this film, so it doesn't come back
    # in the inbox from another source
    await db.execute(
        update(Suggestion)
        .where(Suggestion.film_id == suggestion.film_id, Suggestion.user_action == None)  # noqa: E711
        .values(user_action=user_action, actioned_at=now)
    )
    suggestion.film.status = FilmStatus.queued if body.action == "queue" else FilmStatus.dismissed

    await db.commit()
    return {"success": True, "action": body.action}
