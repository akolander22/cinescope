"""Sources Routes — /api/sources"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.services.plex_service import get_plex_server
from app.db.database import get_db
from app.models.source import Source
from app.models.app_setting import get_setting, set_setting
from app.services.radarr_service import (
    check_radarr_connection, get_quality_profiles, get_root_folders,
    QUALITY_PROFILE_KEY, ROOT_FOLDER_KEY,
)

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


class RadarrSettings(BaseModel):
    quality_profile_id: int
    root_folder: str


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


@router.get("/radarr/options")
async def radarr_options(db: AsyncSession = Depends(get_db)):
    """Radarr's quality profiles and root folders, plus the saved choice."""
    try:
        profiles = await get_quality_profiles()
        folders = await get_root_folders()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Radarr: {e}")

    saved_profile = await get_setting(db, QUALITY_PROFILE_KEY)
    return {
        "quality_profiles": profiles,
        "root_folders": folders,
        "selected": {
            "quality_profile_id": int(saved_profile) if saved_profile else None,
            "root_folder": await get_setting(db, ROOT_FOLDER_KEY),
        },
    }


@router.put("/radarr/settings")
async def save_radarr_settings(body: RadarrSettings, db: AsyncSession = Depends(get_db)):
    """Saves the quality profile and root folder used for Send to Radarr."""
    try:
        valid_profiles = {p["id"] for p in await get_quality_profiles()}
        valid_folders = {f["path"] for f in await get_root_folders()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Radarr: {e}")

    if body.quality_profile_id not in valid_profiles:
        raise HTTPException(status_code=400, detail="Unknown quality profile")
    if body.root_folder not in valid_folders:
        raise HTTPException(status_code=400, detail="Unknown root folder")

    await set_setting(db, QUALITY_PROFILE_KEY, body.quality_profile_id)
    await set_setting(db, ROOT_FOLDER_KEY, body.root_folder)
    await db.commit()
    return {"quality_profile_id": body.quality_profile_id, "root_folder": body.root_folder}
