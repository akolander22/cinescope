"""
Source and Suggestion models.

A Source is a discovery feed (Letterboxd, IMDb trending, etc.)
A Suggestion links a Film to the Source that found it, with metadata.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Source(Base):
    """
    A discovery source — where we look for interesting films.
    
    LEARNING NOTE: Storing sources in the DB (rather than hardcoding them)
    means you can add/enable/disable them via the API without redeploying.
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)           # Human-readable: "Letterboxd Popular"
    source_type = Column(String, nullable=False)    # "letterboxd" | "imdb" | "metacritic" | "a24"
    url = Column(String)                            # The URL we scrape/poll
    is_active = Column(Boolean, default=True)
    interval_hours = Column(Integer, default=6)     # How often to poll
    last_polled_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    suggestions = relationship("Suggestion", back_populates="source")

    def __repr__(self):
        return f"<Source {self.name} [{'active' if self.is_active else 'disabled'}]>"


class Suggestion(Base):
    """
    A junction between a Film and the Source that surfaced it.
    
    One film can be suggested by multiple sources — this is how we 
    build a "cross-source score" (a film appearing in 3 lists scores higher).
    
    LEARNING NOTE: This is a classic many-to-many relationship broken into
    an explicit junction table with extra data (score, tags). SQLAlchemy's
    `relationship()` lets you navigate both directions:
        film.suggestions  → all Suggestion records for that film
        suggestion.film   → the Film object
        suggestion.source → the Source object
    """
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    film_id = Column(Integer, ForeignKey("films.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    raw_score = Column(Float)         # Score as reported by the source (0-100)
    composite_score = Column(Float)   # Weighted score combining all sources
    tags = Column(String)             # Comma-separated: "Festival Pick,A24,Critics Pick"
    notes = Column(Text)              # e.g. "Cannes 2025 competition entry"

    # What the user did with this suggestion
    user_action = Column(String, nullable=True)  # "queued" | "dismissed" | None
    actioned_at = Column(DateTime(timezone=True), nullable=True)

    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

    film = relationship("Film", back_populates="suggestions")
    source = relationship("Source", back_populates="suggestions")

    def __repr__(self):
        return f"<Suggestion film_id={self.film_id} source={self.source_id} score={self.composite_score}>"
