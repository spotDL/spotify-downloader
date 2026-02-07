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
    bitrate: Mapped[str | None] = mapped_column(
        String(20),
        default=None,
        nullable=True,
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
    overwrite: Mapped[str] = mapped_column(
        String(10),
        default="skip",
        nullable=False,
    )
    max_filename_length: Mapped[int] = mapped_column(
        Integer,
        default=255,
        nullable=False,
    )
    restrict: Mapped[str | None] = mapped_column(
        String(10),
        default=None,
        nullable=True,
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
    embed_cover: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    id3_separator: Mapped[str] = mapped_column(
        String(5),
        default="/",
        nullable=False,
    )

    # SponsorBlock
    sponsor_block: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # LRC / Lyrics files
    generate_lrc: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # M3U playlist generation
    m3u: Mapped[str | None] = mapped_column(
        String(255),
        default=None,
        nullable=True,
    )

    # Archive (deduplication)
    archive: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
    )

    # Content filtering
    skip_explicit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    scan_for_songs: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Playlist options
    playlist_numbering: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    fetch_albums: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Proxy
    proxy: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
    )

    # Custom arguments
    ffmpeg_args: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
    )
    yt_dlp_args: Mapped[str | None] = mapped_column(
        String(500),
        default=None,
        nullable=True,
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

    # Appearance settings
    compact_sidebar: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    enable_animations: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    reduce_motion: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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

    # Metadata embed preferences (per-field source priority)
    # Format: {
    #   "default_order": ["spotify", "musicbrainz", "discogs"],
    #   "fields": {
    #     "genres": {"order": ["musicbrainz", "discogs"], "enabled": true},
    #     "label": {"order": ["discogs", "musicbrainz"], "enabled": true},
    #     ...
    #   }
    # }
    metadata_embed_preferences: Mapped[dict | None] = mapped_column(
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
