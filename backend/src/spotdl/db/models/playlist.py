"""Playlist database models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.song import Song


class Playlist(Base, TimestampMixin):
    """
    Internal playlist entity with cross-platform linking.

    Playlists are identified by internal UUIDs and can be linked
    to multiple platform-specific IDs.
    """

    __tablename__ = "playlists"

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
    owner_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    cover_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    total_tracks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    platform_links: Mapped[list[PlaylistPlatformLink]] = relationship(
        "PlaylistPlatformLink",
        back_populates="playlist",
        cascade="all, delete-orphan",
    )
    tracks: Mapped[list[PlaylistTrack]] = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )

    def __repr__(self) -> str:
        return f"<Playlist(id={self.id}, name={self.name})>"


class PlaylistPlatformLink(Base, TimestampMixin):
    """
    Links an internal playlist to a platform-specific identifier.
    """

    __tablename__ = "playlist_platform_links"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_playlist_platform_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    playlist_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("playlists.id", ondelete="CASCADE"),
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
    playlist: Mapped[Playlist] = relationship(
        "Playlist",
        back_populates="platform_links",
    )

    def __repr__(self) -> str:
        return f"<PlaylistPlatformLink(playlist_id={self.playlist_id}, platform={self.platform})>"


class PlaylistTrack(Base):
    """
    Junction table linking playlists to songs with position ordering.
    """

    __tablename__ = "playlist_tracks"
    __table_args__ = (
        UniqueConstraint("playlist_id", "position", name="uq_playlist_track_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    playlist_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Relationships
    playlist: Mapped[Playlist] = relationship(
        "Playlist",
        back_populates="tracks",
    )
    song: Mapped[Song] = relationship(
        "Song",
    )

    def __repr__(self) -> str:
        return f"<PlaylistTrack(playlist_id={self.playlist_id}, song_id={self.song_id}, position={self.position})>"
