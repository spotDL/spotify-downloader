"""End-to-end (offline) tests for the metadata-correction report router.

The app is built through the real ``create_app`` seam with a fake registry and an
in-memory SQLite schema; a user registers to obtain an access JWT. These tests
prove: an anonymous ``POST /reports`` is 401, an authenticated one returns 201
with a ``pending`` report, ``GET /reports/me`` returns only the caller's own
reports, and the routes are mount-gated to auth-active modes — all without
touching the network or a real clock.
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


@asynccontextmanager
async def _auth_app(
    *, data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("report-test-secret-key-0123456789-abcdef"),
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


async def _register(client: httpx.AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Reporter"},
    )
    assert resp.status_code == 201, resp.text
    access: str = resp.json()["access_token"]
    return access


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _report_body() -> dict[str, str]:
    return {
        "subject_type": "track",
        "subject_id": str(uuid4()),
        "field": "name",
        "proposed_value": "Corrected Title",
        "reason": "the title has a typo",
    }


async def test_report_requires_authentication(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.post("/api/v1/reports", json=_report_body())
    assert resp.status_code == 401
    assert resp.json()["code"] == "authentication_required"


async def test_authenticated_report_returns_201_pending(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client, "reporter@example.com")
        resp = await client.post("/api/v1/reports", json=_report_body(), headers=_bearer(access))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subject_type"] == "track"
    assert body["field"] == "name"
    assert body["proposed_value"] == "Corrected Title"
    assert body["status"] == "pending"
    assert "created_at" in body


async def test_reports_me_returns_only_own_reports(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        alice = await _register(client, "alice@example.com")
        bob = await _register(client, "bob@example.com")
        await client.post("/api/v1/reports", json=_report_body(), headers=_bearer(alice))
        await client.post("/api/v1/reports", json=_report_body(), headers=_bearer(bob))

        mine = await client.get("/api/v1/reports/me", headers=_bearer(alice))
        anon = await client.get("/api/v1/reports/me")
    assert mine.status_code == 200, mine.text
    assert len(mine.json()) == 1
    assert anon.status_code == 401


async def test_invalid_subject_type_is_422(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        access = await _register(client, "reporter@example.com")
        body = _report_body()
        body["subject_type"] = "not-a-real-type"
        resp = await client.post("/api/v1/reports", json=body, headers=_bearer(access))
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


def test_report_routes_absent_in_embedded_mode() -> None:
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    assert not any(path.startswith("/api/v1/reports") for path in paths)


def test_report_routes_present_when_auth_active() -> None:
    paths = create_app(Settings(mode=DeploymentMode.SELFHOST)).openapi()["paths"]
    assert "/api/v1/reports" in paths
    assert "/api/v1/reports/me" in paths
