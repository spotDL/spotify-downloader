"""User database model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.match import Match
    from spotdl.db.models.vote import Vote


class User(Base, TimestampMixin):
    """
    User model for authentication and contributions.

    Users are required for submitting matches and voting.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    reputation_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    submitted_matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="submitted_by_user",
        foreign_keys="Match.submitted_by",
    )
    verified_matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="verified_by_user",
        foreign_keys="Match.verified_by",
    )
    votes: Mapped[list[Vote]] = relationship(
        "Vote",
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
