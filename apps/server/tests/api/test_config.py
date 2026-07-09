"""Offline tests for ``GET /api/v1/config`` (spec §4 feature gating).

``config`` needs no DB or provider I/O — the feature flags are computed from
``settings.mode`` (a startup-fixed value), so a plain ASGITransport (no lifespan)
suffices (the process-scoped ``clock``/``rate_limiter`` the HOSTED rate-limit
middleware reads are set directly on ``app.state`` in lieu of the lifespan).
Downloads + library are on for selfhost/embedded, off for hosted; auth
+ voting are now *computed* (Plan 6): active for hosted/selfhost, off in embedded
by default (spec §4: embedded auth = "none (loopback only)"). ``oauth_providers``
lists the configured providers (empty when auth is inactive or none are set) and
``matcher_version`` is always present. The auth-active override + oauth-provider
cases live in ``test_config_community.py``.
"""

from __future__ import annotations

import httpx
from spotdl_core.matching import MATCHER_V5_DEFAULT
from spotdl_server.app import create_app
from spotdl_server.auth.clock import SystemClock
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.settings import DeploymentMode, Settings


def _client(mode: DeploymentMode) -> httpx.AsyncClient:
    app = create_app(Settings(mode=mode))
    # This test skips the lifespan (config flags are startup-fixed), so provide
    # the process-scoped state the rate-limit middleware reads in HOSTED mode
    # where it is mounted (built by the lifespan in production).
    app.state.clock = SystemClock()
    app.state.rate_limiter = InMemoryRateLimiter(app.state.clock)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _config(mode: DeploymentMode) -> dict:  # type: ignore[type-arg]
    async with _client(mode) as client:
        resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    return resp.json()


async def test_config_selfhost() -> None:
    body = await _config(DeploymentMode.SELFHOST)
    assert body["mode"] == "selfhost"
    assert body["features"] == {
        "downloads": True,
        "library": True,
        "auth": True,
        "voting": True,
    }
    # No OAuth creds configured → empty list even though auth is active.
    assert body["oauth_providers"] == []
    assert body["matcher_version"] == MATCHER_V5_DEFAULT.matcher_version


async def test_config_hosted() -> None:
    body = await _config(DeploymentMode.HOSTED)
    assert body["mode"] == "hosted"
    # Hosted disables local downloads/library but keeps auth + voting on.
    assert body["features"]["downloads"] is False
    assert body["features"]["library"] is False
    assert body["features"]["auth"] is True
    assert body["features"]["voting"] is True
    assert body["oauth_providers"] == []
    assert body["matcher_version"] == MATCHER_V5_DEFAULT.matcher_version


async def test_config_embedded() -> None:
    body = await _config(DeploymentMode.EMBEDDED)
    assert body["mode"] == "embedded"
    assert body["features"]["downloads"] is True
    assert body["features"]["library"] is True
    # Embedded (loopback) has no auth surface by default → voting off, no OAuth.
    assert body["features"]["auth"] is False
    assert body["features"]["voting"] is False
    assert body["oauth_providers"] == []
