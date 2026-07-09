"""Offline unit tests for :class:`AuthService` (spec §6.2 — auth CONTRACT).

The whole suite is offline and time is controlled by the ``FakeClock`` fixture:
every token expiry and refresh rotation reads *now* through the injected clock,
so the reuse-detection state machine and the 30-day refresh expiry are exercised
deterministically without sleeping. A single in-memory ``session`` fixture backs
each test; the service flushes (never commits) so rotated/revoked rows are
visible within the unit of work exactly as they would be after a real request's
``get_session`` commit.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from spotdl_server.auth.context import ANONYMOUS, AuthContext
from spotdl_server.auth.tokens import TokenService
from spotdl_server.repositories.tokens import RefreshTokenRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.services.auth import AuthService, TokenPair
from spotdl_server.services.errors import (
    EmailTaken,
    InvalidCredentials,
    InvalidToken,
    TokenExpired,
)
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock

_SECRET = "unit-test-secret-key-0123456789-abcdef"  # ≥32 bytes (HS256 recommended min)
_REFRESH_TTL = 2_592_000  # 30 days (contract default)


def _service(session: AsyncSession, clock: FakeClock) -> AuthService:
    token_service = TokenService(secret=_SECRET, clock=clock, refresh_ttl_s=_REFRESH_TTL)
    return AuthService(
        session=session,
        token_service=token_service,
        clock=clock,
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )


# --------------------------------------------------------------------------
# AuthContext value type (CONTRACT)
# --------------------------------------------------------------------------


def test_auth_context_authenticated_flag() -> None:
    assert ANONYMOUS.kind == "anonymous"
    assert ANONYMOUS.authenticated is False
    user_ctx = AuthContext(kind="user", user_id=uuid4(), is_admin=True)
    assert user_ctx.authenticated is True
    assert user_ctx.is_admin is True
    pat_ctx = AuthContext(kind="pat", user_id=uuid4(), token_id=uuid4())
    assert pat_ctx.authenticated is True


# --------------------------------------------------------------------------
# register / login
# --------------------------------------------------------------------------


async def test_register_normalizes_email_and_returns_pair(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="  User@Example.COM ", password="password123")
    assert isinstance(pair, TokenPair)
    assert pair.access_token
    assert pair.refresh_token
    assert pair.user.email == "user@example.com"  # trimmed + casefolded
    assert pair.user.password_hash is not None
    assert "password123" not in pair.user.password_hash  # stored hashed, not plain


async def test_register_then_login_round_trip(session: AsyncSession, clock: FakeClock) -> None:
    svc = _service(session, clock)
    registered = await svc.register(email="user@example.com", password="password123")
    logged_in = await svc.login(email="USER@example.com", password="password123")
    assert logged_in.user.id == registered.user.id
    assert logged_in.access_token
    assert logged_in.refresh_token != registered.refresh_token  # a new family per login


async def test_duplicate_register_raises_email_taken(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    await svc.register(email="dup@example.com", password="password123")
    with pytest.raises(EmailTaken):
        await svc.register(email="Dup@Example.com", password="password123")


async def test_wrong_password_and_unknown_email_are_indistinguishable(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    await svc.register(email="a@example.com", password="password123")
    with pytest.raises(InvalidCredentials) as wrong:
        await svc.login(email="a@example.com", password="not-the-password")
    with pytest.raises(InvalidCredentials) as unknown:
        await svc.login(email="nobody@example.com", password="password123")
    # No user enumeration: the two failures carry the identical message.
    assert str(wrong.value) == str(unknown.value)


async def test_inactive_user_login_rejected(session: AsyncSession, clock: FakeClock) -> None:
    svc = _service(session, clock)
    users = UserRepository(session)
    registered = await svc.register(email="ban@example.com", password="password123")
    banned = await users.get(registered.user.id)
    assert banned is not None
    banned.is_active = False
    await session.flush()
    with pytest.raises(InvalidCredentials):
        await svc.login(email="ban@example.com", password="password123")


async def test_login_upgrades_hash_when_needs_rehash(
    session: AsyncSession, clock: FakeClock
) -> None:
    # Seed a user whose stored hash was produced under weaker-than-current params.
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("password123")
    user = await UserRepository(session).create(email="rehash@example.com", password_hash=weak)
    svc = _service(session, clock)
    await svc.login(email="rehash@example.com", password="password123")
    refreshed = await UserRepository(session).get(user.id)
    assert refreshed is not None
    assert refreshed.password_hash != weak  # transparently re-hashed on login


# --------------------------------------------------------------------------
# refresh rotation + reuse detection (CONTRACT state machine)
# --------------------------------------------------------------------------


async def test_refresh_rotates_and_successor_works(session: AsyncSession, clock: FakeClock) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="rot@example.com", password="password123")
    first = await svc.refresh(refresh_token=pair.refresh_token)
    assert first.refresh_token != pair.refresh_token
    # The freshly-minted successor is itself refreshable (sliding window).
    second = await svc.refresh(refresh_token=first.refresh_token)
    assert second.refresh_token != first.refresh_token
    assert second.access_token


async def test_reuse_of_spent_token_revokes_whole_family(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="reuse@example.com", password="password123")
    successor = await svc.refresh(refresh_token=pair.refresh_token)  # spends the original
    # Re-presenting the spent (rotated) original trips reuse detection.
    with pytest.raises(InvalidToken):
        await svc.refresh(refresh_token=pair.refresh_token)
    # The previously-valid successor is now revoked along with the whole family.
    with pytest.raises(InvalidToken):
        await svc.refresh(refresh_token=successor.refresh_token)


async def test_unknown_refresh_token_is_invalid(session: AsyncSession, clock: FakeClock) -> None:
    svc = _service(session, clock)
    with pytest.raises(InvalidToken):
        await svc.refresh(refresh_token="never-issued")


async def test_expired_refresh_token_raises_token_expired(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="exp@example.com", password="password123")
    clock.advance(_REFRESH_TTL + 1)
    with pytest.raises(TokenExpired):
        await svc.refresh(refresh_token=pair.refresh_token)


# --------------------------------------------------------------------------
# logout (idempotent family revoke) + get_me
# --------------------------------------------------------------------------


async def test_logout_revokes_family_and_is_idempotent(
    session: AsyncSession, clock: FakeClock
) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="out@example.com", password="password123")
    await svc.logout(refresh_token=pair.refresh_token)
    with pytest.raises(InvalidToken):
        await svc.refresh(refresh_token=pair.refresh_token)
    # A second logout of the same token is a no-op, not an error.
    await svc.logout(refresh_token=pair.refresh_token)
    # Logging out an unknown token is also a silent no-op.
    await svc.logout(refresh_token="never-issued")


async def test_get_me_returns_the_user(session: AsyncSession, clock: FakeClock) -> None:
    svc = _service(session, clock)
    pair = await svc.register(email="me@example.com", password="password123")
    me = await svc.get_me(pair.user.id)
    assert me.id == pair.user.id
    assert me.email == "me@example.com"
