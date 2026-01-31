"""Match database model."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.song import Song
    from spotdl.db.models.user import User
    from spotdl.db.models.vote import Vote


class MatchType(StrEnum):
    """Type of match (system-generated or user-submitted)."""

    SYSTEM = "system"
    USER = "user"


class Match(Base, TimestampMixin):
    """
    Match between a source song and a target platform URL.

    Can be system-generated (from matching algorithm) or
    user-submitted (crowdsourced).
    """

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "source_url",
            "target_platform",
            "target_url",
            name="uq_matches_source_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )

    # Source song reference
    source_song_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    # Target (audio source)
    target_platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    target_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Match metadata
    match_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MatchType.SYSTEM,
    )
    match_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Voting
    upvotes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    downvotes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # User references
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    source_song: Mapped[Song | None] = relationship(
        "Song",
        back_populates="source_matches",
        foreign_keys=[source_song_id],
    )
    submitted_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="submitted_matches",
        foreign_keys=[submitted_by],
    )
    verified_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="verified_matches",
        foreign_keys=[verified_by],
    )
    votes: Mapped[list[Vote]] = relationship(
        "Vote",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    @property
    def net_votes(self) -> int:
        """Calculate net vote score (upvotes - downvotes)."""
        return self.upvotes - self.downvotes

    def __repr__(self) -> str:
        return (
            f"<Match(id={self.id}, "
            f"source={self.source_platform}:{self.source_url[:30]}, "
            f"target={self.target_platform})>"
        )
