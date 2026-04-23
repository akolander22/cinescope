"""
Database setup using SQLAlchemy with async support.

LEARNING NOTE: We use async SQLAlchemy so database queries don't block
the entire server while waiting for disk I/O. FastAPI is built around
async/await — using sync DB calls would kill your concurrency benefits.

SQLite is fine for a personal Unraid app. If you ever need multi-user
or heavy concurrent writes, swap to PostgreSQL — the SQLAlchemy layer
makes that a one-line change in config.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """
    All your database models inherit from this.
    SQLAlchemy uses this to know which classes map to DB tables.
    """
    pass


# The engine is the low-level DB connection. echo=True logs all SQL — useful
# while learning, turn off in production.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    connect_args={"check_same_thread": False},  # Required for SQLite
)

# Session factory — you call this to get a DB session in your route handlers
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keeps objects usable after commit
)


async def init_db():
    """
    Creates all tables on startup if they don't exist.
    
    LEARNING NOTE: In a bigger project you'd use Alembic for migrations
    (versioned schema changes). For now, create_all is fine — it's 
    idempotent (safe to run multiple times).
    """
    # Import models here so Base knows about them before create_all
    from app.models import film, source, suggestion  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")


async def get_db():
    """
    Dependency injected into route handlers to provide a DB session.
    
    LEARNING NOTE: The `async with` / `yield` pattern ensures the session
    is always closed after the request, even if an exception occurs.
    FastAPI's `Depends()` system calls this automatically.
    
    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
