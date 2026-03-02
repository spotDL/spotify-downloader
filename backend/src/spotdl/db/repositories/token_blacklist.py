"""Repository for token blacklist operations."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.token_blacklist import BlacklistedToken


class TokenBlacklistRepository:
    """Repository for managing blacklisted tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Create a hash of the token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def add(
        self,
        token: str,
        expires_at: datetime,
        reason: str | None = None,
    ) -> BlacklistedToken:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            expires_at: When the token expires
            reason: Optional reason for blacklisting

        Returns:
            Created BlacklistedToken instance
        """
        token_hash = self._hash_token(token)

        # Check if already blacklisted
        existing = await self.session.get(BlacklistedToken, token_hash)
        if existing:
            return existing

        blacklisted = BlacklistedToken(
            token_hash=token_hash,
            token=token,
            expires_at=expires_at,
            reason=reason,
        )
        self.session.add(blacklisted)
        await self.session.flush()
        return blacklisted

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if blacklisted and not expired, False otherwise
        """
        token_hash = self._hash_token(token)
        now = datetime.now(UTC)

        result = await self.session.execute(
            select(BlacklistedToken).where(
                BlacklistedToken.token_hash == token_hash,
                BlacklistedToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none() is not None

    async def cleanup_expired(self) -> int:
        """
        Remove expired tokens from the blacklist.

        Returns:
            Number of tokens removed
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            delete(BlacklistedToken).where(BlacklistedToken.expires_at <= now)
        )
        await self.session.flush()
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def get_all_active(self) -> list[tuple[str, datetime]]:
        """
        Get all active (non-expired) blacklisted token hashes and expiry times.

        Returns:
            List of tuples (token_hash, expires_at)
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(BlacklistedToken.token_hash, BlacklistedToken.expires_at).where(
                BlacklistedToken.expires_at > now
            )
        )
        return [(row[0], row[1]) for row in result.all()]

    async def count_active(self) -> int:
        """
        Count active (non-expired) blacklisted tokens.

        Returns:
            Number of active blacklisted tokens
        """
        from sqlalchemy import func

        now = datetime.now(UTC)
        result = await self.session.execute(
            select(func.count())
            .select_from(BlacklistedToken)
            .where(BlacklistedToken.expires_at > now)
        )
        return result.scalar() or 0
