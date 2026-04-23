"""
Database Models

LEARNING NOTE: Each class here maps to a table in SQLite. SQLAlchemy reads
the Column definitions and creates the table schema. The relationship()
calls set up foreign key links so you can do things like
`suggestion.film` to get the Film object directly.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class FilmStatus(str, enum.Enum):
    """Tracks where a film sits in the workflow."""
    owned = "owned"          # Already in your Plex library
    suggested = "suggested"  # Discovered, waiting for your review
    queued = "queued"        # You approved it
    dismissed = "dismissed"  # You said no
    added = "added"          # Sent to Radarr


class Film(Base):
    """
    Central film record. Every film we know about — owned or discovered —
    lives here. We use TMDB ID as the canonical identifier since both
    Plex and Radarr use TMDB under the hood.
    """
    __tablename__ = "films"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=True)
    imdb_id = Column(String, unique=True, index=True, nullable=True)

    title = Column(String, nullable=False)
    year = Column(Integer)
    genre = Column(String)           # Comma-separated, e.g. "Drama,Thriller"
    overview = Column(Text)
    poster_path = Column(String)     # TMDB poster URL
    runtime_minutes = Column(Integer)

    status = Column(Enum(FilmStatus), default=FilmStatus.suggested, index=True)

    # Scores from various sources (0-100)
    tmdb_score = Column(Float)
    imdb_score = Column(Float)
    metacritic_score = Column(Integer)
    rt_score = Column(Integer)       # Rotten Tomatoes

    # Plex-specific
    plex_key = Column(String)        # Plex's internal rating key, for quick lookups
    in_plex = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    suggestions = relationship("Suggestion", back_populates="film", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Film {self.title} ({self.year}) [{self.status}]>"
