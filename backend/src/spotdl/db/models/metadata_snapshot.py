"""Metadata snapshot model for storing metadata from different sources."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, JSONType, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.song import Song


class MetadataSnapshot(Base, TimestampMixin):
    """
    Stores metadata snapshots from different sources.

    This allows users to view and compare metadata from multiple providers
    (Spotify, MusicBrainz, Discogs, etc.) and switch between them on
    entity pages.
    """

    __tablename__ = "metadata_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )

    # The song this snapshot belongs to
    song_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source identifier (e.g., "spotify", "musicbrainz", "discogs")
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Complete raw API response for future-proofing
    # Stores the exact response from the provider's API
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType(),
        nullable=True,
        doc="Complete raw API response for future-proofing",
    )

    # Normalized/extracted metadata fields for quick access
    # Includes standardized fields from the provider
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType(),
        nullable=False,
        doc="Normalized metadata fields for quick access",
    )

    # When this snapshot was fetched from the source
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Confidence score for this metadata (0.0 to 1.0)
    # Higher scores indicate more reliable/complete metadata
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    # Relationship back to song
    song: Mapped[Song] = relationship(
        "Song",
        back_populates="metadata_snapshots",
    )

    def __repr__(self) -> str:
        return f"<MetadataSnapshot(song_id={self.song_id}, source={self.source})>"
