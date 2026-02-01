"""Lyrics database model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid, utc_now

if TYPE_CHECKING:
    from spotdl.db.models.song import Song


class Lyrics(Base, TimestampMixin):
    """
    Lyrics for songs from various providers.

    Stores both plain text and synchronized (LRC format) lyrics.
    Multiple sources can exist for the same song.
    """

    __tablename__ = "lyrics"
    __table_args__ = (
        UniqueConstraint("song_id", "source", name="uq_lyrics_song_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("songs.id", ondelete="CASCADE"),
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

    # Relationships
    song: Mapped[Song] = relationship(
        "Song",
        back_populates="lyrics",
    )

    def __repr__(self) -> str:
        return f"<Lyrics(id={self.id}, song_id={self.song_id}, source={self.source})>"
