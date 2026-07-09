"""Refresh-token + API-token repositories: the credential-store data layer.

Both token kinds are **opaque secrets stored only as sha256 hex digests** — the
plaintext token never touches the database. These repositories deal purely in
hashes and ORM rows; minting the secrets and computing digests lives in
:mod:`spotdl_server.auth.tokens`.

* :class:`RefreshTokenRepository` — rotating, reuse-detecting refresh tokens.
  A token belongs to a ``family_id`` lineage; consuming one *rotates* it
  (stamps ``rotated_at`` + ``replaced_by``), and detecting reuse of an already
  rotated/revoked token *revokes the whole family*. :meth:`get_by_hash` takes a
  ``FOR UPDATE`` row lock on Postgres (silently a no-op on SQLite) so the
  compare-and-rotate in the auth service is race-free under concurrent refreshes.
* :class:`ApiTokenRepository` — personal access tokens (PATs) for the CLI, with
  an ownership-scoped lookup (:meth:`get_owned`) so one user can never address
  another user's token by id.

Every time-dependent mutation takes an explicit ``now`` (from the injected
:class:`~spotdl_server.auth.clock.Clock`) rather than reading the wall clock, so
expiry and rotation are deterministic in tests. Repositories never commit; the
caller owns the unit of work.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import ApiToken, RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        """Insert a refresh-token row (storing only the ``token_hash``)."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the refresh token with ``token_hash``, or ``None``.

        Locks the row ``FOR UPDATE`` so the auth service's read-then-rotate is
        atomic under concurrency. On SQLite the lock clause is silently dropped
        (the whole DB is already single-writer), so the same code path serves
        both dialects.
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        return result.scalar_one_or_none()

    async def mark_rotated(
        self, token: RefreshToken, *, replaced_by: uuid.UUID, now: datetime
    ) -> None:
        """Mark ``token`` as consumed by a refresh, pointing at its successor."""
        token.rotated_at = now
        token.replaced_by = replaced_by
        await self.session.flush()

    async def revoke_family(self, family_id: uuid.UUID, *, now: datetime) -> int:
        """Revoke every still-active token in ``family_id``; return the count.

        Already-revoked members are skipped (their ``revoked_at`` is left
        untouched), so a re-sweep of the same family returns ``0``. Iterating the
        loaded rows (rather than a bulk UPDATE) keeps the session's identity map
        consistent — families are tiny (one live token plus its spent
        predecessors), so this is cheap.
        """
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        tokens = list(result.scalars().all())
        for token in tokens:
            token.revoked_at = now
        await self.session.flush()
        return len(tokens)

    async def revoke(self, token: RefreshToken, *, now: datetime) -> None:
        """Revoke a single refresh token (e.g. logout of one session)."""
        token.revoked_at = now
        await self.session.flush()


class ApiTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        token_prefix: str,
        token_hash: str,
        expires_at: datetime | None,
    ) -> ApiToken:
        """Insert a PAT row (storing only ``token_prefix`` + ``token_hash``)."""
        token = ApiToken(
            user_id=user_id,
            name=name,
            token_prefix=token_prefix,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> ApiToken | None:
        """Return the PAT with ``token_hash``, or ``None`` (auth lookup key)."""
        result = await self.session.execute(
            select(ApiToken).where(ApiToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[ApiToken]:
        """Every PAT owned by ``user_id``, newest-first (revoked ones included).

        Listing intentionally does not filter revoked tokens: the token-management
        UI shows them (greyed out) so the user sees their full credential history.
        """
        result = await self.session.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc(), ApiToken.id)
        )
        return list(result.scalars().all())

    async def touch_last_used(self, token: ApiToken, *, now: datetime) -> None:
        """Best-effort update of ``token.last_used_at`` for activity display."""
        token.last_used_at = now
        await self.session.flush()

    async def revoke(self, token: ApiToken, *, now: datetime) -> None:
        """Revoke a PAT (the auth dependency then rejects it)."""
        token.revoked_at = now
        await self.session.flush()

    async def get_owned(self, token_id: uuid.UUID, user_id: uuid.UUID) -> ApiToken | None:
        """Return PAT ``token_id`` only if ``user_id`` owns it, else ``None``.

        The ownership guard for revoke-by-id: a user must never be able to
        address (or revoke) another user's token, so ownership is enforced in the
        query rather than checked after a bare ``get``.
        """
        result = await self.session.execute(
            select(ApiToken).where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
