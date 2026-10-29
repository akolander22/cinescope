"""Radarr settings and Send to Radarr, with Radarr stubbed out."""

import pytest

from app.api.routes import queue as queue_routes, sources as source_routes
from app.models.film import Film, FilmStatus
from app.services import radarr_service

PROFILES = [{"id": 4, "name": "HD-1080p"}, {"id": 6, "name": "Ultra-HD"}]
FOLDERS = [{"path": "/data/media/movies", "free_space": 1}, {"path": "/data/media/kids", "free_space": 1}]


@pytest.fixture
def radarr(monkeypatch):
    async def profiles():
        return PROFILES

    async def folders():
        return FOLDERS

    sent = []

    async def fake_add(film, profile_id, root_folder):
        sent.append((film.title, profile_id, root_folder))
        return {"success": True, "radarr_id": 1}

    for module in (radarr_service, source_routes):
        monkeypatch.setattr(module, "get_quality_profiles", profiles)
        monkeypatch.setattr(module, "get_root_folders", folders)
    monkeypatch.setattr(queue_routes, "add_to_radarr", fake_add)
    return sent


async def queued_film(session_factory, tmdb_id=438631):
    async with session_factory() as db:
        film = Film(title="Dune", year=2021, tmdb_id=tmdb_id, status=FilmStatus.queued)
        db.add(film)
        await db.commit()
        return film.id


@pytest.mark.asyncio
async def test_defaults_to_radarrs_first_profile_and_folder(client, session_factory, radarr):
    film_id = await queued_film(session_factory)
    res = await client.post(f"/api/queue/{film_id}/send-to-radarr")
    assert res.json()["success"] is True
    assert radarr == [("Dune", 4, "/data/media/movies")]


@pytest.mark.asyncio
async def test_uses_saved_choice(client, session_factory, radarr):
    res = await client.put("/api/sources/radarr/settings",
                           json={"quality_profile_id": 6, "root_folder": "/data/media/kids"})
    assert res.status_code == 200

    options = (await client.get("/api/sources/radarr/options")).json()
    assert options["selected"] == {"quality_profile_id": 6, "root_folder": "/data/media/kids"}

    film_id = await queued_film(session_factory)
    await client.post(f"/api/queue/{film_id}/send-to-radarr")
    assert radarr == [("Dune", 6, "/data/media/kids")]


@pytest.mark.asyncio
async def test_rejects_unknown_profile(client, radarr):
    res = await client.put("/api/sources/radarr/settings",
                           json={"quality_profile_id": 99, "root_folder": "/data/media/kids"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_film_without_tmdb_id_is_a_clear_400(client, session_factory, radarr):
    film_id = await queued_film(session_factory, tmdb_id=None)
    res = await client.post(f"/api/queue/{film_id}/send-to-radarr")
    assert res.status_code == 400
    assert "TMDB ID" in res.json()["detail"]
    assert radarr == []
