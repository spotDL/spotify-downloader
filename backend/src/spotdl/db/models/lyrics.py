"""Lyrics database model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid, utc_now

if TYPE_CHECKING:
    from spotdl.db.models.entity_unified import Entity


class Lyrics(Base, TimestampMixin):
    """
    Lyrics for entities from various providers.

    Stores both plain text and synchronized (LRC format) lyrics.
    Multiple sources can exist for the same entity.
    """

    __tablename__ = "lyrics"
    __table_args__ = (
        UniqueConstraint("entity_id", "source", name="uq_lyrics_entity_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lyrics_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    lyrics_synced: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Vote tracking
    upvotes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    downvotes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="suggested",
    )

    # Quality and deduplication tracking
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA256 hash of lyrics content for deduplication",
    )
    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=0.5,
        doc="Quality score 0-1, higher = better (synced lyrics, verified sources)",
    )
    is_verified: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        doc="Whether lyrics have been human-verified",
    )
    line_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of lines for quality assessment",
    )

    # Provider-specific metadata
    provider_track_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Track ID on the lyrics provider (for refetching)",
    )
    has_translations: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        doc="Whether translations are available (MusixMatch)",
    )
    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        doc="Detected language of lyrics",
    )

    # Relationships
    entity: Mapped[Entity] = relationship(
        "Entity",
    )

    def __repr__(self) -> str:
        return f"<Lyrics(id={self.id}, entity_id={self.entity_id}, source={self.source})>"

