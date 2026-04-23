"""
Configuration — all settings come from environment variables or .env file.

LEARNING NOTE: pydantic-settings gives you type-safe config. Any env var
you define here can be overridden by setting it in your Docker environment
or Unraid template. Never hardcode secrets — always use env vars.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # --- App ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    # SQLite path inside the container. We'll mount /data as a volume on Unraid
    # so the database persists between container restarts.
    DATABASE_URL: str = "sqlite+aiosqlite:////data/cinescope.db"

    # --- Plex ---
    # You'll find your token in Plex's web UI: 
    # Settings > Account > Authorized Devices, or inspect network requests.
    PLEX_URL: str = "http://localhost:32400"
    PLEX_TOKEN: str = ""
    PLEX_MOVIE_LIBRARY: str = "Movies"  # The exact name of your Movies library in Plex

    # --- Radarr ---
    RADARR_URL: str = "http://localhost:7878"
    RADARR_API_KEY: str = ""

    # --- Scheduler ---
    # How often (in hours) to poll discovery sources for new films
    DISCOVERY_INTERVAL_HOURS: int = 6

    # --- CORS ---
    # In production, set this to your actual frontend URL
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- Scoring ---
    # Minimum score a discovered film needs to appear in suggestions
    MIN_SUGGESTION_SCORE: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single instance imported everywhere — like a singleton
settings = Settings()
