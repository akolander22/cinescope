"""Plex sync: upserts, removals, and not blocking the event loop."""

import asyncio
import time

import pytest
from sqlalchemy import select

from app.models.film import Film, FilmStatus
from app.services import plex_service


def movie(key, title, year, tmdb_id=None):
    return {"plex_key": key, "title": title, "year": year, "tmdb_id": tmdb_id, "imdb_id": None}


async def films_by_title(session_factory):
    async with session_factory() as db:
        return {f.title: f for f in (await db.execute(select(Film))).scalars()}


@pytest.mark.asyncio
async def test_sync_adds_owns_and_removes(session_factory):
    async with session_factory() as db:
        db.add_all([
            Film(title="Heat", year=1995, plex_key="1", in_plex=True, status=FilmStatus.owned),
            Film(title="Gone", year=2000, plex_key="2", in_plex=True, status=FilmStatus.owned),
            # Suggested earlier, since downloaded
            Film(title="Dune", year=2021, tmdb_id=438631, status=FilmStatus.suggested),
        ])
        await db.commit()

        result = await plex_service.sync_plex_library(db, movies=[
            movie("1", "Heat", 1995),
            movie("3", "Dune", 2021, tmdb_id=438631),
            movie("4", "Alien", 1979),
        ])

    assert result == {"synced": 3, "new": 1, "updated": 2, "removed": 1}
    films = await films_by_title(session_factory)
    assert films["Dune"].status == FilmStatus.owned and films["Dune"].in_plex
    assert films["Alien"].status == FilmStatus.owned
    assert not films["Gone"].in_plex and films["Gone"].status == FilmStatus.dismissed


@pytest.mark.asyncio
async def test_empty_plex_response_removes_nothing(session_factory):
    async with session_factory() as db:
        db.add(Film(title="Heat", year=1995, plex_key="1", in_plex=True, status=FilmStatus.owned))
        await db.commit()
        result = await plex_service.sync_plex_library(db, movies=[])
    assert result["removed"] == 0
    assert (await films_by_title(session_factory))["Heat"].in_plex


@pytest.mark.asyncio
async def test_sync_runs_plex_reads_off_the_event_loop(session_factory, monkeypatch):
    def slow_plex():
        time.sleep(0.5)  # plexapi blocks like this
        return [movie("1", "Heat", 1995)]

    monkeypatch.setattr(plex_service, "_fetch_plex_movies", slow_plex)
    monkeypatch.setattr(plex_service, "AsyncSessionLocal", session_factory)

    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.05)
            ticks += 1

    t = asyncio.create_task(ticker())
    result = await plex_service.run_plex_sync()
    t.cancel()

    assert result["new"] == 1
    assert ticks >= 5, "event loop was blocked during the Plex read"
    assert plex_service.sync_state["running"] is False
    assert plex_service.sync_state["last_result"] == result


@pytest.mark.asyncio
async def test_sync_endpoints(client, session_factory, monkeypatch):
    monkeypatch.setattr(plex_service.settings, "PLEX_TOKEN", "x")
    monkeypatch.setattr(plex_service, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(plex_service, "_fetch_plex_movies", lambda: [])
    started = await client.post("/api/library/sync")
    assert started.status_code == 202 and started.json()["started"] is True
    status = await client.get("/api/library/sync/status")
    assert status.status_code == 200 and "running" in status.json()
