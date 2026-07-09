"""OAuth provider clients — pure httpx, no FastAPI/DB (CONTRACT — spec §6.2).

The authorization-code half of OAuth login lives here as a small protocol plus
two concrete clients. Each client is handed an injected
:class:`httpx.AsyncClient` (so ``respx`` intercepts every call and the default
test suite is fully offline) together with its provider credentials, which come
from ``Settings`` — never hardcoded. The clients speak only HTTP; they know
nothing about our database, sessions, or FastAPI, so :class:`OAuthService`
(services layer) can compose them without a layering violation and tests can
swap a fake implementing :class:`OAuthProviderClient`.

The three-step flow each client implements:

1. :meth:`~OAuthProviderClient.authorize_url` — the URL we send the user's
   browser to (carries our signed ``state`` and ``redirect_uri``).
2. :meth:`~OAuthProviderClient.exchange_code` — trade the returned ``code`` for a
   *provider* access token.
3. :meth:`~OAuthProviderClient.fetch_user_info` — read the account's stable id,
   email, and handle into a provider-agnostic :class:`OAuthUserInfo`.

GitHub requests ``read:user user:email`` and may need a second ``/user/emails``
call when the profile email is private; Discord requests ``identify email`` and
returns the email inline from ``/users/@me``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlencode

import httpx
from spotdl_core.providers import ProviderAuthError

from spotdl_server.db.enums import OAuthProvider


@dataclass(frozen=True)
class OAuthUserInfo:
    """The provider-agnostic account facts :class:`OAuthService` logs in with.

    ``provider_account_id`` is the provider's *stable* user id (the login lookup
    key, so a renamed handle still maps to the same local user); ``email`` is the
    verified account email or ``None`` when the provider withheld it (GitHub
    private-email accounts); ``username`` is the display handle, stored for the
    profile only.
    """

    provider_account_id: str
    email: str | None
    username: str | None


@runtime_checkable
class OAuthProviderClient(Protocol):
    """The authorization-code contract every provider client (and fake) meets."""

    provider: OAuthProvider

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        """Return the provider authorize URL carrying ``state`` + ``redirect_uri``."""
        ...

    async def exchange_code(self, *, code: str, redirect_uri: str) -> str:
        """Trade an authorization ``code`` for the provider's access token."""
        ...

    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo:
        """Read the authenticated account into an :class:`OAuthUserInfo`."""
        ...


def _require_token(payload: dict[str, Any], provider: OAuthProvider) -> str:
    """Return ``payload['access_token']`` or raise a provider-auth failure.

    A provider that rejects the code answers ``200`` with an ``error`` field (and
    no token), so a missing/empty token is a genuine auth failure, mapped to the
    502 ``provider_auth_error`` envelope rather than leaking as an unmapped 500.
    """
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise ProviderAuthError(f"{provider.value} token exchange returned no access token")
    return token


class GitHubOAuth:
    """GitHub authorization-code client (``read:user user:email`` scopes)."""

    provider = OAuthProvider.GITHUB
    _AUTHORIZE = "https://github.com/login/oauth/authorize"
    _TOKEN = "https://github.com/login/oauth/access_token"  # noqa: S105 - public endpoint URL
    _USER = "https://api.github.com/user"
    _EMAILS = "https://api.github.com/user/emails"
    _SCOPE = "read:user user:email"

    def __init__(self, *, client_id: str, client_secret: str, http: httpx.AsyncClient) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "scope": self._SCOPE,
                "state": state,
            }
        )
        return f"{self._AUTHORIZE}?{query}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> str:
        resp = await self._http.post(
            self._TOKEN,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return _require_token(resp.json(), self.provider)

    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        resp = await self._http.get(self._USER, headers=headers)
        resp.raise_for_status()
        profile = resp.json()
        email = profile.get("email")
        if not email:
            email = await self._primary_verified_email(headers)
        return OAuthUserInfo(
            provider_account_id=str(profile["id"]),
            email=email,
            username=profile.get("login"),
        )

    async def _primary_verified_email(self, headers: dict[str, str]) -> str | None:
        """Second call for a private profile: pick the primary *verified* email.

        GitHub only lets us log a user in under an address they have proven they
        own, so unverified entries are ignored; a verified primary wins, else the
        first verified address, else ``None`` (→ ``oauth_email_required``).
        """
        resp = await self._http.get(self._EMAILS, headers=headers)
        resp.raise_for_status()
        emails = [e for e in resp.json() if e.get("verified")]
        for entry in emails:
            if entry.get("primary"):
                return str(entry["email"])
        return str(emails[0]["email"]) if emails else None


class DiscordOAuth:
    """Discord authorization-code client (``identify email`` scopes)."""

    provider = OAuthProvider.DISCORD
    _AUTHORIZE = "https://discord.com/api/oauth2/authorize"
    _TOKEN = "https://discord.com/api/oauth2/token"  # noqa: S105 - public endpoint URL
    _USER = "https://discord.com/api/users/@me"
    _SCOPE = "identify email"

    def __init__(self, *, client_id: str, client_secret: str, http: httpx.AsyncClient) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": self._SCOPE,
                "state": state,
            }
        )
        return f"{self._AUTHORIZE}?{query}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> str:
        resp = await self._http.post(
            self._TOKEN,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return _require_token(resp.json(), self.provider)

    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo:
        resp = await self._http.get(self._USER, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        profile = resp.json()
        return OAuthUserInfo(
            provider_account_id=str(profile["id"]),
            email=profile.get("email"),
            username=profile.get("username"),
        )


def build_oauth_client(
    provider: OAuthProvider,
    *,
    client_id: str,
    client_secret: str,
    http: httpx.AsyncClient,
) -> OAuthProviderClient:
    """Construct the concrete client for ``provider`` (the assembly seam)."""
    if provider is OAuthProvider.GITHUB:
        return GitHubOAuth(client_id=client_id, client_secret=client_secret, http=http)
    if provider is OAuthProvider.DISCORD:
        return DiscordOAuth(client_id=client_id, client_secret=client_secret, http=http)
    raise ValueError(f"unsupported OAuth provider: {provider}")  # pragma: no cover - exhaustive
