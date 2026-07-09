"""Offline unit tests for :class:`PatService` (spec §6.2 — PAT CONTRACT).

Personal access tokens are opaque secrets stored only as sha256 digests; the full
token is returned exactly once (on create) and never again. These tests pin that
once-shown behaviour, prove the digest — not the plaintext — is what is persisted,
and exercise the ownership-checked revoke (a stranger can never revoke, or even
address, another user's token). Time flows through the ``FakeClock`` fixture so
``revoked_at`` stamps are deterministic. The service flushes (never commits); the
in-memory ``session`` fixture owns the unit of work.
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_server.auth.tokens import sha256_hex
from spotdl_server.repositories.tokens import ApiTokenRepository
from spotdl_server.repositories.users import UserRepository
from spotdl_server.services.errors import TokenNotFound
from spotdl_server.services.pat import PatService
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock


async def _make_user(session: AsyncSession, email: str | None = None) -> uuid.UUID:
    user = await UserRepository(session).create(
        email=email or f"{uuid.uuid4().hex}@example.com", password_hash="h"
    )
    return user.id


def _service(session: AsyncSession, clock: FakeClock) -> PatService:
    return PatService(session=session, clock=clock, api_tokens=ApiTokenRepository(session))


async def test_create_returns_full_token_once_and_stores_only_the_hash(
    session: AsyncSession, clock: FakeClock
) -> None:
    user_id = await _make_user(session)
    svc = _service(session, clock)

    row, full = await svc.create(user_id=user_id, name="laptop")

    # The full secret is a ``spdl_pat_`` token, returned exactly once here.
    assert full.startswith("spdl_pat_")
    assert row.name == "laptop"
    # Only the digest + a short display prefix are persisted — never the plaintext.
    assert row.token_hash == sha256_hex(full)
    assert full not in row.token_hash
    assert row.token_prefix.startswith("spdl_pat_")
    assert full.startswith(row.token_prefix)
    assert row.expires_at is None
    assert row.revoked_at is None


async def test_create_persists_optional_expiry(session: AsyncSession, clock: FakeClock) -> None:
    user_id = await _make_user(session)
    svc = _service(session, clock)
    expires_at = clock.now()

    row, _full = await svc.create(user_id=user_id, name="ci", expires_at=expires_at)

    assert row.expires_at == expires_at


async def test_list_for_user_is_scoped_and_hides_no_rows(
    session: AsyncSession, clock: FakeClock
) -> None:
    owner = await _make_user(session)
    stranger = await _make_user(session)
    svc = _service(session, clock)
    row_a, _ = await svc.create(user_id=owner, name="one")
    row_b, _ = await svc.create(user_id=owner, name="two")
    await svc.create(user_id=stranger, name="other")

    listed = await svc.list_for_user(owner)

    assert {t.id for t in listed} == {row_a.id, row_b.id}


async def test_revoke_stamps_revoked_at(session: AsyncSession, clock: FakeClock) -> None:
    user_id = await _make_user(session)
    svc = _service(session, clock)
    row, _full = await svc.create(user_id=user_id, name="cli")
    assert row.revoked_at is None

    clock.advance(30)
    await svc.revoke(user_id=user_id, token_id=row.id)

    assert row.revoked_at == clock.now()


async def test_revoke_other_users_token_is_not_found_and_leaves_it_active(
    session: AsyncSession, clock: FakeClock
) -> None:
    owner = await _make_user(session)
    stranger = await _make_user(session)
    svc = _service(session, clock)
    row, _full = await svc.create(user_id=owner, name="owned")

    # Ownership guard: a stranger cannot revoke (or even address) another user's PAT.
    with pytest.raises(TokenNotFound):
        await svc.revoke(user_id=stranger, token_id=row.id)

    assert row.revoked_at is None  # the victim's token is untouched


async def test_revoke_missing_token_is_not_found(session: AsyncSession, clock: FakeClock) -> None:
    user_id = await _make_user(session)
    svc = _service(session, clock)
    with pytest.raises(TokenNotFound):
        await svc.revoke(user_id=user_id, token_id=uuid.uuid4())
