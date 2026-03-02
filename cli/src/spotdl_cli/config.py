"""Configuration management for SpotDL CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from platformdirs import user_cache_dir, user_config_dir, user_data_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """SpotDL CLI settings."""

    model_config = SettingsConfigDict(
        env_prefix="SPOTDL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Directories
    config_dir: Path = Field(default_factory=lambda: Path(user_config_dir("spotdl")))
    data_dir: Path = Field(default_factory=lambda: Path(user_data_dir("spotdl")))
    cache_dir: Path = Field(default_factory=lambda: Path(user_cache_dir("spotdl")))
    output_dir: Path = Field(default_factory=lambda: Path.home() / "Music" / "SpotDL")

    # Backend API
    api_url: str = "http://localhost:8000"
    api_timeout: float = 30.0
    backend_mode: Literal["local", "remote"] = "local"
    offline_mode: bool = False
    auth_token: str | None = None

    # Download settings
    audio_format: Literal["mp3", "m4a", "flac", "opus", "ogg", "wav"] = "mp3"
    audio_quality: Literal["best", "320k", "256k", "192k", "128k"] = "best"
    bitrate: str | None = None  # "auto", "disable", "128k", "320k", or VBR "0"-"9"
    threads: int = Field(default=4, ge=1, le=16)
    overwrite: Literal["skip", "force", "metadata"] = "skip"

    # Output template
    output_template: str = "{artist} - {title}"
    max_filename_length: int = 255
    restrict: str | None = None  # "strict" or "loose" filename sanitization

    # Metadata
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover: bool = True
    id3_separator: str = "/"

    # Archive / deduplication
    archive: str | None = None  # Path to archive file
    add_unavailable: bool = False  # Also archive songs that fail to download

    # LRC generation
    generate_lrc: bool = False

    # SponsorBlock
    sponsor_block: bool = False
    sponsor_block_categories: list[str] = Field(default_factory=lambda: [
        "sponsor", "intro", "outro", "selfpromo", "preview", "filler",
        "interaction", "music_offtopic",
    ])

    # M3U playlist generation
    m3u: str | None = None  # M3U output file template (supports {list} variable)

    # Save command
    save_file: str | None = None  # Default save output path

    # Sync command
    sync_without_deleting: bool = False
    sync_remove_lrc: bool = False

    # Skip/overwrite helpers
    create_skip_file: bool = False
    respect_skip_file: bool = False

    # Scan for existing songs
    scan_for_songs: bool = False

    # Skip explicit tracks
    skip_explicit: bool = False

    # Custom FFmpeg / yt-dlp arguments
    ffmpeg_args: str | None = None
    yt_dlp_args: str | None = None

    # Proxy
    proxy: str | None = None

    # Provider selection (legacy CSV lists)
    audio_providers: list[str] = Field(
        default_factory=lambda: ["youtube_music", "youtube"]
    )
    lyrics_providers: list[str] = Field(
        default_factory=lambda: ["synced", "genius", "musixmatch", "azlyrics"]
    )

    # Provider preferences (order + enabled)
    audio_source_preferences: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {"id": "youtube_music", "enabled": True},
            {"id": "youtube", "enabled": True},
            {"id": "soundcloud", "enabled": False},
            {"id": "bandcamp", "enabled": False},
            {"id": "piped", "enabled": False},
        ]
    )
    metadata_source_preferences: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {"id": "spotify", "enabled": True},
            {"id": "musicbrainz", "enabled": True},
            {"id": "discogs", "enabled": True},
        ]
    )
    lyrics_source_preferences: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {"id": "synced", "enabled": True},
            {"id": "genius", "enabled": True},
            {"id": "musixmatch", "enabled": True},
            {"id": "azlyrics", "enabled": False},
        ]
    )

    # Search customization
    search_query: str | None = None  # Custom search query template

    # Playlist options
    playlist_numbering: bool = False
    fetch_albums: bool = False

    # Error logging
    save_errors: str | None = None  # Path to save error log
    print_errors: bool = False

    # Spotify credentials (optional, enables Spotify URL support)
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_user_auth: bool = False  # Use OAuth flow for private playlists

    # SoundCloud OAuth (CLI-only)
    soundcloud_client_id: str | None = None
    soundcloud_auth_token: str | None = None

    # Matching settings (for offline mode)
    name_match_threshold: float = 60.0
    artist_match_threshold: float = 70.0
    time_match_threshold: float = 25.0

    # Advanced
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cookie_file: str | None = None

    # Appearance
    compact_mode: bool = False
    enable_animations: bool = True

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config_file_path(self) -> Path:
        """Get the config file path."""
        return self.config_dir / "config.json"

    @property
    def database_path(self) -> Path:
        """Get the local database path for offline mode."""
        return self.data_dir / "spotdl.db"

    @property
    def cookies_path(self) -> Path:
        """Get the cookies file path."""
        return self.config_dir / "cookies.txt"

    @property
    def cache_path(self) -> Path:
        """Get the cache database path."""
        return self.cache_dir / "cache.db"

    def save(self) -> None:
        """Save settings to config file."""
        self.ensure_directories()

        # Fields to persist (exclude computed/directory fields that shouldn't be saved)
        persist_fields = {
            "api_url",
            "api_timeout",
            "backend_mode",
            "offline_mode",
            "auth_token",
            "audio_format",
            "audio_quality",
            "bitrate",
            "threads",
            "overwrite",
            "output_template",
            "max_filename_length",
            "restrict",
            "embed_metadata",
            "embed_lyrics",
            "embed_cover",
            "id3_separator",
            "archive",
            "add_unavailable",
            "generate_lrc",
            "sponsor_block",
            "sponsor_block_categories",
            "m3u",
            "save_file",
            "sync_without_deleting",
            "sync_remove_lrc",
            "create_skip_file",
            "respect_skip_file",
            "scan_for_songs",
            "skip_explicit",
            "ffmpeg_args",
            "yt_dlp_args",
            "proxy",
            "audio_providers",
            "lyrics_providers",
            "audio_source_preferences",
            "metadata_source_preferences",
            "lyrics_source_preferences",
            "search_query",
            "playlist_numbering",
            "fetch_albums",
            "save_errors",
            "print_errors",
            "spotify_client_id",
            "spotify_client_secret",
            "spotify_user_auth",
            "soundcloud_client_id",
            "soundcloud_auth_token",
            "name_match_threshold",
            "artist_match_threshold",
            "time_match_threshold",
            "output_dir",
            "log_level",
            "cookie_file",
            "compact_mode",
            "enable_animations",
        }

        config_data: dict[str, Any] = {}
        for field_name in persist_fields:
            value = getattr(self, field_name)
            # Convert Path to string for JSON serialization
            if isinstance(value, Path):
                value = str(value)
            config_data[field_name] = value

        try:
            with open(self.config_file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            logger.debug("Settings saved to %s", self.config_file_path)
        except OSError as e:
            logger.error("Failed to save settings: %s", e)
            raise

    @classmethod
    def load_from_file(cls, config_path: Path) -> dict[str, Any]:
        """Load settings from a config file."""
        if not config_path.exists():
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Settings loaded from %s", config_path)
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load settings from %s: %s", config_path, e)
            return {}


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = _load_settings()
    return _settings


def _load_settings() -> Settings:
    """Load settings from config file, falling back to defaults."""
    # First create a default settings to get the config dir path
    default_config_dir = Path(user_config_dir("spotdl"))
    config_file = default_config_dir / "config.json"

    # Load saved config if exists
    saved_config = Settings.load_from_file(config_file)

    # Create settings with saved values (env vars still take priority)
    settings = Settings(**saved_config)
    settings.ensure_directories()

    return settings


def reset_settings() -> Settings:
    """Reset settings to defaults and clear the global instance."""
    global _settings

    # Get config file path before resetting
    if _settings is not None:
        config_file = _settings.config_file_path
        # Remove the config file if it exists
        if config_file.exists():
            try:
                config_file.unlink()
                logger.info("Removed config file: %s", config_file)
            except OSError as e:
                logger.warning("Failed to remove config file: %s", e)

    # Create fresh settings instance
    _settings = Settings()
    _settings.ensure_directories()
    return _settings
