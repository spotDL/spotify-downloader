"""Offline (in-memory SQLite) tests for the refresh-token + API-token repos.

Time flows through the ``clock`` fixture (a ``FakeClock``): every rotation,
revocation, and last-used stamp is an explicit ``now`` argument, so expiry and
ordering are deterministic without sleeping.
"""

from __future__ import annotations

import uuid

from spotdl_server.auth.tokens import new_pat, new_refresh_token, sha256_hex
from spotdl_server.repositories.tokens import ApiTokenRepository, RefreshTokenRepository
from spotdl_server.repositories.users import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeClock


async def _make_user(session: AsyncSession) -> uuid.UUID:
    user = await UserRepository(session).create(
        email=f"{uuid.uuid4().hex}@example.com", password_hash="h"
    )
    return user.id


class TestRefreshTokenRepository:
    async def test_create_then_get_by_hash(self, session: AsyncSession, clock: FakeClock) -> None:
        user_id = await _make_user(session)
        repo = RefreshTokenRepository(session)
        family = uuid.uuid4()
        token_hash = sha256_hex(new_refresh_token())

        created = await repo.create(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family,
            expires_at=clock.now(),
        )
        assert created.family_id == family
        assert created.rotated_at is None
        assert created.revoked_at is None

        found = await repo.get_by_hash(token_hash)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_hash_returns_none_when_absent(self, session: AsyncSession) -> None:
        repo = RefreshTokenRepository(session)
        assert await repo.get_by_hash(sha256_hex("missing")) is None

    async def test_mark_rotated_stamps_successor(
        self, session: AsyncSession, clock: FakeClock
    ) -> None:
        user_id = await _make_user(session)
        repo = RefreshTokenRepository(session)
        family = uuid.uuid4()
        old = await repo.create(
            user_id=user_id,
            token_hash=sha256_hex("old"),
            family_id=family,
            expires_at=clock.now(),
        )
        new = await repo.create(
            user_id=user_id,
            token_hash=sha256_hex("new"),
            family_id=family,
            expires_at=clock.now(),
        )

        clock.advance(60)
        await repo.mark_rotated(old, replaced_by=new.id, now=clock.now())

        assert old.rotated_at == clock.now()
        assert old.replaced_by == new.id

    async def test_revoke_marks_single_token(self, session: AsyncSession, clock: FakeClock) -> None:
        user_id = await _make_user(session)
        repo = RefreshTokenRepository(session)
        token = await repo.create(
            user_id=user_id,
            token_hash=sha256_hex("one"),
            family_id=uuid.uuid4(),
            expires_at=clock.now(),
        )
        clock.advance(5)
        await repo.revoke(token, now=clock.now())
        assert token.revoked_at == clock.now()

    async def test_revoke_family_counts_and_skips_already_revoked(
        self, session: AsyncSession, clock: FakeClock
    ) -> None:
        user_id = await _make_user(session)
        repo = RefreshTokenRepository(session)
        family = uuid.uuid4()
        tokens = [
            await repo.create(
                user_id=user_id,
                token_hash=sha256_hex(f"fam-{i}"),
                family_id=family,
                expires_at=clock.now(),
            )
            for i in range(3)
        ]
        # A token in a *different* family must not be touched.
        other = await repo.create(
            user_id=user_id,
            token_hash=sha256_hex("other-family"),
            family_id=uuid.uuid4(),
            expires_at=clock.now(),
        )
        # Pre-revoke one member of the target family; it must be skipped.
        await repo.revoke(tokens[0], now=clock.now())

        clock.advance(30)
        revoked = await repo.revoke_family(family, now=clock.now())
        assert revoked == 2  # only the two still-active members

        for tok in tokens:
            assert tok.revoked_at is not None
        assert other.revoked_at is None

        # A second sweep of the same family revokes nothing new.
        assert await repo.revoke_family(family, now=clock.now()) == 0

    async def test_revoke_family_empty_returns_zero(
        self, session: AsyncSession, clock: FakeClock
    ) -> None:
        repo = RefreshTokenRepository(session)
        assert await repo.revoke_family(uuid.uuid4(), now=clock.now()) == 0


