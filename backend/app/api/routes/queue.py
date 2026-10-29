"""Queue Routes — /api/queue"""

import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.film import Film, FilmStatus
from app.models.app_setting import get_setting
from app.services.radarr_service import (
    add_to_radarr, resolve_radarr_target, QUALITY_PROFILE_KEY, ROOT_FOLDER_KEY,
)

router = APIRouter()


class FilmOut(BaseModel):
    id: int
    title: str
    year: Optional[int]
    genre: Optional[str]
    overview: Optional[str]
    poster_path: Optional[str]
    tmdb_id: Optional[int]
    status: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[FilmOut])
async def get_queue(db: AsyncSession = Depends(get_db)):
    """Returns all films approved (queued) but not yet sent to Radarr."""
    result = await db.execute(
        select(Film)
        .where(Film.status == FilmStatus.queued)
        .order_by(Film.title)
    )
    return result.scalars().all()


@router.post("/{film_id}/send-to-radarr")
async def send_to_radarr(film_id: int, db: AsyncSession = Depends(get_db)):
    """
    Sends a queued film to Radarr, using the quality profile and root folder
    picked on the Sources page (or Radarr's first ones if none is saved).
    """
    film = await db.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    if film.status != FilmStatus.queued:
        raise HTTPException(status_code=400, detail="Film must be in queued status")

    if not film.tmdb_id:
        raise HTTPException(status_code=400, detail=f"'{film.title}' has no TMDB ID, so Radarr can't identify it")

    try:
        saved_profile = await get_setting(db, QUALITY_PROFILE_KEY)
        profile_id, root_folder = await resolve_radarr_target(
            int(saved_profile) if saved_profile else None,
            await get_setting(db, ROOT_FOLDER_KEY),
        )
        result = await add_to_radarr(film, profile_id, root_folder)
        if result.get("success"):
            film.status = FilmStatus.added
            await db.commit()
            return {"success": True, "message": f"'{film.title}' added to Radarr"}
        else:
            return {"success": False, "reason": result.get("reason")}
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Radarr integration not yet implemented — see services/radarr_service.py"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Radarr request failed: {e}")
