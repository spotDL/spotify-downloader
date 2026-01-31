"""Vote database model."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.match import Match
    from spotdl.db.models.user import User


class VoteType(StrEnum):
    """Type of vote."""

    UP = "up"
    DOWN = "down"


class Vote(Base, TimestampMixin):
    """
    User vote on a match.

    Each user can only vote once per match.
    """

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_votes_match_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vote_type: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
    )

    # Relationships
    match: Mapped[Match] = relationship(
        "Match",
        back_populates="votes",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="votes",
    )

    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, match_id={self.match_id}, type={self.vote_type})>"
