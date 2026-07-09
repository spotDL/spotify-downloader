"""End-to-end (offline) tests for the rate-limit middleware.

The app is built through the real ``create_app`` seam with a fake registry and an
in-memory SQLite schema. After the lifespan starts, a ``FakeClock`` and an
``InMemoryRateLimiter`` bound to it are swapped onto ``app.state`` so window
resets are driven by ``clock.advance`` — fully deterministic, no ``sleep``.

These prove the four things the tier table promises on the wire: an anonymous IP
is throttled at ``anon_read`` (120/min) with a ``Retry-After`` header and the
``rate_limited`` envelope; a second IP is unaffected; the window resets after
60 s; an authenticated caller gets the far larger ``authed_read`` budget; the
public ``/auth/login`` endpoint is throttled at the stricter ``anon_auth``
(20/min); and a selfhost app (rate limiting inactive) never 429s — the
middleware is not even mounted.
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
from spotdl_server.app import create_app
from spotdl_server.auth.tokens import TokenService
from spotdl_server.db.base import Base
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock
from apps.server.tests.fakes import build_fake_registry

_SECRET = "ratelimit-test-secret-key-0123456789-abcdef"
_IP_HEADER = "x-forwarded-for"


@asynccontextmanager
async def _rl_app(
    *,
    data_dir: Path,
    clock: FakeClock,
    rate_limit_enabled: bool | None = True,
    mode: DeploymentMode = DeploymentMode.SELFHOST,
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=mode,
        data_dir=data_dir,
        auth_secret_key=SecretStr(_SECRET),
        rate_limit_enabled=rate_limit_enabled,
        client_ip_header=_IP_HEADER,
    )
    app = create_app(settings, registry=build_fake_registry())
    async with app.router.lifespan_context(app):
        # Deterministic time + an in-memory limiter bound to the same clock.
        app.state.clock = clock
        app.state.rate_limiter = InMemoryRateLimiter(clock)
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


def _headers(ip: str, *, bearer: str | None = None) -> dict[str, str]:
    headers = {_IP_HEADER: ip}
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    return headers


async def test_anonymous_reads_throttled_at_anon_read(tmp_path: Path, clock: FakeClock) -> None:
    async with _rl_app(data_dir=tmp_path, clock=clock) as (client, _app):
        # 120 requests fit inside the anon_read window.
        for _ in range(120):
            ok = await client.get("/api/v1/config", headers=_headers("1.1.1.1"))
            assert ok.status_code == 200

        blocked = await client.get("/api/v1/config", headers=_headers("1.1.1.1"))
        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"] == "60"
        body = blocked.json()
        assert body["code"] == "rate_limited"
        assert body["detail"] == {"limit": 120, "window": 60, "retry_after": 60}


async def test_second_ip_unaffected(tmp_path: Path, clock: FakeClock) -> None:
    async with _rl_app(data_dir=tmp_path, clock=clock) as (client, _app):
        for _ in range(121):
            await client.get("/api/v1/config", headers=_headers("1.1.1.1"))
        # A different client IP has its own untouched budget.
        other = await client.get("/api/v1/config", headers=_headers("2.2.2.2"))
        assert other.status_code == 200


async def test_window_resets_after_60s(tmp_path: Path, clock: FakeClock) -> None:
    async with _rl_app(data_dir=tmp_path, clock=clock) as (client, _app):
        for _ in range(120):
            await client.get("/api/v1/config", headers=_headers("1.1.1.1"))
        assert (await client.get("/api/v1/config", headers=_headers("1.1.1.1"))).status_code == 429

        clock.advance(60)  # window elapses -> fresh budget

        assert (await client.get("/api/v1/config", headers=_headers("1.1.1.1"))).status_code == 200


async def test_authenticated_caller_gets_authed_read_budget(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _rl_app(data_dir=tmp_path, clock=clock) as (client, _app):
        token = TokenService(secret=_SECRET, clock=clock).mint_access(
            user_id=uuid.uuid4(), is_admin=False
        )
        # 121 requests would 429 an anonymous IP (limit 120); an authenticated
        # caller (authed_read = 600) sails past.
        for _ in range(121):
            resp = await client.get("/api/v1/config", headers=_headers("1.1.1.1", bearer=token))
            assert resp.status_code == 200
        # And the remaining budget is exposed for clients that want it.
        assert int(resp.headers["X-RateLimit-Remaining"]) == 600 - 121


async def test_login_throttled_at_anon_auth(tmp_path: Path, clock: FakeClock) -> None:
    async with _rl_app(data_dir=tmp_path, clock=clock) as (client, _app):
        body = {"email": "nobody@example.com", "password": "wrongpassword"}
        # 20 attempts fit inside anon_auth; each is a normal 401 (bad creds).
        for _ in range(20):
            resp = await client.post("/api/v1/auth/login", json=body, headers=_headers("3.3.3.3"))
            assert resp.status_code == 401

        blocked = await client.post("/api/v1/auth/login", json=body, headers=_headers("3.3.3.3"))
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == {"limit": 20, "window": 60, "retry_after": 60}


async def test_inactive_rate_limiting_never_429s(tmp_path: Path, clock: FakeClock) -> None:
    # Selfhost default: rate_limit_active() is False, so the middleware is not
    # mounted and volume never matters.
    async with _rl_app(data_dir=tmp_path, clock=clock, rate_limit_enabled=None) as (client, app):
        assert app.state.settings.rate_limit_active() is False
        for _ in range(200):
            resp = await client.get("/api/v1/config", headers=_headers("1.1.1.1"))
            assert resp.status_code == 200


@pytest.mark.parametrize("path", ["/api/v1/config"])
async def test_hosted_default_activates_rate_limiting(
    tmp_path: Path, clock: FakeClock, path: str
) -> None:
    # Hosted mode activates rate limiting by default (no explicit flag).
    async with _rl_app(
        data_dir=tmp_path, clock=clock, rate_limit_enabled=None, mode=DeploymentMode.HOSTED
    ) as (client, app):
        assert app.state.settings.rate_limit_active() is True
        for _ in range(120):
            await client.get(path, headers=_headers("4.4.4.4"))
        assert (await client.get(path, headers=_headers("4.4.4.4"))).status_code == 429
