"""Tests for provider configuration module."""

import pytest

from spotdl.core.providers_config import (
    AUDIO_SOURCE_PROVIDERS,
    LYRICS_PROVIDERS,
    METADATA_PROVIDERS,
    get_all_providers,
    get_default_preferences,
    validate_preferences,
)


class TestProviderConstants:
    """Tests for provider constants."""

    def test_audio_source_providers_structure(self) -> None:
        """Test audio source providers have correct structure."""
        assert len(AUDIO_SOURCE_PROVIDERS) > 0
        for provider in AUDIO_SOURCE_PROVIDERS:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider
            assert isinstance(provider["id"], str)
            assert isinstance(provider["name"], str)
            assert isinstance(provider["default_enabled"], bool)

    def test_metadata_providers_structure(self) -> None:
        """Test metadata providers have correct structure."""
        assert len(METADATA_PROVIDERS) > 0
        for provider in METADATA_PROVIDERS:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider

    def test_lyrics_providers_structure(self) -> None:
        """Test lyrics providers have correct structure."""
        assert len(LYRICS_PROVIDERS) > 0
        for provider in LYRICS_PROVIDERS:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider


class TestGetDefaultPreferences:
    """Tests for get_default_preferences function."""

    def test_get_audio_defaults(self) -> None:
        """Test getting default audio preferences."""
        prefs = get_default_preferences("audio")
        assert isinstance(prefs, list)
        assert len(prefs) > 0
        for pref in prefs:
            assert "id" in pref
            assert "enabled" in pref
            assert isinstance(pref["enabled"], bool)

    def test_get_metadata_defaults(self) -> None:
        """Test getting default metadata preferences."""
        prefs = get_default_preferences("metadata")
        assert isinstance(prefs, list)
        assert len(prefs) > 0

    def test_get_lyrics_defaults(self) -> None:
        """Test getting default lyrics preferences."""
        prefs = get_default_preferences("lyrics")
        assert isinstance(prefs, list)
        assert len(prefs) > 0

    def test_get_invalid_category_returns_empty(self) -> None:
        """Test getting defaults for invalid category returns empty list."""
        prefs = get_default_preferences("invalid")
        assert prefs == []

    def test_youtube_music_enabled_by_default(self) -> None:
        """Test YouTube Music is enabled by default."""
        prefs = get_default_preferences("audio")
        yt_music = next((p for p in prefs if p["id"] == "youtube_music"), None)
        assert yt_music is not None
        assert yt_music["enabled"] is True

    def test_soundcloud_enabled_by_default(self) -> None:
        """Test SoundCloud is enabled by default."""
        prefs = get_default_preferences("audio")
        soundcloud = next((p for p in prefs if p["id"] == "soundcloud"), None)
        assert soundcloud is not None
        assert soundcloud["enabled"] is True


class TestValidatePreferences:
    """Tests for validate_preferences function."""

    def test_validate_none_returns_defaults(self) -> None:
        """Test validating None returns defaults."""
        result = validate_preferences(None, "audio")
        defaults = get_default_preferences("audio")
        assert len(result) == len(defaults)

    def test_validate_empty_list_returns_defaults(self) -> None:
        """Test validating empty list returns defaults."""
        result = validate_preferences([], "audio")
        defaults = get_default_preferences("audio")
        assert len(result) == len(defaults)

    def test_validate_filters_invalid_ids(self) -> None:
        """Test validation filters out invalid provider IDs."""
        invalid_prefs = [
            {"id": "youtube_music", "enabled": True},
            {"id": "invalid_provider", "enabled": True},
        ]
        result = validate_preferences(invalid_prefs, "audio")
        # Should have youtube_music plus other valid defaults
        assert len(result) >= len(AUDIO_SOURCE_PROVIDERS)
        assert not any(p["id"] == "invalid_provider" for p in result)

    def test_validate_preserves_user_order(self) -> None:
        """Test validation preserves user-specified order."""
        user_prefs = [
            {"id": "youtube", "enabled": True},
            {"id": "youtube_music", "enabled": False},
        ]
        result = validate_preferences(user_prefs, "audio")
        # First two should match user order
        assert result[0]["id"] == "youtube"
        assert result[1]["id"] == "youtube_music"
        assert result[0]["enabled"] is True
        assert result[1]["enabled"] is False

    def test_validate_adds_missing_providers(self) -> None:
        """Test validation adds missing providers with defaults."""
        partial_prefs = [{"id": "youtube_music", "enabled": True}]
        result = validate_preferences(partial_prefs, "audio")
        # Should have all audio providers
        assert len(result) == len(AUDIO_SOURCE_PROVIDERS)
        # All valid provider IDs should be present
        result_ids = {p["id"] for p in result}
        expected_ids = {p["id"] for p in AUDIO_SOURCE_PROVIDERS}
        assert result_ids == expected_ids

    def test_validate_metadata_category(self) -> None:
        """Test validation works for metadata category."""
        result = validate_preferences(None, "metadata")
        assert len(result) == len(METADATA_PROVIDERS)

    def test_validate_lyrics_category(self) -> None:
        """Test validation works for lyrics category."""
        result = validate_preferences(None, "lyrics")
        assert len(result) == len(LYRICS_PROVIDERS)


class TestGetAllProviders:
    """Tests for get_all_providers function."""

    def test_get_all_providers_structure(self) -> None:
        """Test get_all_providers returns correct structure."""
        providers = get_all_providers()
        assert isinstance(providers, dict)
        assert "audio_sources" in providers
        assert "metadata_sources" in providers
        assert "lyrics_sources" in providers

    def test_get_all_providers_contains_correct_data(self) -> None:
        """Test get_all_providers contains correct provider data."""
        providers = get_all_providers()
        assert providers["audio_sources"] == AUDIO_SOURCE_PROVIDERS
        assert providers["metadata_sources"] == METADATA_PROVIDERS
        assert providers["lyrics_sources"] == LYRICS_PROVIDERS
