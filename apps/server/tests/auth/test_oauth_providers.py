"""Offline tests for the concrete OAuth provider clients (respx-mocked HTTP).

Every provider call is faked with ``respx`` so the suite never touches
``github.com`` / ``discord.com``. ``respx.mock(assert_all_mocked=True)`` makes an
un-mocked request an error, proving no real network is used. Each concrete client
is handed an injected :class:`httpx.AsyncClient`, which is exactly what respx
intercepts. The tests pin the CONTRACT the ``OAuthService`` relies on: the
``authorize_url`` shape, the token-exchange POST, and the ``OAuthUserInfo`` parse
(GitHub's two-call private-email path; Discord's single call).
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from spotdl_core.providers import ProviderAuthError, ProviderUnavailable
from spotdl_server.auth.oauth_providers import (
    DiscordOAuth,
    GitHubOAuth,
    OAuthUserInfo,
    build_oauth_client,
)
from spotdl_server.db.enums import OAuthProvider

_REDIRECT = "https://api.spotdl.example/api/v1/auth/oauth/github/callback"


def test_build_oauth_client_dispatches_by_provider() -> None:
    http = httpx.AsyncClient()
    gh = build_oauth_client(
        OAuthProvider.GITHUB, client_id="gh-id", client_secret="gh-secret", http=http
    )
    disc = build_oauth_client(
        OAuthProvider.DISCORD, client_id="d-id", client_secret="d-secret", http=http
    )
    assert isinstance(gh, GitHubOAuth)
    assert isinstance(disc, DiscordOAuth)
    assert gh.provider is OAuthProvider.GITHUB
    assert disc.provider is OAuthProvider.DISCORD


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------


def test_github_authorize_url_shape() -> None:
    client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=httpx.AsyncClient())
    url = client.authorize_url(state="the-state", redirect_uri=_REDIRECT)
    parsed = urlparse(url)
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["gh-id"]
    assert params["redirect_uri"] == [_REDIRECT]
    assert params["state"] == ["the-state"]
    assert params["scope"] == ["read:user user:email"]


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_github_exchange_code_posts_and_returns_token(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "gho_abc", "token_type": "bearer"})
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        token = await client.exchange_code(code="the-code", redirect_uri=_REDIRECT)
    assert token == "gho_abc"
    posted = route.calls.last.request
    body = parse_qs(posted.content.decode())
    assert body["code"] == ["the-code"]
    assert body["client_id"] == ["gh-id"]
    assert body["client_secret"] == ["gh-secret"]
    assert body["redirect_uri"] == [_REDIRECT]


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_github_fetch_user_info_single_call(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200, json={"id": 42, "login": "octocat", "email": "octo@example.com"}
        )
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        info = await client.fetch_user_info(access_token="gho_abc")
    assert info == OAuthUserInfo(
        provider_account_id="42", email="octo@example.com", username="octocat"
    )


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_github_fetch_user_info_falls_back_to_emails_endpoint(
    respx_mock: respx.MockRouter,
) -> None:
    # Private profile email -> the /user payload has email=null, so the client
    # must make the second /user/emails call and pick the primary verified one.
    respx_mock.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"id": 7, "login": "ghost", "email": None})
    )
    respx_mock.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"email": "secondary@example.com", "primary": False, "verified": True},
                {"email": "primary@example.com", "primary": True, "verified": True},
            ],
        )
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        info = await client.fetch_user_info(access_token="gho_abc")
    assert info.provider_account_id == "7"
    assert info.username == "ghost"
    assert info.email == "primary@example.com"


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_github_fetch_user_info_no_verified_email_yields_none(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"id": 9, "login": "nomail", "email": None})
    )
    respx_mock.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200, json=[{"email": "unverified@example.com", "primary": True, "verified": False}]
        )
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        info = await client.fetch_user_info(access_token="gho_abc")
    assert info.email is None


@respx.mock(assert_all_mocked=True)
async def test_github_exchange_code_without_token_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "bad_verification_code"})
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        with pytest.raises(ProviderAuthError):
            await client.exchange_code(code="bad", redirect_uri=_REDIRECT)


@respx.mock(assert_all_mocked=True)
async def test_github_exchange_code_non_2xx_raises_provider_auth_error(
    respx_mock: respx.MockRouter,
) -> None:
    # A non-2xx from the token endpoint (e.g. a reused/expired code) must become a
    # mapped SpotdlError, not an unmapped httpx.HTTPStatusError leaking as a 500.
    respx_mock.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(400, json={"error": "bad_verification_code"})
    )
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        with pytest.raises(ProviderAuthError):
            await client.exchange_code(code="bad", redirect_uri=_REDIRECT)


@respx.mock(assert_all_mocked=True)
async def test_github_fetch_user_info_non_2xx_raises_provider_unavailable(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://api.github.com/user").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        with pytest.raises(ProviderUnavailable):
            await client.fetch_user_info(access_token="gho_abc")


@respx.mock(assert_all_mocked=True)
async def test_github_emails_endpoint_non_2xx_raises_provider_unavailable(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"id": 7, "login": "ghost", "email": None})
    )
    respx_mock.get("https://api.github.com/user/emails").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as http:
        client = GitHubOAuth(client_id="gh-id", client_secret="gh-secret", http=http)
        with pytest.raises(ProviderUnavailable):
            await client.fetch_user_info(access_token="gho_abc")


# --------------------------------------------------------------------------
# Discord
# --------------------------------------------------------------------------


def test_discord_authorize_url_shape() -> None:
    client = DiscordOAuth(client_id="d-id", client_secret="d-secret", http=httpx.AsyncClient())
    url = client.authorize_url(state="st", redirect_uri="https://api.spotdl.example/cb")
    parsed = urlparse(url)
    assert parsed.netloc == "discord.com"
    assert parsed.path == "/api/oauth2/authorize"
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["d-id"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == ["identify email"]
    assert params["state"] == ["st"]


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_discord_exchange_code_posts_form(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("https://discord.com/api/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "disc_tok"})
    )
    async with httpx.AsyncClient() as http:
        client = DiscordOAuth(client_id="d-id", client_secret="d-secret", http=http)
        token = await client.exchange_code(code="c", redirect_uri="https://api.spotdl.example/cb")
    assert token == "disc_tok"
    body = parse_qs(route.calls.last.request.content.decode())
    assert body["grant_type"] == ["authorization_code"]
    assert body["code"] == ["c"]


@respx.mock(assert_all_mocked=True, assert_all_called=True)
async def test_discord_fetch_user_info(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://discord.com/api/users/@me").mock(
        return_value=httpx.Response(
            200, json={"id": "1234567890", "username": "nick", "email": "nick@example.com"}
        )
    )
    async with httpx.AsyncClient() as http:
        client = DiscordOAuth(client_id="d-id", client_secret="d-secret", http=http)
        info = await client.fetch_user_info(access_token="disc_tok")
    assert info == OAuthUserInfo(
        provider_account_id="1234567890", email="nick@example.com", username="nick"
    )


@respx.mock(assert_all_mocked=True)
async def test_discord_exchange_code_non_2xx_raises_provider_auth_error(
    respx_mock: respx.MockRouter,
) -> None:
    # Discord answers a reused/expired code with a 400 invalid_grant — must map to
    # ProviderAuthError, not leak as an unmapped httpx.HTTPStatusError.
    respx_mock.post("https://discord.com/api/oauth2/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    async with httpx.AsyncClient() as http:
        client = DiscordOAuth(client_id="d-id", client_secret="d-secret", http=http)
        with pytest.raises(ProviderAuthError):
            await client.exchange_code(code="bad", redirect_uri="https://api.spotdl.example/cb")


@respx.mock(assert_all_mocked=True)
async def test_discord_fetch_user_info_non_2xx_raises_provider_unavailable(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://discord.com/api/users/@me").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as http:
        client = DiscordOAuth(client_id="d-id", client_secret="d-secret", http=http)
        with pytest.raises(ProviderUnavailable):
            await client.fetch_user_info(access_token="disc_tok")
