"""Queue Routes — /api/queue"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.film import Film, FilmStatus
from app.services.radarr_service import add_to_radarr

router = APIRouter()


class FilmOut(BaseModel):
    id: int
    title: str
    year: Optional[int]
    genre: Optional[str]
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
    Sends a queued film to Radarr.
    
    YOUR TASK: Once add_to_radarr() is implemented in radarr_service.py,
    this will work end-to-end. For now it returns 501.
    """
    film = await db.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    if film.status != FilmStatus.queued:
        raise HTTPException(status_code=400, detail="Film must be in queued status")

    try:
        result = await add_to_radarr(film)
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
