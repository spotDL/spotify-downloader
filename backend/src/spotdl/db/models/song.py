"""Song database model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.match import Match


class Song(Base, TimestampMixin):
    """
    Platform-agnostic song cache.

    Stores song metadata from any source platform to avoid
    repeated API calls.
    """

    __tablename__ = "songs"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_songs_platform_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    platform_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    platform_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    artists: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    album_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    isrc: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # Full metadata JSON for provider-specific fields
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    source_matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="source_song",
        foreign_keys="Match.source_song_id",
    )

    def __repr__(self) -> str:
        return f"<Song(id={self.id}, name={self.name}, platform={self.platform})>"
