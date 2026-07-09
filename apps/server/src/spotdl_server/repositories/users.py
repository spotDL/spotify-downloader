"""User + OAuth-identity repositories: the account-store data-access layer.

Two repositories back email+password and OAuth login:

* :class:`UserRepository` — the ``users`` table (the login identity is a
  *normalized* email; normalizing the address is the caller's job, so this repo
  stores and looks up whatever string it is handed).
* :class:`OAuthIdentityRepository` — the ``oauth_identities`` table linking a
  provider account (``github`` / ``discord``) to a local user.

Both accept a caller-owned :class:`~sqlalchemy.ext.asyncio.AsyncSession`, take
and return ORM models or plain values (never Pydantic/HTTP types), and never
commit — the service/unit-of-work owns the transaction. ``flush`` is used so a
newly-created row's server/Python-side defaults (its ``id``) are populated and
uniqueness violations surface as :class:`~sqlalchemy.exc.IntegrityError` at the
call site rather than at some later commit.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import OAuthProvider
from spotdl_server.db.models import OAuthIdentity, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Return the user with ``user_id``, or ``None`` if absent."""
        return await self.session.get(User, user_id)

    async def get_by_email(self, normalized_email: str) -> User | None:
        """Return the user whose email equals ``normalized_email`` exactly.

        The repository does no normalization: the caller must pass the same
        normalized form that was stored (store-normalized, look-up-normalized).
        """
        result = await self.session.execute(select(User).where(User.email == normalized_email))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str | None,
        display_name: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Insert a new user and return it (with its generated ``id``).

        ``password_hash`` is ``None`` for OAuth-only accounts. A duplicate email
        raises :class:`~sqlalchemy.exc.IntegrityError` from the ``uq_users_email``
        constraint at the flush below.
        """
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            is_admin=is_admin,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_password_hash(self, user: User, password_hash: str) -> None:
        """Replace ``user``'s stored password hash (e.g. a rehash upgrade)."""
        user.password_hash = password_hash
        await self.session.flush()

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        """Return ``(page, total)`` for the admin user list.

        ``page`` is ordered newest-first by ``created_at`` (stable-tiebroken by
        ``id``) and windowed by ``limit``/``offset``; ``total`` is the full row
        count, independent of the window, so the admin UI can paginate.
        """
        total = await self.session.scalar(select(func.count()).select_from(User)) or 0
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc(), User.id).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total


class OAuthIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_provider_account(
        self, provider: OAuthProvider, account_id: str
    ) -> OAuthIdentity | None:
        """Return the identity for ``(provider, account_id)``, or ``None``.

        This is the OAuth login lookup key (``uq_oauth_identities_provider_
        provider_account_id``); it is scoped to ``provider`` so the same account
        id under a different provider never collides.
        """
        result = await self.session.execute(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == provider,
                OAuthIdentity.provider_account_id == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def link(
        self,
        *,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        provider_account_id: str,
        provider_username: str | None,
    ) -> OAuthIdentity:
        """Link ``provider`` account ``provider_account_id`` to ``user_id``.

        Raises :class:`~sqlalchemy.exc.IntegrityError` if that provider account
        is already linked, or if the user already has an identity for this
        provider (the two ``oauth_identities`` unique constraints).
        """
        identity = OAuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_account_id=provider_account_id,
            provider_username=provider_username,
        )
        self.session.add(identity)
        await self.session.flush()
        return identity
