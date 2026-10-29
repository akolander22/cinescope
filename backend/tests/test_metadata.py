"""TMDB metadata backfill, with TMDB stubbed out."""

import pytest
from sqlalchemy import select

from app.models.film import Film, FilmStatus
from app.services import metadata_service


@pytest.mark.asyncio
async def test_backfill_fills_posters_by_id_and_search(session_factory, monkeypatch):
    async with session_factory() as db:
        db.add_all([
            Film(title="Heat", year=1995, tmdb_id=949, status=FilmStatus.owned),
            Film(title="Alien", year=1979, status=FilmStatus.owned),       # no TMDB ID
            Film(title="Nope Film", year=2001, status=FilmStatus.owned),   # not on TMDB
        ])
        await db.commit()

    async def fake_tmdb_get(endpoint, params=None):
        if endpoint == "/search/movie":
            return {"results": [{"id": 348}] if params["query"] == "Alien" else []}
        movie_id = int(endpoint.rsplit("/", 1)[1])
        return {"id": movie_id, "poster_path": f"/{movie_id}.jpg", "overview": "o",
                "vote_average": 8.0, "genres": [{"name": "Thriller"}], "runtime": 120,
                "imdb_id": f"tt{movie_id}"}

    monkeypatch.setattr(metadata_service, "tmdb_get", fake_tmdb_get)
    monkeypatch.setattr(metadata_service, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(metadata_service, "REQUEST_DELAY", 0)
    monkeypatch.setattr(metadata_service.settings, "TMDB_API_TOKEN", "test")

    result = await metadata_service.backfill_metadata()
    assert result == {"checked": 3, "updated": 2, "not_found": 1}

    async with session_factory() as db:
        films = {f.title: f for f in (await db.execute(select(Film))).scalars()}
    assert films["Heat"].poster_path == "/949.jpg"
    assert films["Alien"].tmdb_id == 348 and films["Alien"].genre == "Thriller"
    assert films["Nope Film"].poster_path is None
