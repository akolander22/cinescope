"""Queue/dismiss actions and the suggestions inbox."""

import pytest
from sqlalchemy import select

from app.models.film import Film, FilmStatus
from app.models.source import Source, Suggestion
from app.services.discovery_service import _upsert_suggestion


async def seed(session_factory):
    """Two sources both suggesting Dune, plus an owned film with a stale suggestion."""
    async with session_factory() as db:
        a = Source(name="TMDB Trending", source_type="tmdb_trending")
        b = Source(name="TMDB Upcoming", source_type="tmdb_upcoming")
        dune = Film(title="Dune", year=2021, status=FilmStatus.suggested)
        owned = Film(title="Heat", year=1995, status=FilmStatus.owned, in_plex=True)
        db.add_all([a, b, dune, owned])
        await db.flush()
        db.add_all([
            Suggestion(film_id=dune.id, source_id=a.id, composite_score=80),
            Suggestion(film_id=dune.id, source_id=b.id, composite_score=70),
            Suggestion(film_id=owned.id, source_id=a.id, composite_score=90),
        ])
        await db.commit()
        return dune.id


async def suggestion_ids(client):
    res = await client.get("/api/suggestions/")
    assert res.status_code == 200
    return res.json()


@pytest.mark.asyncio
async def test_inbox_hides_owned_films(client, session_factory):
    await seed(session_factory)
    titles = {s["title"] for s in await suggestion_ids(client)}
    assert titles == {"Dune"}


@pytest.mark.asyncio
@pytest.mark.parametrize("action,status", [("queue", FilmStatus.queued), ("dismiss", FilmStatus.dismissed)])
async def test_action_updates_film_and_all_its_suggestions(client, session_factory, action, status):
    dune_id = await seed(session_factory)
    first = (await suggestion_ids(client))[0]

    res = await client.post(f"/api/suggestions/{first['id']}/action", json={"action": action})
    assert res.status_code == 200, res.text

    # The film disappears from the inbox, including the other source's suggestion
    assert await suggestion_ids(client) == []

    async with session_factory() as db:
        dune = await db.get(Film, dune_id)
        assert dune.status == status
        actions = (await db.execute(
            select(Suggestion.user_action).where(Suggestion.film_id == dune_id)
        )).scalars().all()
        assert actions == [status.value, status.value]


@pytest.mark.asyncio
async def test_unknown_action_and_missing_suggestion(client, session_factory):
    await seed(session_factory)
    assert (await client.post("/api/suggestions/1/action", json={"action": "nope"})).status_code == 400
    assert (await client.post("/api/suggestions/999/action", json={"action": "queue"})).status_code == 404


@pytest.mark.asyncio
async def test_discovery_skips_films_already_handled(session_factory):
    await seed(session_factory)
    async with session_factory() as db:
        src = (await db.execute(select(Source).where(Source.source_type == "tmdb_upcoming"))).scalar_one()
        # Heat is owned, so a new source finding it shouldn't add a suggestion
        assert await _upsert_suggestion(db, src, {"title": "Heat", "year": 1995}) is False
        await db.commit()
        count = len((await db.execute(
            select(Suggestion).join(Film).where(Film.title == "Heat")
        )).scalars().all())
        assert count == 1
