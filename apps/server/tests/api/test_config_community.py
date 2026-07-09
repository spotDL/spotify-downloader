"""Offline tests for the Plan 6 ``GET /config`` community extensions (spec §4).

The Plan 5 mode-default matrix lives in ``test_config.py``; this module covers the
community-layer additions: the explicit embedded opt-in (``auth_enabled=True``
honored even in EMBEDDED mode), the ``oauth_providers`` list reflecting configured
credentials, and the mount-time regression guard proving EMBEDDED mode exposes
**no** community route surface (the sibling of Plan 5's no-download-routes guard).

Everything is startup-fixed and DB-free: ``ConfigResponse`` derives purely from
``settings``, so a plain ``ASGITransport`` (no lifespan) plus the ``app.state``
stubs the HOSTED rate-limit middleware reads is all these tests need.
"""

from __future__ import annotations

import httpx
from pydantic import SecretStr
from spotdl_server.app import create_app
from spotdl_server.auth.clock import SystemClock
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.settings import DeploymentMode, Settings


def _client(settings: Settings) -> httpx.AsyncClient:
    app = create_app(settings)
    # Skip the lifespan (config flags are startup-fixed) but provide the
    # process-scoped state the rate-limit middleware reads where it is mounted.
    app.state.clock = SystemClock()
    app.state.rate_limiter = InMemoryRateLimiter(app.state.clock)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _config(settings: Settings) -> dict:  # type: ignore[type-arg]
    async with _client(settings) as client:
        resp = await client.get("/api/v1/config")
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_embedded_auth_opt_in_is_honored() -> None:
    """An operator can force auth on in EMBEDDED mode (opt-in overrides the default)."""
    body = await _config(
        Settings(
            mode=DeploymentMode.EMBEDDED,
            auth_enabled=True,
            auth_secret_key=SecretStr("config-community-secret-0123456789"),
        )
    )
    assert body["features"]["auth"] is True
    assert body["features"]["voting"] is True


async def test_voting_off_when_disabled_even_with_auth() -> None:
    """``voting`` requires accounts *and* the voting switch; disabling it wins."""
    body = await _config(
        Settings(mode=DeploymentMode.SELFHOST, voting_enabled=False),
    )
    assert body["features"]["auth"] is True
    assert body["features"]["voting"] is False


async def test_oauth_providers_reflect_configured_creds() -> None:
    """``oauth_providers`` lists only providers with both an id and a secret."""
    body = await _config(
        Settings(
            mode=DeploymentMode.SELFHOST,
            github_client_id="gh-id",
            github_client_secret=SecretStr("gh-secret"),
        )
    )
    assert body["oauth_providers"] == ["github"]


async def test_oauth_providers_empty_when_auth_inactive() -> None:
    """Even with creds set, EMBEDDED (auth inactive) reports no providers."""
    body = await _config(
        Settings(
            mode=DeploymentMode.EMBEDDED,
            github_client_id="gh-id",
            github_client_secret=SecretStr("gh-secret"),
        )
    )
    assert body["features"]["auth"] is False
    assert body["oauth_providers"] == []


def test_embedded_mounts_no_community_routes() -> None:
    """EMBEDDED (defaults) exposes the Plan 5 read surface but **no** community write
    surface: no ``auth``/``admin``/``reports`` routers, and no vote or match-submit
    routes. The mount-time embedded gate, the sibling of Plan 5's no-download guard.

    The router mount is resolved at ``create_app`` time; this FastAPI version
    *defers* ``include_router`` into opaque ``_IncludedRouter`` entries that expose
    no ``path`` on ``app.routes`` until the schema is built, so we introspect the
    mount-time-resolved public surface via ``openapi()["paths"]`` — the same
    mechanism every other community-gating test in this suite uses.
    """
    paths = create_app(Settings(mode=DeploymentMode.EMBEDDED)).openapi()["paths"]

    # No community router is mounted at all (auth / admin / reports prefixes).
    for forbidden_prefix in ("/api/v1/auth", "/api/v1/admin", "/api/v1/reports"):
        assert not any(path.startswith(forbidden_prefix) for path in paths), forbidden_prefix
    # No vote endpoints anywhere, and no match-submission (POST) route.
    assert not any(path.endswith("/vote") for path in paths)
    assert "post" not in paths.get("/api/v1/tracks/{id}/matches", {})

    # The Plan 5 read surface is still fully mounted (incl. the GET matches read).
    assert "/api/v1/config" in paths
    assert "/api/v1/resolve" in paths
    assert "get" in paths["/api/v1/tracks/{id}/matches"]
    assert "/api/v1/search" in paths
