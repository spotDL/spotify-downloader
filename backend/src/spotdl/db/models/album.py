"""Album database models."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid
from spotdl.db.models.song import JSONType

if TYPE_CHECKING:
    from spotdl.db.models.artist import Artist
    from spotdl.db.models.song import Song


class Album(Base, TimestampMixin):
    """
    Internal album entity with cross-platform linking.

    Albums are identified by internal UUIDs and can be linked
    to multiple platform-specific IDs.
    """

    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    name_normalized: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    artist_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("artists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artist_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    cover_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    total_tracks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Extended metadata
    album_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    release_date: Mapped[date | None] = mapped_column(
        Date,
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
    popularity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    genres: Mapped[list[str] | None] = mapped_column(
        JSONType(),
        nullable=True,
    )

    # Relationships
    artist: Mapped[Artist | None] = relationship(
        "Artist",
        back_populates="albums",
    )
    platform_links: Mapped[list[AlbumPlatformLink]] = relationship(
        "AlbumPlatformLink",
        back_populates="album",
        cascade="all, delete-orphan",
    )
    songs: Mapped[list[Song]] = relationship(
        "Song",
        back_populates="album",
        foreign_keys="Song.album_id",
    )

    def __repr__(self) -> str:
        return f"<Album(id={self.id}, name={self.name}, artist={self.artist_name})>"


class AlbumPlatformLink(Base, TimestampMixin):
    """
    Links an internal album to a platform-specific identifier.
    """

    __tablename__ = "album_platform_links"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_album_platform_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    # Relationships
    album: Mapped[Album] = relationship(
        "Album",
        back_populates="platform_links",
    )

    def __repr__(self) -> str:
        return f"<AlbumPlatformLink(album_id={self.album_id}, platform={self.platform}, platform_id={self.platform_id})>"
