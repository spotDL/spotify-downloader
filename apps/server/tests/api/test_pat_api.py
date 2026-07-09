"""End-to-end (offline) tests for the ``/api/v1/auth/tokens`` router.

The app is built through the real ``create_app`` seam with a fake provider
registry and an in-memory SQLite schema; a ``FakeClock`` is swapped onto
``app.state.clock`` after the lifespan starts so PAT expiry is deterministic. An
auth secret is configured on ``Settings`` (never hardcoded in source) so a user
can register and obtain the access JWT used to manage their PATs. These tests
prove the create-once contract (the full ``token`` appears only in the create
response), that a minted PAT authenticates ``GET /auth/me`` (a ``pat`` context),
that listing never leaks the secret, and that revoked / expired / unowned tokens
are rejected — all without touching the network or a real clock.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock, precreate_schema
from apps.server.tests.fakes import build_fake_registry

_ACCESS_TTL = 900


@asynccontextmanager
async def _auth_app(
    *, data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("pat-test-secret-key-0123456789-abcdef"),
        access_token_ttl_seconds=_ACCESS_TTL,
    )
    await precreate_schema(settings)
    app = create_app(settings, registry=build_fake_registry())
    async with app.router.lifespan_context(app):
        app.state.clock = clock  # deterministic PAT expiry, replacing the SystemClock
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def _register(client: httpx.AsyncClient, email: str = "cli@example.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "CLI"},
    )
    assert resp.status_code == 201, resp.text
    access: str = resp.json()["access_token"]
    return access


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_returns_full_token_only_here(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        resp = await client.post(
            "/api/v1/auth/tokens", json={"name": "laptop"}, headers=_bearer(access)
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "laptop"
    assert body["token"].startswith("spdl_pat_")
    assert body["token_prefix"].startswith("spdl_pat_")
    assert body["token"].startswith(body["token_prefix"])
    assert body["id"]
    assert body["created_at"]
    assert body["expires_at"] is None


async def test_created_pat_authenticates_me_as_pat_context(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        created = await client.post(
            "/api/v1/auth/tokens", json={"name": "laptop"}, headers=_bearer(access)
        )
        token = created.json()["token"]
        me = await client.get("/api/v1/auth/me", headers=_bearer(token))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "cli@example.com"


async def test_list_never_exposes_the_secret(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        created = await client.post(
            "/api/v1/auth/tokens", json={"name": "laptop"}, headers=_bearer(access)
        )
        full = created.json()["token"]
        listing = await client.get("/api/v1/auth/tokens", headers=_bearer(access))
    assert listing.status_code == 200, listing.text
    rows = listing.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "laptop"
    assert row["token_prefix"].startswith("spdl_pat_")
    assert "token" not in row
    assert "token_hash" not in row
    # The full secret must appear nowhere in a listing response.
    assert full not in listing.text
    assert row["revoked_at"] is None
    assert row["last_used_at"] is None  # never used for auth yet


async def test_revoked_pat_is_rejected(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        created = await client.post(
            "/api/v1/auth/tokens", json={"name": "laptop"}, headers=_bearer(access)
        )
        token_id = created.json()["id"]
        token = created.json()["token"]

        # Sanity: the PAT works before revocation.
        assert (await client.get("/api/v1/auth/me", headers=_bearer(token))).status_code == 200

        deleted = await client.delete(f"/api/v1/auth/tokens/{token_id}", headers=_bearer(access))
        assert deleted.status_code == 204, deleted.text

        after = await client.get("/api/v1/auth/me", headers=_bearer(token))
    # A revoked PAT is treated as unauthenticated by the auth dependency.
    assert after.status_code == 401
    assert after.json()["code"] == "authentication_required"


async def test_expired_pat_is_rejected(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        created = await client.post(
            "/api/v1/auth/tokens",
            json={"name": "ci", "expires_in_days": 1},
            headers=_bearer(access),
        )
        assert created.json()["expires_at"] is not None
        token = created.json()["token"]

        # Before expiry the PAT authenticates.
        assert (await client.get("/api/v1/auth/me", headers=_bearer(token))).status_code == 200

        clock.advance(86_400 + 1)  # push past the 1-day expiry
        after = await client.get("/api/v1/auth/me", headers=_bearer(token))
    assert after.status_code == 401
    assert after.json()["code"] == "authentication_required"


async def test_revoke_unowned_token_is_not_found(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        resp = await client.delete(f"/api/v1/auth/tokens/{uuid4()}", headers=_bearer(access))
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_tokens_require_authentication(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        anon_list = await client.get("/api/v1/auth/tokens")
        anon_create = await client.post("/api/v1/auth/tokens", json={"name": "x"})
    assert anon_list.status_code == 401
    assert anon_create.status_code == 401


async def test_create_rejects_blank_name(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client)
        resp = await client.post("/api/v1/auth/tokens", json={"name": ""}, headers=_bearer(access))
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


def test_tokens_router_absent_in_embedded_mode() -> None:
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    assert not any(path.startswith("/api/v1/auth/tokens") for path in paths)
