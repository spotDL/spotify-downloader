"""End-to-end (offline) tests for the ``/api/v1/auth`` router.

The app is built through the real ``create_app`` seam with a fake provider
registry and an in-memory SQLite schema; a ``FakeClock`` is swapped onto
``app.state.clock`` after the lifespan starts so token expiry is deterministic.
An auth secret is configured on ``Settings`` (never hardcoded in source) so the
token service can mint/verify JWTs. These tests prove the register/login/refresh
round-trips, the ``GET /me`` guard (JWT and PAT), and the expired-access-token
path — all without touching the network or a real clock.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.auth.tokens import new_pat, sha256_hex
from spotdl_server.db.base import Base
from spotdl_server.repositories.tokens import ApiTokenRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock
from apps.server.tests.fakes import build_fake_registry

_ACCESS_TTL = 900


@asynccontextmanager
async def _auth_app(
    *, data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("api-test-secret-key-0123456789-abcdef"),
        access_token_ttl_seconds=_ACCESS_TTL,
    )
    app = create_app(settings, registry=build_fake_registry())
    async with app.router.lifespan_context(app):
        app.state.clock = clock  # deterministic expiry, replacing the SystemClock
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def _register(client: httpx.AsyncClient, email: str = "user@example.com") -> dict:  # type: ignore[type-arg]
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "User"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_returns_tokens_and_user(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = await _register(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == _ACCESS_TTL
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["is_admin"] is False
    assert "password" not in body["user"]


async def test_register_duplicate_email_is_conflict(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        await _register(client)
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "User@example.com", "password": "password123"},
        )
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


async def test_register_rejects_short_password(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


async def test_me_with_access_token_returns_profile(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = await _register(client)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


async def test_me_without_header_is_unauthenticated(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "authentication_required"


async def test_me_with_expired_access_token_is_rejected(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = await _register(client)
        clock.advance(_ACCESS_TTL + 1)  # push the access token past its 15-min life
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
    # An expired/invalid JWT is treated as unauthenticated by the dependency.
    assert resp.status_code == 401
    assert resp.json()["code"] == "authentication_required"


async def test_me_with_pat_returns_profile(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        full, prefix = new_pat()
        async with app.state.sessionmaker() as db:
            user = await UserRepository(db).create(
                email="cli@example.com", password_hash=None, display_name="CLI"
            )
            await ApiTokenRepository(db).create(
                user_id=user.id,
                name="laptop",
                token_prefix=prefix,
                token_hash=sha256_hex(full),
                expires_at=None,
            )
            await db.commit()
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {full}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "cli@example.com"


async def test_login_and_refresh_round_trip(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        await _register(client)
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        refresh_token = login.json()["refresh_token"]

        refreshed = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["refresh_token"] != refresh_token
        assert refreshed.json()["access_token"]


async def test_refresh_reuse_is_invalid_token(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = await _register(client)
        first = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        )
        assert first.status_code == 200
        # Re-presenting the now-spent original refresh token is reuse -> 401.
        reuse = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        )
    assert reuse.status_code == 401
    assert reuse.json()["code"] == "invalid_token"


async def test_logout_revokes_refresh_and_requires_auth(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = await _register(client)
        # Logout needs an authenticated caller.
        anon = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": body["refresh_token"]}
        )
        assert anon.status_code == 401

        out = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": body["refresh_token"]},
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert out.status_code == 204

        # The refresh token is dead after logout.
        after = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
        )
    assert after.status_code == 401


def test_auth_router_absent_in_embedded_mode() -> None:
    # FastAPI includes routers lazily, so introspect the OpenAPI paths (the
    # public, mount-time-resolved surface) rather than ``app.routes``.
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    assert not any(path.startswith("/api/v1/auth") for path in paths)


@pytest.mark.parametrize("mode", [DeploymentMode.SELFHOST, DeploymentMode.HOSTED])
def test_auth_router_mounted_when_auth_active(mode: DeploymentMode) -> None:
    paths = create_app(Settings(mode=mode, auth_secret_key=SecretStr("x"))).openapi()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/me" in paths
