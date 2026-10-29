"""
App settings — small key/value store for choices made in the UI.

LEARNING NOTE: Env vars are good for secrets and things you set once at
deploy time. Choices you change from the browser (like which Radarr quality
profile to use) need to live in the database instead.
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


async def get_setting(db: AsyncSession, key: str):
    row = await db.get(AppSetting, key)
    return row.value if row else None


async def set_setting(db: AsyncSession, key: str, value) -> None:
    row = await db.get(AppSetting, key)
    if row:
        row.value = None if value is None else str(value)
    else:
        db.add(AppSetting(key=key, value=None if value is None else str(value)))
