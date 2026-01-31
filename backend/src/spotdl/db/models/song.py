"""Song database model."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Integer, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import Base, GUID, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from spotdl.db.models.match import Match


class JSONType(TypeDecorator[Any]):
    """
    Platform-independent JSON type.

    Uses PostgreSQL's JSONB when available, otherwise uses
    Text with JSON serialization for SQLite.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


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

    # Relationships
    source_matches: Mapped[list[Match]] = relationship(
        "Match",
        back_populates="source_song",
        foreign_keys="Match.source_song_id",
    )

    def __repr__(self) -> str:
        return f"<Song(id={self.id}, name={self.name}, platform={self.platform})>"
