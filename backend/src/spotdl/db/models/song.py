"""Song database model."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, JSONType, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.album import Album
    from spotdl.db.models.artist import Artist
    from spotdl.db.models.lyrics import Lyrics
    from spotdl.db.models.match import Match
    from spotdl.db.models.metadata_snapshot import MetadataSnapshot


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
        GUID(),
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
        JSONType(),
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
        JSONType(),
        nullable=True,
    )

    # Foreign keys to internal entity tables
    artist_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("artists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    album_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("albums.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Spotify audio features
    bpm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    energy: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    danceability: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    valence: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    key: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    mode: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    loudness: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    speechiness: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    acousticness: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    instrumentalness: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    liveness: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    time_signature: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Additional metadata
    popularity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    label: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    copyright_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    release_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    explicit: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    genres: Mapped[list[str] | None] = mapped_column(
        JSONType(),
        nullable=True,
    )

    # Metadata enrichment tracking
    field_sources: Mapped[dict[str, str] | None] = mapped_column(
        JSONType(),
        nullable=True,
        doc="Tracks which metadata source provided which field, e.g. {'genres': 'musicbrainz', 'label': 'discogs'}",
    )
    musicbrainz_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="MusicBrainz recording ID for re-fetching metadata",
    )
    discogs_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Discogs release ID for re-fetching metadata",
    )
    enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time metadata was enriched from external sources",
    )

    # Relationships
    artist: Mapped[Artist | None] = relationship(
        "Artist",
        back_populates="songs",
        foreign_keys=[artist_id],
    )
    album: Mapped[Album | None] = relationship(
        "Album",
        back_populates="songs",
        foreign_keys=[album_id],
    )
    source_matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="source_song",
        foreign_keys="Match.source_song_id",
    )
    lyrics: Mapped[list[Lyrics]] = relationship(
        "Lyrics",
        back_populates="song",
        cascade="all, delete-orphan",
    )
    metadata_snapshots: Mapped[list[MetadataSnapshot]] = relationship(
        "MetadataSnapshot",
        back_populates="song",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Song(id={self.id}, name={self.name}, platform={self.platform})>"
