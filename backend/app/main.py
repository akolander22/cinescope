"""
CineScope - Media Intelligence Backend
Entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.db.database import init_db
from app.api.routes import library, suggestions, sources, queue
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(library.router,     prefix="/api/library",     tags=["Library"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(sources.router,     prefix="/api/sources",     tags=["Sources"])
app.include_router(queue.router,       prefix="/api/queue",       tags=["Queue"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# ── Serve React frontend ─────────────────────────────────────
# The built React app lives in /app/static/ inside the container.
# We mount it at /assets (Vite's output for JS/CSS files) and
# catch-all any other route to serve index.html so React Router works.

STATIC_DIR = "/app/static"

if os.path.exists(STATIC_DIR):
    # Serve Vite's asset files (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        Catch-all route — serves index.html for any non-API path.
        This is required for client-side routing to work (React handles
        the routing in the browser, not the server).
        """
        return FileResponse(f"{STATIC_DIR}/index.html")
else:
    # Running locally without a built frontend — just show a message
    @app.get("/")
    async def no_frontend():
        return {
            "message": "CineScope API running. Frontend not built yet.",
            "docs": "/docs"
        }
