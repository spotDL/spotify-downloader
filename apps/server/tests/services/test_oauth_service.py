"""Offline unit tests for :class:`OAuthService` (login-or-register + linking).

No provider network: a :class:`FakeOAuthProvider` implements the
``OAuthProviderClient`` protocol and returns a canned :class:`OAuthUserInfo`, so
the whole login-or-register + identity-linking state machine is exercised against
an in-memory SQLite session with a ``FakeClock``. State (CSRF) signing is real —
the service signs and verifies its own stateless HMAC token — so tampering is
tested end to end without any DB row for state.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from spotdl_server.auth.oauth_providers import OAuthUserInfo
from spotdl_server.auth.tokens import TokenService
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.repositories.tokens import RefreshTokenRepository
from spotdl_server.repositories.users import OAuthIdentityRepository, UserRepository
from spotdl_server.services.auth import AuthService, TokenPair
from spotdl_server.services.errors import InvalidToken, OAuthEmailRequired
from spotdl_server.services.oauth import OAuthService, sign_state, verify_state
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock

_SECRET = "oauth-unit-test-secret-key-0123456789-abcdef"
_REDIRECT_BASE = "https://api.spotdl.example"


class FakeOAuthProvider:
    """A protocol-satisfying provider client returning canned data (no network)."""

    def __init__(
        self,
        *,
        provider: OAuthProvider = OAuthProvider.GITHUB,
        info: OAuthUserInfo,
        token: str = "fake-provider-token",
    ) -> None:
        self.provider = provider
        self._info = info
        self._token = token
        self.exchanged: list[tuple[str, str]] = []

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        return f"https://fake.example/authorize?state={state}&redirect_uri={redirect_uri}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> str:
        self.exchanged.append((code, redirect_uri))
        return self._token

    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo:
        return self._info


def _service(session: AsyncSession, clock: FakeClock, provider: FakeOAuthProvider) -> OAuthService:
    token_service = TokenService(secret=_SECRET, clock=clock)
    return OAuthService(
        session=session,
        token_service=token_service,
        clock=clock,
        users=UserRepository(session),
        identities=OAuthIdentityRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
        clients={provider.provider: provider},
        auth_secret=_SECRET,
        redirect_base_url=_REDIRECT_BASE,
    )


def _auth_service(session: AsyncSession, clock: FakeClock) -> AuthService:
    return AuthService(
        session=session,
        token_service=TokenService(secret=_SECRET, clock=clock),
        clock=clock,
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )


def _state_from_authorize_url(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


# --------------------------------------------------------------------------
# state (CSRF) signing
# --------------------------------------------------------------------------


def test_sign_and_verify_state_round_trip(clock: FakeClock) -> None:
    state = sign_state(secret=_SECRET, clock=clock)
    verify_state(state, secret=_SECRET, clock=clock)  # does not raise


def test_verify_state_rejects_tampered_signature(clock: FakeClock) -> None:
    state = sign_state(secret=_SECRET, clock=clock)
    payload, _, _sig = state.partition(".")
    with pytest.raises(InvalidToken):
        verify_state(f"{payload}.deadbeef", secret=_SECRET, clock=clock)


def test_verify_state_rejects_wrong_secret(clock: FakeClock) -> None:
    state = sign_state(secret=_SECRET, clock=clock)
    with pytest.raises(InvalidToken):
        verify_state(state, secret="a-different-secret-entirely-1234567890", clock=clock)


def test_verify_state_rejects_expired(clock: FakeClock) -> None:
    state = sign_state(secret=_SECRET, clock=clock, ttl=600)
    clock.advance(601)
    with pytest.raises(InvalidToken):
        verify_state(state, secret=_SECRET, clock=clock)


def test_verify_state_rejects_malformed(clock: FakeClock) -> None:
    with pytest.raises(InvalidToken):
        verify_state("not-a-valid-state", secret=_SECRET, clock=clock)


# --------------------------------------------------------------------------
# authorize_url
# --------------------------------------------------------------------------


def test_authorize_url_signs_a_verifiable_state(session: AsyncSession, clock: FakeClock) -> None:
    provider = FakeOAuthProvider(info=OAuthUserInfo("1", "a@example.com", "a"))
    svc = _service(session, clock, provider)
    url = svc.authorize_url(OAuthProvider.GITHUB)
    state = _state_from_authorize_url(url)
    verify_state(state, secret=_SECRET, clock=clock)  # the state the URL carries verifies


# --------------------------------------------------------------------------
# complete: login-or-register + linking
# --------------------------------------------------------------------------


async def _complete(svc: OAuthService, clock: FakeClock, provider: OAuthProvider) -> TokenPair:
    state = sign_state(secret=_SECRET, clock=clock)
    return await svc.complete(provider, code="the-code", state=state)


async def test_new_account_creates_user_and_identity(
    session: AsyncSession, clock: FakeClock
) -> None:
    provider = FakeOAuthProvider(
        info=OAuthUserInfo(provider_account_id="gh-1", email="new@example.com", username="newbie")
    )
    svc = _service(session, clock, provider)
    pair = await _complete(svc, clock, OAuthProvider.GITHUB)
    assert isinstance(pair, TokenPair)
    assert pair.access_token and pair.refresh_token
    assert pair.user.email == "new@example.com"
    assert pair.user.password_hash is None  # OAuth-only account
    identity = await OAuthIdentityRepository(session).get_by_provider_account(
        OAuthProvider.GITHUB, "gh-1"
    )
    assert identity is not None
    assert identity.user_id == pair.user.id
    assert identity.provider_username == "newbie"
    expected_redirect = f"{_REDIRECT_BASE}/api/v1/auth/oauth/github/callback"
    assert provider.exchanged == [("the-code", expected_redirect)]


async def test_second_login_same_account_reuses_user(
    session: AsyncSession, clock: FakeClock
) -> None:
    provider = FakeOAuthProvider(
        info=OAuthUserInfo(provider_account_id="gh-1", email="dup@example.com", username="dup")
    )
    svc = _service(session, clock, provider)
    first = await _complete(svc, clock, OAuthProvider.GITHUB)
    second = await _complete(svc, clock, OAuthProvider.GITHUB)
    assert first.user.id == second.user.id
    users, total = await UserRepository(session).list_users(limit=10, offset=0)
    assert total == 1


async def test_provider_email_links_to_existing_password_user(
    session: AsyncSession, clock: FakeClock
) -> None:
    # A pre-existing email+password account with the same (normalized) email as
    # the provider returns: the OAuth identity is *linked* to that user, not a
    # second account.
    auth = _auth_service(session, clock)
    registered = await auth.register(email="linkme@example.com", password="password123")
    provider = FakeOAuthProvider(
        info=OAuthUserInfo(
            provider_account_id="gh-42", email="LinkMe@Example.com", username="linker"
        )
    )
    svc = _service(session, clock, provider)
    pair = await _complete(svc, clock, OAuthProvider.GITHUB)
    assert pair.user.id == registered.user.id  # linked, not duplicated
    identity = await OAuthIdentityRepository(session).get_by_provider_account(
        OAuthProvider.GITHUB, "gh-42"
    )
    assert identity is not None
    assert identity.user_id == registered.user.id


async def test_bad_state_raises_invalid_token(session: AsyncSession, clock: FakeClock) -> None:
    provider = FakeOAuthProvider(info=OAuthUserInfo("gh-1", "x@example.com", "x"))
    svc = _service(session, clock, provider)
    with pytest.raises(InvalidToken):
        await svc.complete(OAuthProvider.GITHUB, code="c", state="tampered.state")


async def test_provider_without_email_raises_oauth_email_required(
    session: AsyncSession, clock: FakeClock
) -> None:
    provider = FakeOAuthProvider(
        info=OAuthUserInfo(provider_account_id="gh-noemail", email=None, username="private")
    )
    svc = _service(session, clock, provider)
    with pytest.raises(OAuthEmailRequired):
        await _complete(svc, clock, OAuthProvider.GITHUB)
    # No account was created for the emailless login.
    _users, total = await UserRepository(session).list_users(limit=10, offset=0)
    assert total == 0
