"""Tests for configuration module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from spotdl_cli.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = Settings()

        assert settings.api_url == "http://localhost:8000"
        assert settings.offline_mode is False
        assert settings.audio_format == "mp3"
        assert settings.audio_quality == "best"
        assert settings.threads == 4
        assert settings.overwrite == "skip"
        assert settings.embed_metadata is True
        assert settings.embed_lyrics is True
        assert settings.embed_cover is True

    def test_custom_settings(self) -> None:
        """Test custom settings values."""
        settings = Settings(
            api_url="http://custom:9000",
            offline_mode=True,
            audio_format="flac",
            audio_quality="320k",
            threads=8,
            overwrite="force",
        )

        assert settings.api_url == "http://custom:9000"
        assert settings.offline_mode is True
        assert settings.audio_format == "flac"
        assert settings.audio_quality == "320k"
        assert settings.threads == 8
        assert settings.overwrite == "force"

    def test_settings_from_env(self) -> None:
        """Test settings from environment variables."""
        with patch.dict("os.environ", {
            "SPOTDL_API_URL": "http://env:8080",
            "SPOTDL_OFFLINE_MODE": "true",
            "SPOTDL_AUDIO_FORMAT": "m4a",
        }):
            settings = Settings()

            assert settings.api_url == "http://env:8080"
            assert settings.offline_mode is True
            assert settings.audio_format == "m4a"

    def test_database_path(self, tmp_path: Path) -> None:
        """Test database path property."""
        settings = Settings(data_dir=tmp_path)
        assert settings.database_path == tmp_path / "spotdl.db"

    def test_cookies_path(self, tmp_path: Path) -> None:
        """Test cookies path property."""
        settings = Settings(config_dir=tmp_path)
        assert settings.cookies_path == tmp_path / "cookies.txt"

    def test_cache_path(self, tmp_path: Path) -> None:
        """Test cache path property."""
        settings = Settings(cache_dir=tmp_path)
        assert settings.cache_path == tmp_path / "cache.db"

    def test_ensure_directories(self, tmp_path: Path) -> None:
        """Test directory creation."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"
        output_dir = tmp_path / "output"

        settings = Settings(
            config_dir=config_dir,
            data_dir=data_dir,
            cache_dir=cache_dir,
            output_dir=output_dir,
        )

        settings.ensure_directories()

        assert config_dir.exists()
        assert data_dir.exists()
        assert cache_dir.exists()
        assert output_dir.exists()

    def test_threads_validation(self) -> None:
        """Test threads validation (1-16)."""
        settings = Settings(threads=1)
        assert settings.threads == 1

        settings = Settings(threads=16)
        assert settings.threads == 16

        with pytest.raises(ValueError):
            Settings(threads=0)

        with pytest.raises(ValueError):
            Settings(threads=17)


class TestSettingsPersistence:
    """Tests for settings persistence."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading settings."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)

        # Create settings with custom values
        settings = Settings(
            config_dir=config_dir,
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "output",
            api_url="http://custom:9000",
            offline_mode=True,
            audio_format="flac",
            threads=8,
        )

        # Save settings
        settings.save()

        # Verify config file exists
        config_file = config_dir / "config.json"
        assert config_file.exists()

        # Load settings from file
        loaded_data = Settings.load_from_file(config_file)

        assert loaded_data["api_url"] == "http://custom:9000"
        assert loaded_data["offline_mode"] is True
        assert loaded_data["audio_format"] == "flac"
        assert loaded_data["threads"] == 8

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file returns empty dict."""
        nonexistent = tmp_path / "does_not_exist.json"
        result = Settings.load_from_file(nonexistent)
        assert result == {}

    def test_config_file_path(self, tmp_path: Path) -> None:
        """Test config_file_path property."""
        settings = Settings(config_dir=tmp_path)
        assert settings.config_file_path == tmp_path / "config.json"


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns same instance."""
        # Reset global
        import spotdl_cli.config
        spotdl_cli.config._settings = None

        s1 = get_settings()
        s2 = get_settings()

        assert s1 is s2
