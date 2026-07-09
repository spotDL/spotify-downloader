"""Offline (in-memory SQLite) tests for the user + OAuth-identity repositories.

Email normalization is the *caller's* job: these repositories store and look up
the email exactly as given, so every test stores an already-normalized value.
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.repositories.users import OAuthIdentityRepository, UserRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRepository:
    async def test_create_then_get_roundtrips(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        user = await repo.create(
            email="alice@example.com",
            password_hash="argon2id$fake",
            display_name="Alice",
        )
        assert user.id is not None
        assert user.is_admin is False
        assert user.is_active is True

        fetched = await repo.get(user.id)
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == "alice@example.com"
        assert fetched.display_name == "Alice"

    async def test_get_returns_none_when_absent(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        assert await repo.get(uuid.uuid4()) is None

    async def test_create_oauth_only_user_has_null_password_hash(
        self, session: AsyncSession
    ) -> None:
        repo = UserRepository(session)
        user = await repo.create(email="oauth@example.com", password_hash=None)
        assert user.password_hash is None

    async def test_create_admin_flag_honoured(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        user = await repo.create(email="root@example.com", password_hash="h", is_admin=True)
        assert user.is_admin is True

    async def test_get_by_email_looks_up_normalized_value(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        await repo.create(email="bob@example.com", password_hash="h")

        found = await repo.get_by_email("bob@example.com")
        assert found is not None
        assert found.email == "bob@example.com"
        # The repo does not normalize; a differently-cased key does not match.
        assert await repo.get_by_email("BOB@example.com") is None

    async def test_get_by_email_returns_none_when_absent(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        assert await repo.get_by_email("nobody@example.com") is None

    async def test_duplicate_email_raises_integrity_error(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        await repo.create(email="dup@example.com", password_hash="h")
        with pytest.raises(IntegrityError):
            await repo.create(email="dup@example.com", password_hash="h2")

    async def test_set_password_hash_upgrades_in_place(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        user = await repo.create(email="rehash@example.com", password_hash="old")

        await repo.set_password_hash(user, "new-argon2id-hash")
        assert user.password_hash == "new-argon2id-hash"

        refetched = await repo.get(user.id)
        assert refetched is not None
        assert refetched.password_hash == "new-argon2id-hash"

    async def test_list_users_returns_page_and_total(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        for i in range(5):
            await repo.create(email=f"u{i}@example.com", password_hash="h")

        page, total = await repo.list_users(limit=2, offset=0)
        assert total == 5
        assert len(page) == 2

        page2, total2 = await repo.list_users(limit=2, offset=4)
        assert total2 == 5
        assert len(page2) == 1

    async def test_list_users_empty(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        page, total = await repo.list_users(limit=10, offset=0)
        assert page == []
        assert total == 0


class TestOAuthIdentityRepository:
    async def _make_user(self, session: AsyncSession) -> uuid.UUID:
        user = await UserRepository(session).create(
            email=f"{uuid.uuid4().hex}@example.com", password_hash=None
        )
        return user.id

    async def test_link_then_get_by_provider_account(self, session: AsyncSession) -> None:
        user_id = await self._make_user(session)
        repo = OAuthIdentityRepository(session)

        identity = await repo.link(
            user_id=user_id,
            provider=OAuthProvider.GITHUB,
            provider_account_id="gh-12345",
            provider_username="octocat",
        )
        assert identity.user_id == user_id
        assert identity.provider is OAuthProvider.GITHUB

        found = await repo.get_by_provider_account(OAuthProvider.GITHUB, "gh-12345")
        assert found is not None
        assert found.id == identity.id
        assert found.provider_username == "octocat"

    async def test_get_by_provider_account_returns_none_when_absent(
        self, session: AsyncSession
    ) -> None:
        repo = OAuthIdentityRepository(session)
        assert await repo.get_by_provider_account(OAuthProvider.DISCORD, "nope") is None

    async def test_get_by_provider_account_is_scoped_to_provider(
        self, session: AsyncSession
    ) -> None:
        user_id = await self._make_user(session)
        repo = OAuthIdentityRepository(session)
        await repo.link(
            user_id=user_id,
            provider=OAuthProvider.GITHUB,
            provider_account_id="shared-id",
            provider_username=None,
        )
        # Same account id under a different provider must not match.
        assert await repo.get_by_provider_account(OAuthProvider.DISCORD, "shared-id") is None

    async def test_duplicate_provider_account_raises_integrity_error(
        self, session: AsyncSession
    ) -> None:
        user_a = await self._make_user(session)
        user_b = await self._make_user(session)
        repo = OAuthIdentityRepository(session)
        await repo.link(
            user_id=user_a,
            provider=OAuthProvider.GITHUB,
            provider_account_id="dupe",
            provider_username=None,
        )
        with pytest.raises(IntegrityError):
            await repo.link(
                user_id=user_b,
                provider=OAuthProvider.GITHUB,
                provider_account_id="dupe",
                provider_username=None,
            )
