"""User database model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.metadata_report import MetadataReport
    from spotdl.db.models.user_settings import UserSettings


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
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    settings: Mapped[UserSettings | None] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    submitted_reports: Mapped[list[MetadataReport]] = relationship(
        "MetadataReport",
        back_populates="reporter",
        foreign_keys="MetadataReport.reporter_id",
        lazy="selectin",
    )
    reviewed_reports: Mapped[list[MetadataReport]] = relationship(
        "MetadataReport",
        back_populates="reviewer",
        foreign_keys="MetadataReport.reviewed_by",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
