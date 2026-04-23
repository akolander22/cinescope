"""
CineScope - Media Intelligence Backend
Entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import init_db
from app.api.routes import library, suggestions, sources, queue
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    
    LEARNING NOTE: This is FastAPI's modern way to run code on startup/shutdown.
    The code before `yield` runs on startup, code after runs on shutdown.
    We use this to initialize our DB and start the background scheduler.
    """
    print("🎬 CineScope starting up...")
    await init_db()
    start_scheduler()
    yield
    print("🎬 CineScope shutting down...")
    stop_scheduler()


app = FastAPI(
    title="CineScope",
    description="Media intelligence — library monitoring and film discovery",
    version="0.1.0",
    lifespan=lifespan,
)

# LEARNING NOTE: CORS (Cross-Origin Resource Sharing) lets your frontend
# (running on a different port) talk to this backend. In dev you allow all
# origins. In production you'd lock this down to your actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups (think of these like Flask blueprints)
app.include_router(library.router, prefix="/api/library", tags=["Library"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])


@app.get("/health")
async def health_check():
    """Simple health check — useful for Docker and Unraid to know the app is alive."""
    return {"status": "ok", "version": "0.1.0"}
