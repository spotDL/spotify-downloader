"""Tests for configuration."""

import pytest
import os

from spotdl.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.app_name == "SpotDL API"
        assert settings.app_version == "5.0.0"
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.port == 8000

    def test_is_production(self):
        """Test is_production property."""
        settings = Settings(environment="production")
        assert settings.is_production is True
        assert settings.is_development is False

        settings = Settings(environment="development")
        assert settings.is_production is False
        assert settings.is_development is True

    def test_database_type_detection(self):
        """Test database type detection."""
        settings = Settings(database_url="sqlite:///./test.db")
        assert settings.database_is_sqlite is True
        assert settings.database_is_postgres is False

        settings = Settings(database_url="postgresql://user:pass@localhost/db")
        assert settings.database_is_sqlite is False
        assert settings.database_is_postgres is True

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance (cached)
        assert settings1 is settings2

    def test_cors_origins_default(self):
        """Test default CORS origins."""
        settings = Settings()

        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:5173" in settings.cors_origins
