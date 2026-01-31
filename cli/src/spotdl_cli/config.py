"""Configuration management for SpotDL CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from platformdirs import user_cache_dir, user_config_dir, user_data_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    offline_mode: bool = False

    # Download settings
    audio_format: Literal["mp3", "m4a", "flac", "opus", "ogg", "wav"] = "mp3"
    audio_quality: Literal["best", "320k", "256k", "192k", "128k"] = "best"
    threads: int = Field(default=4, ge=1, le=16)
    overwrite: bool = False

    # Output template
    output_template: str = "{artist} - {title}"

    # Metadata
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover: bool = True

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

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

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


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
