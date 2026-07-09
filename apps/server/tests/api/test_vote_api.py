"""End-to-end (offline) tests for the voting routers.

The app is built through the real ``create_app`` seam with a fake registry and an
in-memory SQLite schema; a user registers to obtain an access JWT, and votable
rows (a match, a lyrics variant, an entity link) are inserted directly through the
lifespan-built session factory. These tests prove: an anonymous vote is 401, an
authenticated vote returns 200 with the updated tallies and ``your_vote``, an
unknown votable id is 404 ``not_found``, and the three votable kinds
(matches / lyrics / links) behave in parallel — all without touching the network
or a real clock.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.db.enums import LinkStatus
from spotdl_server.db.models import EntityLink, Lyrics, Match, ProviderSnapshot, Track
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock
from apps.server.tests.fakes import build_fake_registry


@asynccontextmanager
async def _auth_app(
    *, data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("vote-test-secret-key-0123456789-abcdef"),
    )
    app = create_app(settings, registry=build_fake_registry())
    async with app.router.lifespan_context(app):
        app.state.clock = clock
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def _register(client: httpx.AsyncClient, email: str = "voter@example.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Voter"},
    )
    assert resp.status_code == 201, resp.text
    access: str = resp.json()["access_token"]
    return access


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_match(app: FastAPI) -> uuid.UUID:
    async with app.state.sessionmaker() as session:
        track = Track(name="Track", duration_ms=200000)
        session.add(track)
        await session.flush()
        match = Match(
            track_id=track.id,
            target_provider=ProviderId.YTMUSIC,
            target_id=uuid.uuid4().hex,
            target_url="https://example.test/a",
            score=90.0,
            matcher_version="v5.0",
            status=MatchStatus.AUTO,
        )
        session.add(match)
        await session.flush()
        match_id = match.id
        await session.commit()
    return match_id


async def _make_lyrics(app: FastAPI) -> uuid.UUID:
    async with app.state.sessionmaker() as session:
        track = Track(name="Track", duration_ms=200000)
        session.add(track)
        await session.flush()
        lyrics = Lyrics(
            track_id=track.id, source=ProviderId.LRCLIB, kind=LyricsKind.PLAIN, text="la"
        )
        session.add(lyrics)
        await session.flush()
        lyrics_id = lyrics.id
        await session.commit()
    return lyrics_id


async def _make_link(app: FastAPI) -> uuid.UUID:
    async with app.state.sessionmaker() as session:
        snapshot = ProviderSnapshot(
            provider=ProviderId.SPOTIFY,
            provider_entity_id=uuid.uuid4().hex,
            entity_type=EntityType.TRACK,
            raw_payload={},
        )
        session.add(snapshot)
        await session.flush()
        link = EntityLink(
            entity_type=EntityType.TRACK,
            entity_id=uuid.uuid4(),
            snapshot_id=snapshot.id,
            status=LinkStatus.AUTO,
        )
        session.add(link)
        await session.flush()
        link_id = link.id
        await session.commit()
    return link_id


async def test_vote_requires_authentication(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        match_id = await _make_match(app)
        resp = await client.post(f"/api/v1/matches/{match_id}/vote", json={"value": "up"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "authentication_required"


async def test_authenticated_upvote_returns_updated_tallies(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        match_id = await _make_match(app)
        resp = await client.post(
            f"/api/v1/matches/{match_id}/vote", json={"value": "up"}, headers=_bearer(access)
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["votable_type"] == "match"
    assert body["votable_id"] == str(match_id)
    assert body["upvotes"] == 1
    assert body["downvotes"] == 0
    assert body["net_score"] == 1
    assert body["your_vote"] == 1
    assert body["status"] == "auto"


async def test_change_and_retract_vote(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        match_id = await _make_match(app)
        await client.post(
            f"/api/v1/matches/{match_id}/vote", json={"value": "up"}, headers=_bearer(access)
        )
        down = await client.post(
            f"/api/v1/matches/{match_id}/vote", json={"value": "down"}, headers=_bearer(access)
        )
        retract = await client.post(
            f"/api/v1/matches/{match_id}/vote", json={"value": "retract"}, headers=_bearer(access)
        )
    assert down.json()["net_score"] == -1
    assert down.json()["your_vote"] == -1
    assert retract.json()["net_score"] == 0
    assert retract.json()["your_vote"] is None


async def test_unknown_match_id_is_404(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        resp = await client.post(
            f"/api/v1/matches/{uuid.uuid4()}/vote", json={"value": "up"}, headers=_bearer(access)
        )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_lyrics_vote(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        lyrics_id = await _make_lyrics(app)
        resp = await client.post(
            f"/api/v1/lyrics/{lyrics_id}/vote", json={"value": "up"}, headers=_bearer(access)
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["votable_type"] == "lyrics"
    assert body["net_score"] == 1
    assert body["your_vote"] == 1
    assert body["status"] is None  # lyrics never gets a status


async def test_link_vote(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        link_id = await _make_link(app)
        resp = await client.post(
            f"/api/v1/links/{link_id}/vote", json={"value": "down"}, headers=_bearer(access)
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["votable_type"] == "entity_link"
    assert body["downvotes"] == 1
    assert body["net_score"] == -1
    assert body["your_vote"] == -1
    assert body["status"] == "auto"


async def test_invalid_value_is_422(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        access = await _register(client)
        match_id = await _make_match(app)
        resp = await client.post(
            f"/api/v1/matches/{match_id}/vote", json={"value": "sideways"}, headers=_bearer(access)
        )
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


def test_vote_routers_absent_in_embedded_mode() -> None:
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    assert not any("/vote" in path for path in paths)


@pytest.mark.parametrize("prefix", ["/api/v1/matches", "/api/v1/lyrics", "/api/v1/links"])
def test_vote_routes_present_when_auth_active(prefix: str) -> None:
    paths = create_app(Settings(mode=DeploymentMode.SELFHOST)).openapi()["paths"]
    assert any(path.startswith(prefix) and path.endswith("/vote") for path in paths)
