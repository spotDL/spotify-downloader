"""User settings database model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotdl.db.models.base import GUID, Base, TimestampMixin, generate_uuid
from spotdl.db.models.song import JSONType

if TYPE_CHECKING:
    from spotdl.db.models.user import User


class UserSettings(Base, TimestampMixin):
    """
    User settings model for storing user-specific configuration.

    Mirrors CLI configuration options to allow consistent behavior
    across CLI and web interface.
    """

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Download settings
    audio_format: Mapped[str] = mapped_column(
        String(10),
        default="mp3",
        nullable=False,
    )
    audio_quality: Mapped[str] = mapped_column(
        String(10),
        default="best",
        nullable=False,
    )
    output_template: Mapped[str] = mapped_column(
        String(255),
        default="{artist} - {title}",
        nullable=False,
    )
    output_directory: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
    )
    max_concurrent_downloads: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    overwrite_existing: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Metadata settings
    embed_metadata: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    embed_lyrics: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    embed_cover_art: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Spotify credentials (encrypted/hashed in production)
    spotify_client_id: Mapped[str | None] = mapped_column(
        String(255),
        default=None,
        nullable=True,
    )
    spotify_client_secret: Mapped[str | None] = mapped_column(
        String(255),
        default=None,
        nullable=True,
    )
    spotify_user_auth: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Server settings
    api_url: Mapped[str] = mapped_column(
        String(500),
        default="http://localhost:8000",
        nullable=False,
    )
    api_timeout: Mapped[float] = mapped_column(
        Float,
        default=30.0,
        nullable=False,
    )
    offline_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Matching thresholds (for offline mode)
    name_match_threshold: Mapped[float] = mapped_column(
        Float,
        default=60.0,
        nullable=False,
    )
    artist_match_threshold: Mapped[float] = mapped_column(
        Float,
        default=70.0,
        nullable=False,
    )
    time_match_threshold: Mapped[float] = mapped_column(
        Float,
        default=25.0,
        nullable=False,
    )

    # Advanced settings
    log_level: Mapped[str] = mapped_column(
        String(10),
        default="INFO",
        nullable=False,
    )
    cookie_file: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
    )

    # Custom settings stored as JSON (for future extensibility)
    custom_settings: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
    )

    # Provider preferences (ordered lists with enabled status)
    # Format: [{"id": "youtube_music", "enabled": true}, ...]
    audio_source_preferences: Mapped[list | None] = mapped_column(
        JSONType(),
        nullable=True,
    )
    metadata_source_preferences: Mapped[list | None] = mapped_column(
        JSONType(),
        nullable=True,
    )
    lyrics_source_preferences: Mapped[list | None] = mapped_column(
        JSONType(),
        nullable=True,
    )

    # Relationship back to user
    user: Mapped[User] = relationship(
        "User",
        back_populates="settings",
    )

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id})>"
