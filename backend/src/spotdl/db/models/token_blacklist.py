"""Token blacklist model for tracking revoked tokens."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from spotdl.db.models.base import Base, utc_now


class BlacklistedToken(Base):
    """
    Model for storing blacklisted JWT tokens.

    Tokens are added here when a user logs out or when tokens need to be
    revoked. Expired tokens can be periodically cleaned up.
    """

    __tablename__ = "blacklisted_tokens"

    # Use token hash as primary key (tokens can be long)
    token_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hash length
        primary_key=True,
    )

    # Store full token for validation (optional, can be removed if only hash is needed)
    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # When the token expires (for cleanup purposes)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # When the token was blacklisted
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Optional: reason for blacklisting (logout, password change, etc.)
    reason: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Index for efficient expiry cleanup
    __table_args__ = (
        Index("ix_blacklisted_tokens_expires_at", expires_at),
    )
