"""End-to-end (offline) tests for the minimal admin router (spec §6.2).

The app is built through the real ``create_app`` seam with a fake registry and an
in-memory SQLite schema. An admin is minted by registering a user and flipping
``is_admin`` directly in the DB (there is no self-service promotion endpoint).
These tests prove: every ``/api/v1/admin`` route requires an **active admin**
(anonymous → 401, non-admin → 403), the user list paginates with a ``total``, the
report queue filters by status, approve/reject stamps the decision and is
reflected in the queue, ``GET /stats`` returns correct aggregate counts, and a
**demoted** admin (a still-valid token whose claim says admin but whose DB row is
no longer admin) is rejected by the re-load guard — all without network or a real
clock.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.db.models import User
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
        auth_secret_key=SecretStr("admin-test-secret-key-0123456789-abcdef"),
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


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: httpx.AsyncClient, email: str) -> tuple[str, str]:
    """Register a user; return ``(access_token, user_id)``."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": email.split("@")[0]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["user"]["id"]


async def _set_admin(app: FastAPI, user_id: str, *, is_admin: bool) -> None:
    """Flip a user's ``is_admin`` flag directly in the DB (no promotion endpoint)."""
    async with app.state.sessionmaker() as db:
        user = await db.get(User, UUID(user_id))
        assert user is not None
        user.is_admin = is_admin
        await db.commit()


async def _file_report(client: httpx.AsyncClient, token: str) -> str:
    resp = await client.post(
        "/api/v1/reports",
        json={"subject_type": "track", "subject_id": str(uuid4()), "reason": "typo"},
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_admin_routes_require_authentication(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        for path in ("/api/v1/admin/users", "/api/v1/admin/reports", "/api/v1/admin/stats"):
            resp = await client.get(path)
            assert resp.status_code == 401, path
            assert resp.json()["code"] == "authentication_required"


async def test_admin_routes_forbid_non_admin(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        token, _uid = await _register(client, "normal@example.com")
        resp = await client.get("/api/v1/admin/users", headers=_bearer(token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_admin_lists_users_with_total(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        await _register(client, "bob@example.com")
        await _register(client, "carol@example.com")
        await _set_admin(app, admin_id, is_admin=True)

        resp = await client.get(
            "/api/v1/admin/users", params={"limit": 2, "offset": 0}, headers=_bearer(admin_token)
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert {"id", "email", "is_admin", "is_active", "created_at"} <= body["items"][0].keys()


async def test_report_queue_filters_and_decision_reflected(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        reporter_token, _rid = await _register(client, "reporter@example.com")
        await _set_admin(app, admin_id, is_admin=True)

        report_id = await _file_report(client, reporter_token)
        await _file_report(client, reporter_token)

        # Pending queue holds both reports.
        pending = await client.get("/api/v1/admin/reports", headers=_bearer(admin_token))
        assert pending.status_code == 200, pending.text
        assert pending.json()["total"] == 2

        # Approve one.
        approved = await client.post(
            f"/api/v1/admin/reports/{report_id}/approve",
            json={"note": "correct"},
            headers=_bearer(admin_token),
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"

        # It has left the pending queue; the approved filter now finds it.
        pending2 = await client.get("/api/v1/admin/reports", headers=_bearer(admin_token))
        assert pending2.json()["total"] == 1

        approved_q = await client.get(
            "/api/v1/admin/reports",
            params={"status": "approved"},
            headers=_bearer(admin_token),
        )
        assert approved_q.json()["total"] == 1
        assert approved_q.json()["items"][0]["id"] == report_id


async def test_reject_report(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        reporter_token, _rid = await _register(client, "reporter@example.com")
        await _set_admin(app, admin_id, is_admin=True)
        report_id = await _file_report(client, reporter_token)

        resp = await client.post(
            f"/api/v1/admin/reports/{report_id}/reject",
            json={"note": "spam"},
            headers=_bearer(admin_token),
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"


async def test_decide_unknown_report_is_404(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        await _set_admin(app, admin_id, is_admin=True)
        resp = await client.post(
            f"/api/v1/admin/reports/{uuid4()}/approve",
            json={},
            headers=_bearer(admin_token),
        )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_stats_returns_correct_counts(tmp_path: Path, clock: FakeClock) -> None:
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        reporter_token, _rid = await _register(client, "reporter@example.com")
        await _set_admin(app, admin_id, is_admin=True)
        await _file_report(client, reporter_token)

        resp = await client.get("/api/v1/admin/stats", headers=_bearer(admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["users_total"] == 2
    assert body["reports_total"] == 1
    assert body["reports_pending"] == 1
    # No matches/votes seeded via the public API in this scenario.
    assert body["matches_total"] == 0
    assert body["votes_total"] == 0
    assert body["community_verified_matches"] == 0
    assert body["rejected_matches"] == 0


async def test_demoted_admin_is_rejected_by_reload_guard(tmp_path: Path, clock: FakeClock) -> None:
    # An admin obtains a token whose claim says is_admin=True, then is demoted in
    # the DB while the ≤15-min token is still valid. require_admin re-loads the row.
    async with _auth_app(data_dir=tmp_path, clock=clock) as (client, app):
        admin_token, admin_id = await _register(client, "admin@example.com")
        await _set_admin(app, admin_id, is_admin=True)

        # Log in AFTER promotion so the JWT claim carries is_admin=True.
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        ok = await client.get("/api/v1/admin/users", headers=_bearer(token))
        assert ok.status_code == 200, ok.text

        # Demote in the DB; the still-valid token must no longer act as admin.
        await _set_admin(app, admin_id, is_admin=False)
        after = await client.get("/api/v1/admin/users", headers=_bearer(token))
    assert after.status_code == 403
    assert after.json()["code"] == "forbidden"


def test_admin_routes_absent_in_embedded_mode() -> None:
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]
    assert not any(path.startswith("/api/v1/admin") for path in paths)


def test_admin_routes_present_when_auth_active() -> None:
    paths = create_app(Settings(mode=DeploymentMode.SELFHOST)).openapi()["paths"]
    assert "/api/v1/admin/users" in paths
    assert "/api/v1/admin/reports" in paths
    assert "/api/v1/admin/stats" in paths
