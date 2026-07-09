"""End-to-end (offline) tests for the match-submission router.

The app is built through the real ``create_app`` seam with a fake registry and an
in-memory SQLite schema; a user registers to obtain an access JWT and a track is
inserted directly through the lifespan-built session factory. These tests prove:
an anonymous submit is 401, an authenticated submit of an audio-track URL returns
201 ``MatchOut`` and then appears in ``GET /tracks/{id}/matches`` (Plan 5), a
Spotify URL is 400 ``not_an_audio_target``, garbage is 400 ``unsupported_url``,
and an unknown track is 404 — all without touching the network or a real clock.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.db.models import Track
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock, precreate_schema
from apps.server.tests.fakes import build_fake_registry

_YT_URL = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"


@asynccontextmanager
async def _auth_app(
    *, data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("submit-test-secret-key-0123456789-abcdef"),
    )
    await precreate_schema(settings)
    app = create_app(settings, registry=build_fake_registry())
    async with app.router.lifespan_context(app):
        app.state.clock = clock
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def _register(client: httpx.AsyncClient, email: str = "submitter@example.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Submitter"},
    )
    assert resp.status_code == 201, resp.text
    access: str = resp.json()["access_token"]
    return access


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_track(app: FastAPI) -> uuid.UUID:
    async with app.state.sessionmaker() as session:
        track = Track(name="Track", duration_ms=200000)
        session.add(track)
        await session.flush()
        track_id = track.id
        await session.commit()
    return track_id


async def test_submit_requires_authentication(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        track_id = await _make_track(app)
        resp = await client.post(f"/api/v1/tracks/{track_id}/matches", json={"url": _YT_URL})
    assert resp.status_code == 401
    assert resp.json()["code"] == "authentication_required"


async def test_authenticated_submit_returns_201_and_appears_in_matches(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        track_id = await _make_track(app)
        resp = await client.post(
            f"/api/v1/tracks/{track_id}/matches",
            json={"url": _YT_URL},
            headers=_bearer(access),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["target_provider"] == "ytmusic"
        assert body["target_id"] == "dQw4w9WgXcQ"
        assert body["matcher_version"] == "community"
        assert body["status"] == "auto"
        assert body["score"] == 0.0

        listed = await client.get(f"/api/v1/tracks/{track_id}/matches")
    assert listed.status_code == 200, listed.text
    ids = [m["id"] for m in listed.json()["matches"]]
    assert body["id"] in ids


async def test_spotify_url_is_400_not_an_audio_target(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        track_id = await _make_track(app)
        resp = await client.post(
            f"/api/v1/tracks/{track_id}/matches",
            json={"url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"},
            headers=_bearer(access),
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == "not_an_audio_target"


async def test_garbage_url_is_400_unsupported_url(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        track_id = await _make_track(app)
        resp = await client.post(
            f"/api/v1/tracks/{track_id}/matches",
            json={"url": "not a url at all"},
            headers=_bearer(access),
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == "unsupported_url"


async def test_unknown_track_is_404(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        resp = await client.post(
            f"/api/v1/tracks/{uuid.uuid4()}/matches",
            json={"url": _YT_URL},
            headers=_bearer(access),
        )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_submission_route_absent_in_embedded_mode() -> None:
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    submit = paths.get("/api/v1/tracks/{id}/matches", {})
    assert "post" not in submit


def test_submission_route_present_when_auth_active() -> None:
    paths = create_app(Settings(mode=DeploymentMode.SELFHOST)).openapi()["paths"]
    assert "post" in paths["/api/v1/tracks/{id}/matches"]