class TestApiTokenRepository:
    async def test_create_then_get_by_hash(self, session: AsyncSession, clock: FakeClock) -> None:
        user_id = await _make_user(session)
        repo = ApiTokenRepository(session)
        full, prefix = new_pat()
        token_hash = sha256_hex(full)

        created = await repo.create(
            user_id=user_id,
            name="laptop",
            token_prefix=prefix,
            token_hash=token_hash,
            expires_at=None,
        )
        assert created.name == "laptop"
        assert created.token_prefix == prefix
        assert created.last_used_at is None
        assert created.revoked_at is None

        found = await repo.get_by_hash(token_hash)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_hash_returns_none_when_absent(self, session: AsyncSession) -> None:
        repo = ApiTokenRepository(session)
        assert await repo.get_by_hash(sha256_hex("nope")) is None

    async def test_list_for_user_includes_revoked_and_is_scoped(
        self, session: AsyncSession, clock: FakeClock
    ) -> None:
        user_a = await _make_user(session)
        user_b = await _make_user(session)
        repo = ApiTokenRepository(session)

        full1, prefix1 = new_pat()
        t1 = await repo.create(
            user_id=user_a,
            name="one",
            token_prefix=prefix1,
            token_hash=sha256_hex(full1),
            expires_at=None,
        )
        full2, prefix2 = new_pat()
        t2 = await repo.create(
            user_id=user_a,
            name="two",
            token_prefix=prefix2,
            token_hash=sha256_hex(full2),
            expires_at=None,
        )
        # A token owned by another user must not appear.
        full3, prefix3 = new_pat()
        await repo.create(
            user_id=user_b,
            name="other",
            token_prefix=prefix3,
            token_hash=sha256_hex(full3),
            expires_at=None,
        )
        await repo.revoke(t2, now=clock.now())

        listed = await repo.list_for_user(user_a)
        ids = {t.id for t in listed}
        assert ids == {t1.id, t2.id}  # revoked token still listed

    async def test_touch_last_used_updates_timestamp(
        self, session: AsyncSession, clock: FakeClock
    ) -> None:
        user_id = await _make_user(session)
        repo = ApiTokenRepository(session)
        full, prefix = new_pat()
        token = await repo.create(
            user_id=user_id,
            name="cli",
            token_prefix=prefix,
            token_hash=sha256_hex(full),
            expires_at=None,
        )
        assert token.last_used_at is None

        clock.advance(120)
        await repo.touch_last_used(token, now=clock.now())
        assert token.last_used_at == clock.now()

    async def test_revoke_marks_token(self, session: AsyncSession, clock: FakeClock) -> None:
        user_id = await _make_user(session)
        repo = ApiTokenRepository(session)
        full, prefix = new_pat()
        token = await repo.create(
            user_id=user_id,
            name="cli",
            token_prefix=prefix,
            token_hash=sha256_hex(full),
            expires_at=None,
        )
        clock.advance(10)
        await repo.revoke(token, now=clock.now())
        assert token.revoked_at == clock.now()

    async def test_get_owned_returns_token_for_owner(self, session: AsyncSession) -> None:
        user_id = await _make_user(session)
        repo = ApiTokenRepository(session)
        full, prefix = new_pat()
        token = await repo.create(
            user_id=user_id,
            name="cli",
            token_prefix=prefix,
            token_hash=sha256_hex(full),
            expires_at=None,
        )
        found = await repo.get_owned(token.id, user_id)
        assert found is not None
        assert found.id == token.id

    async def test_get_owned_returns_none_for_other_user(self, session: AsyncSession) -> None:
        owner = await _make_user(session)
        stranger = await _make_user(session)
        repo = ApiTokenRepository(session)
        full, prefix = new_pat()
        token = await repo.create(
            user_id=owner,
            name="cli",
            token_prefix=prefix,
            token_hash=sha256_hex(full),
            expires_at=None,
        )
        # Ownership guard: a stranger cannot address another user's token id.
        assert await repo.get_owned(token.id, stranger) is None

    async def test_get_owned_returns_none_for_missing_token(self, session: AsyncSession) -> None:
        user_id = await _make_user(session)
        repo = ApiTokenRepository(session)
        assert await repo.get_owned(uuid.uuid4(), user_id) is None
