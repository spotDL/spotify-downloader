"""End-to-end (offline) tests for the ``/api/v1/auth/oauth`` router.

The app is built through the real ``create_app`` seam with GitHub OAuth
*configured* (so the router mounts) but the provider-client dependency
*overridden* with an in-memory fake — no GitHub network, no respx even. A
``FakeClock`` on ``app.state.clock`` makes state expiry deterministic and the
auth secret comes from ``Settings`` (never hardcoded in source). The tests pin
the dual-mode callback CONTRACT: JSON mode (CLI / generated clients / existing
tests) is unchanged, and browser-handoff mode 302-redirects to the SPA with the
token pair in the URL *fragment* (never the query string).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from spotdl_server.api.deps import build_oauth_clients
from spotdl_server.app import create_app
from spotdl_server.auth.oauth_providers import OAuthUserInfo
from spotdl_server.db.base import Base
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeClock, precreate_schema
from apps.server.tests.fakes import build_fake_registry

_ACCESS_TTL = 900
_SECRET = "oauth-api-test-secret-key-0123456789-abcdef"
_HTML_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
_JSON_ACCEPT = "application/json"


class _FakeGitHub:
    provider = OAuthProvider.GITHUB

    def __init__(self, info: OAuthUserInfo) -> None:
        self._info = info

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        return f"https://fake.example/authorize?state={state}&redirect_uri={redirect_uri}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> str:
        return "fake-provider-token"

    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo:
        return self._info


_DEFAULT_INFO = OAuthUserInfo(provider_account_id="gh-1", email="octo@example.com", username="octo")


@asynccontextmanager
async def _oauth_app(
    *,
    data_dir: Path,
    clock: FakeClock,
    info: OAuthUserInfo = _DEFAULT_INFO,
    spa_base_url: str | None = None,
    web_auth_redirect_enabled: bool | None = None,
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    settings = Settings(
        mode=DeploymentMode.HOSTED,
        data_dir=data_dir,
        auth_secret_key=SecretStr(_SECRET),
        access_token_ttl_seconds=_ACCESS_TTL,
        github_client_id="gh-id",
        github_client_secret=SecretStr("gh-secret"),
        oauth_redirect_base_url="https://api.spotdl.example",
        spa_base_url=spa_base_url,
        web_auth_redirect_enabled=web_auth_redirect_enabled,
        rate_limit_enabled=False,
    )
    await precreate_schema(settings)
    app = create_app(settings, registry=build_fake_registry())
    app.dependency_overrides[build_oauth_clients] = lambda: {
        OAuthProvider.GITHUB: _FakeGitHub(info)
    }
    async with app.router.lifespan_context(app):
        app.state.clock = clock
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


async def _authorize_state(client: httpx.AsyncClient) -> str:
    resp = await client.get(
        "/api/v1/auth/oauth/github/authorize?json=true", headers={"Accept": _JSON_ACCEPT}
    )
    assert resp.status_code == 200, resp.text
    authorize_url = resp.json()["authorize_url"]
    return parse_qs(urlparse(authorize_url).query)["state"][0]


# --------------------------------------------------------------------------
# authorize
# --------------------------------------------------------------------------


async def test_authorize_json_returns_url_with_signed_state(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/authorize?json=true", headers={"Accept": _JSON_ACCEPT}
        )
        assert resp.status_code == 200, resp.text
        url = resp.json()["authorize_url"]
        params = parse_qs(urlparse(url).query)
        assert params["state"][0]  # a signed state is present


async def test_authorize_redirects_by_default(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get("/api/v1/auth/oauth/github/authorize")
    assert resp.status_code == 307
    assert "state=" in resp.headers["location"]


async def test_authorize_unknown_provider_is_404(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get("/api/v1/auth/oauth/discord/authorize?json=true")
    assert resp.status_code == 404


# --------------------------------------------------------------------------
# callback — JSON mode
# --------------------------------------------------------------------------


async def test_callback_json_mode_returns_token_response(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _JSON_ACCEPT},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == _ACCESS_TTL
    assert body["user"]["email"] == "octo@example.com"


async def test_callback_json_mode_tampered_state_is_invalid_token(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/callback?code=abc&state=tampered.state",
            headers={"Accept": _JSON_ACCEPT},
        )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"


async def test_callback_disabled_provider_is_404(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/discord/callback?code=abc&state=x",
            headers={"Accept": _JSON_ACCEPT},
        )
    assert resp.status_code == 404


async def test_callback_json_mode_no_email_is_oauth_email_required(
    tmp_path: Path, clock: FakeClock
) -> None:
    info = OAuthUserInfo(provider_account_id="gh-priv", email=None, username="priv")
    async with _oauth_app(data_dir=tmp_path, clock=clock, info=info) as (client, _app):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _JSON_ACCEPT},
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == "oauth_email_required"


# --------------------------------------------------------------------------
# callback — browser-handoff mode
# --------------------------------------------------------------------------


async def test_callback_browser_handoff_same_origin(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    location = resp.headers["location"]
    split = urlparse(location)
    assert location.startswith("/auth/callback/github")
    assert split.query == ""  # no token in the query string
    frag = parse_qs(split.fragment)
    assert frag["access_token"][0]
    assert frag["refresh_token"][0]
    assert frag["token_type"] == ["bearer"]
    assert frag["expires_in"] == [str(_ACCESS_TTL)]


async def test_callback_browser_handoff_with_spa_base_url(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock, spa_base_url="https://app.example") as (
        client,
        _app,
    ):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://app.example/auth/callback/github#")


async def test_callback_browser_handoff_state_mismatch(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/callback?code=abc&state=tampered.state",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("/auth/callback/github#")
    frag = parse_qs(urlparse(location).fragment)
    assert frag == {"error": ["oauth_state_mismatch"]}
    assert "access_token" not in frag


async def test_callback_browser_handoff_email_required(tmp_path: Path, clock: FakeClock) -> None:
    info = OAuthUserInfo(provider_account_id="gh-priv", email=None, username="priv")
    async with _oauth_app(data_dir=tmp_path, clock=clock, info=info) as (client, _app):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    frag = parse_qs(urlparse(resp.headers["location"]).fragment)
    assert frag == {"error": ["oauth_email_required"]}


async def test_callback_browser_handoff_provider_denied(tmp_path: Path, clock: FakeClock) -> None:
    # A consent denial is a standard OAuth2 redirect: ?error=access_denied&state=...
    # with NO code. The browser must still be handed off to the SPA, never 422'd.
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/callback?error=access_denied&state=whatever",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("/auth/callback/github#")
    frag = parse_qs(urlparse(location).fragment)
    assert frag == {"error": ["provider_auth_error"]}
    assert "access_token" not in frag


async def test_callback_json_mode_provider_denied(tmp_path: Path, clock: FakeClock) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/callback?error=access_denied&state=whatever",
            headers={"Accept": _JSON_ACCEPT},
        )
    assert resp.status_code == 502
    assert resp.json()["code"] == "provider_auth_error"


async def test_callback_missing_code_handed_off_not_422(tmp_path: Path, clock: FakeClock) -> None:
    # A browser hitting the callback with neither code nor error must not get a
    # raw 422 validation body; it is routed through the graceful handoff.
    async with _oauth_app(data_dir=tmp_path, clock=clock) as (client, _app):
        resp = await client.get(
            "/api/v1/auth/oauth/github/callback",
            headers={"Accept": _HTML_ACCEPT},
        )
    assert resp.status_code == 302
    frag = parse_qs(urlparse(resp.headers["location"]).fragment)
    assert frag == {"error": ["provider_auth_error"]}


async def test_web_auth_redirect_disabled_forces_json_for_browser(
    tmp_path: Path, clock: FakeClock
) -> None:
    async with _oauth_app(data_dir=tmp_path, clock=clock, web_auth_redirect_enabled=False) as (
        client,
        _app,
    ):
        state = await _authorize_state(client)
        resp = await client.get(
            f"/api/v1/auth/oauth/github/callback?code=abc&state={state}",
            headers={"Accept": _HTML_ACCEPT},  # browser-like, but toggle forces JSON
        )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


# --------------------------------------------------------------------------
# mount gating
# --------------------------------------------------------------------------


def test_oauth_router_absent_without_providers() -> None:
    paths = create_app(
        Settings(mode=DeploymentMode.HOSTED, auth_secret_key=SecretStr("x"))
    ).openapi()["paths"]
    assert not any("/oauth/" in path for path in paths)


def test_oauth_router_absent_in_embedded_mode() -> None:
    paths = create_app(
        Settings(
            mode=DeploymentMode.EMBEDDED,
            github_client_id="gh-id",
            github_client_secret=SecretStr("gh-secret"),
        )
    ).openapi()["paths"]
    assert not any("/oauth/" in path for path in paths)


@pytest.mark.parametrize("mode", [DeploymentMode.SELFHOST, DeploymentMode.HOSTED])
def test_oauth_router_mounted_when_provider_configured(mode: DeploymentMode) -> None:
    paths = create_app(
        Settings(
            mode=mode,
            auth_secret_key=SecretStr("x"),
            github_client_id="gh-id",
            github_client_secret=SecretStr("gh-secret"),
        )
    ).openapi()["paths"]
    assert "/api/v1/auth/oauth/{provider}/authorize" in paths
    assert "/api/v1/auth/oauth/{provider}/callback" in paths
