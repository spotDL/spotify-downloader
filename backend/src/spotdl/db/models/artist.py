"""Artist database models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid
from spotdl.db.models.song import JSONType

if TYPE_CHECKING:
    from spotdl.db.models.album import Album
    from spotdl.db.models.song import Song


class Artist(Base, TimestampMixin):
    """
    Internal artist entity with cross-platform linking.

    Artists are identified by internal UUIDs and can be linked
    to multiple platform-specific IDs (Spotify, Deezer, YouTube Music, etc.).
    """

    __tablename__ = "artists"

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
    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    genres: Mapped[list[str]] = mapped_column(
        JSONType(),
        nullable=False,
        default=list,
    )

    # Relationships
    platform_links: Mapped[list[ArtistPlatformLink]] = relationship(
        "ArtistPlatformLink",
        back_populates="artist",
        cascade="all, delete-orphan",
    )
    albums: Mapped[list[Album]] = relationship(
        "Album",
        back_populates="artist",
    )
    songs: Mapped[list[Song]] = relationship(
        "Song",
        back_populates="artist",
        foreign_keys="Song.artist_id",
    )

    def __repr__(self) -> str:
        return f"<Artist(id={self.id}, name={self.name})>"


class ArtistPlatformLink(Base, TimestampMixin):
    """
    Links an internal artist to a platform-specific identifier.

    Each platform (Spotify, Deezer, YouTube Music, etc.) has its own
    ID system. This table maps those to our internal artist UUID.
    """

    __tablename__ = "artist_platform_links"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_artist_platform_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("artists.id", ondelete="CASCADE"),
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
    followers: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    artist: Mapped[Artist] = relationship(
        "Artist",
        back_populates="platform_links",
    )

    def __repr__(self) -> str:
        return f"<ArtistPlatformLink(artist_id={self.artist_id}, platform={self.platform}, platform_id={self.platform_id})>"
