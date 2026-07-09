"""Plan 5 acceptance test: the offline end-to-end resolve flow (spec §6.2).

Unlike the per-router API tests (which ``create_all`` the schema on the
lifespan engine), this test proves the *real boot path*: a tmp-file SQLite DB is
migrated by :func:`spotdl_server.bootstrap.upgrade_to_head` — the same
programmatic Alembic seam Plan 8's embedded CLI uses — so the migration, not
``metadata.create_all``, backs the running app. The provider registry is faked at
the ``create_app(settings, registry=...)`` seam (a resolver, an audio provider, a
lyrics provider, plus one deliberately-failing provider), and the app is driven
over ``httpx.ASGITransport``.

The flow asserted, in one unit of work per HTTP call:

1. ``POST /resolve`` a Spotify track URL → ``TrackOut`` body, and the failing
   provider surfaces in ``degraded_sources`` (a degraded source is reported, not
   fatal — spec §10).
2. ``GET /tracks/{id}`` returns the same canonical track.
3. ``GET /tracks/{id}/matches`` is non-empty and ranked (ordered by score).
4. ``GET /tracks/{id}/lyrics`` responds with the well-formed lyrics envelope.
5. Re-``POST /resolve`` the *same* URL → still exactly one canonical track (the
   snapshot cache + canonical merge dedupe), and its matches are *replaced*, not
   duplicated.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.db.base import Base
from spotdl_server.settings import DeploymentMode, Settings
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeLyricsProvider,
    FakeResolver,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/track123"

TRACK = Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567")

CANDIDATES = (
    AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt-best",
        url="https://audio/yt-best",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    ),
    AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt-worse",
        url="https://audio/yt-worse",
        name="Song (Sped Up Nightcore Remix)",
        artists=("Someone Else",),
        duration_ms=123_000,
    ),
)


def _build_registry():  # type: ignore[no-untyped-def]
    """Resolver + audio + lyrics fakes, plus one provider that always fails."""
    return build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=TRACK),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=list(CANDIDATES)),
        FakeLyricsProvider(id=ProviderId.GENIUS, text="la la la"),
        failing=[ProviderId.DEEZER],
    )


@asynccontextmanager
async def _migrated_app_client(data_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    """A client over an app backed by a **migrated** tmp-file DB.

    ``upgrade_to_head`` runs the real Alembic migration against the same file the
    lifespan engine then opens (both derive from ``settings.effective_database_url``),
    proving migration parity end-to-end. The registry is injected and thus not
    closed by the app.
    """
    settings = Settings(mode=DeploymentMode.SELFHOST, data_dir=data_dir)
    # ``upgrade_to_head`` is synchronous and drives Alembic's async env via its
    # own ``asyncio.run``; run it off the test's event loop so that nested call
    # gets a fresh loop (Plan 8's real startup path is likewise pre-event-loop).
    await asyncio.to_thread(upgrade_to_head, settings)  # real boot path — NOT create_all
    app = create_app(settings, registry=_build_registry())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


def _db_file(data_dir: Path) -> Path:
    return data_dir / "spotdl.db"


def _count_tracks(data_dir: Path) -> int:
    """Row count of the canonical ``tracks`` table via a plain sync connection."""
    engine = create_engine(f"sqlite:///{_db_file(data_dir)}")
    try:
        with Session(engine) as session:
            track_table = Base.metadata.tables["tracks"]
            return session.scalar(select(func.count()).select_from(track_table)) or 0
    finally:
        engine.dispose()


async def test_resolve_flow_end_to_end(tmp_path: Path) -> None:
    async with _migrated_app_client(tmp_path) as client:
        # 1) Resolve the URL → TrackOut + degraded source surfaced.
        resolve = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})
        assert resolve.status_code == 200, resolve.text
        body = resolve.json()
        assert body["entity"]["type"] == "track"
        track = body["entity"]["track"]
        assert track["name"] == "Song"
        assert track["artists"] == ["Artist"]
        # The failing DEEZER provider is reported, not fatal.
        assert "deezer" in body["degraded_sources"]
        track_id = track["id"]

        # 2) The canonical track is readable by its id.
        got = await client.get(f"/api/v1/tracks/{track_id}")
        assert got.status_code == 200
        assert got.json()["id"] == track_id
        assert got.json()["name"] == "Song"

        # 3) Matches are present and ranked (net_score descending).
        matches = (await client.get(f"/api/v1/tracks/{track_id}/matches")).json()
        assert matches["track_id"] == track_id
        rows = matches["matches"]
        assert rows, "expected at least one ranked match"
        assert all(row["target_provider"] == "youtube" for row in rows)
        scores = [row["net_score"] for row in rows]
        assert scores == sorted(scores, reverse=True), f"matches not ranked: {scores}"
        first_match_count = len(rows)

        # 4) The lyrics envelope is well-formed (the resolve path persists no
        #    lyrics yet — the sub-resource still responds with the typed shape).
        lyrics = await client.get(f"/api/v1/tracks/{track_id}/lyrics")
        assert lyrics.status_code == 200
        lyrics_body = lyrics.json()
        assert lyrics_body["track_id"] == track_id
        assert isinstance(lyrics_body["lyrics"], list)

    # The migration (not create_all) produced the real schema.
    assert "alembic_version" in set(
        inspect(create_engine(f"sqlite:///{_db_file(tmp_path)}")).get_table_names()
    )
    assert _count_tracks(tmp_path) == 1

    # 5) Re-resolve the SAME url against the SAME migrated DB: one canonical
    #    track, matches replaced (not duplicated).
    async with _migrated_app_client(tmp_path) as client:
        again = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})
        assert again.status_code == 200
        again_id = again.json()["entity"]["track"]["id"]
        assert again_id == track_id, "re-resolve must reuse the canonical track"

        rematches = (await client.get(f"/api/v1/tracks/{track_id}/matches")).json()["matches"]
        assert len(rematches) == first_match_count, "matches duplicated on re-resolve"

    assert _count_tracks(tmp_path) == 1, "re-resolve created a duplicate canonical track"
