"""Metadata report database model for crowdsourced corrections."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.user import User


class ReportStatus(StrEnum):
    """Status of a metadata report."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    FIXED = "fixed"
    DISMISSED = "dismissed"


class MetadataReportEntityType(StrEnum):
    """Type of entity being reported."""

    SONG = "song"
    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"


class MetadataReport(Base, TimestampMixin):
    """
    User-submitted metadata correction reports.

    Supports reporting corrections for any entity type (song, artist, album, playlist).
    Tracks review workflow from submission through resolution.
    """

    __tablename__ = "metadata_reports"
    __table_args__ = (Index("ix_metadata_reports_entity", "entity_type", "entity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    current_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    suggested_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReportStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    reporter: Mapped[User] = relationship(
        "User",
        back_populates="submitted_reports",
        foreign_keys=[reporter_id],
        lazy="selectin",
    )
    reviewer: Mapped[User | None] = relationship(
        "User",
        back_populates="reviewed_reports",
        foreign_keys=[reviewed_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<MetadataReport(id={self.id}, "
            f"entity={self.entity_type}:{self.entity_id}, "
            f"field={self.field_name}, status={self.status})>"
        )
