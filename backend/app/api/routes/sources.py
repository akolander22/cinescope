"""Sources Routes — /api/sources"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.services.plex_service import get_plex_server
from app.db.database import get_db
from app.models.source import Source
from app.services.radarr_service import check_radarr_connection

router = APIRouter()


class SourceOut(BaseModel):
    id: int
    name: str
    source_type: str
    is_active: bool
    interval_hours: int
    description: Optional[str]
    last_polled_at: Optional[str]

    class Config:
        from_attributes = True


class SourceToggle(BaseModel):
    is_active: bool


@router.get("/", response_model=list[SourceOut])
async def get_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.patch("/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    body: SourceToggle,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a discovery source."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.is_active = body.is_active
    await db.commit()
    return {"id": source_id, "is_active": source.is_active}


@router.get("/integrations/status")
async def integration_status():
    radarr_ok = await check_radarr_connection()
    plex_server = get_plex_server()
    return {
        "radarr": {"connected": radarr_ok},
        "plex": {"connected": plex_server is not None},
    }
