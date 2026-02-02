"""Application configuration using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SpotDL API"
    app_version: str = "5.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    deployment_mode: Literal["hosted", "self-hosted"] = Field(
        default="self-hosted",
        description="Deployment mode: 'hosted' for public matching service (no downloads), 'self-hosted' for full functionality",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = Field(
        default=None,
        description="Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If not set, uses DEBUG when debug=True, INFO in development, WARNING otherwise.",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/spotdl.db",
        description="Database connection URL (SQLite or PostgreSQL)",
    )
    database_echo: bool = False

    # Redis (optional, for caching)
    redis_url: RedisDsn | None = None
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # Authentication
    secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production-please"),
        description="Secret key for JWT signing",
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS (use comma-separated strings for env var compatibility)
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="cors_origins",
        description="Allowed CORS origins (comma-separated)",
    )
    cors_allow_credentials: bool = True
    cors_allow_methods_str: str = Field(
        default="*",
        alias="cors_allow_methods",
        description="Allowed CORS methods (comma-separated or *)",
    )
    cors_allow_headers_str: str = Field(
        default="*",
        alias="cors_allow_headers",
        description="Allowed CORS headers (comma-separated or *)",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [s.strip() for s in self.cors_origins_str.split(",") if s.strip()]

    @property
    def cors_allow_methods(self) -> list[str]:
        """Parse CORS methods from comma-separated string."""
        return [s.strip() for s in self.cors_allow_methods_str.split(",") if s.strip()]

    @property
    def cors_allow_headers(self) -> list[str]:
        """Parse CORS headers from comma-separated string."""
        return [s.strip() for s in self.cors_allow_headers_str.split(",") if s.strip()]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Matching
    match_score_threshold: float = 80.0
    isrc_match_threshold: float = 80.0

    # External services (optional)
    spotify_client_id: str | None = None
    spotify_client_secret: SecretStr | None = None

    # Lyrics providers
    genius_access_token: SecretStr | None = Field(
        default=None,
        description="Genius API access token for lyrics fetching",
    )
    lyrics_cache_enabled: bool = Field(
        default=True,
        description="Whether to cache lyrics in the database",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_hosted(self) -> bool:
        """Check if running in hosted mode (public matching service, no downloads)."""
        return self.deployment_mode == "hosted"

    @property
    def is_self_hosted(self) -> bool:
        """Check if running in self-hosted mode (full functionality including downloads)."""
        return self.deployment_mode == "self-hosted"

    @property
    def downloads_enabled(self) -> bool:
        """Check if download functionality is enabled."""
        return self.is_self_hosted

    @property
    def database_is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")

    @property
    def database_is_postgres(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
