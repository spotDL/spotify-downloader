"""Tests for provider preferences module."""

from spotdl.core.provider_preferences import (
    AUDIO_PLATFORM_MAP,
    DEFAULT_PLATFORM_ORDER,
    get_audio_platform_order_from_preferences,
    get_enabled_audio_platforms,
    get_enabled_lyrics_provider_ids,
    get_enabled_metadata_provider_ids,
)
from spotdl.core.providers_config import AUDIO_SOURCE_PROVIDERS
from spotdl.core.services.match import MatchService
from spotdl.core.types.result import TargetPlatform


class TestAudioPlatformConstants:
    """Tests for audio platform constants."""

    def test_audio_platform_map_structure(self) -> None:
        """Test AUDIO_PLATFORM_MAP has correct structure."""
        assert isinstance(AUDIO_PLATFORM_MAP, dict)
        assert len(AUDIO_PLATFORM_MAP) > 0

        for key, value in AUDIO_PLATFORM_MAP.items():
            assert isinstance(key, str)
            assert isinstance(value, TargetPlatform)

    def test_default_platform_order(self) -> None:
        """Test DEFAULT_PLATFORM_ORDER contains expected platforms."""
        assert isinstance(DEFAULT_PLATFORM_ORDER, list)
        assert TargetPlatform.YOUTUBE_MUSIC in DEFAULT_PLATFORM_ORDER
        assert TargetPlatform.YOUTUBE in DEFAULT_PLATFORM_ORDER
        assert TargetPlatform.SOUNDCLOUD in DEFAULT_PLATFORM_ORDER

    def test_platform_map_keys_match_provider_ids(self) -> None:
        """Test AUDIO_PLATFORM_MAP keys match audio provider IDs."""
        expected_keys = {"youtube_music", "youtube", "soundcloud", "bandcamp", "piped"}
        assert set(AUDIO_PLATFORM_MAP.keys()) == expected_keys

    def test_audio_provider_ids_align_with_config(self) -> None:
        """Test audio platform map stays in sync with provider config."""
        config_ids = {provider["id"] for provider in AUDIO_SOURCE_PROVIDERS}
        assert set(AUDIO_PLATFORM_MAP.keys()) == config_ids

    def test_match_service_supports_all_mapped_platforms(self) -> None:
        """Test MatchService wiring matches mapped audio target platforms."""
        audio_prefs = [
            {"id": provider["id"], "enabled": True} for provider in AUDIO_SOURCE_PROVIDERS
        ]
        service = MatchService(audio_preferences=audio_prefs)
        assert set(service.supported_platforms) == set(AUDIO_PLATFORM_MAP.values())


class TestGetEnabledAudioPlatforms:
    """Tests for get_enabled_audio_platforms function."""

    def test_none_preferences_returns_defaults(self) -> None:
        """Test None preferences returns default enabled platforms."""
        platforms = get_enabled_audio_platforms(None)
        assert isinstance(platforms, list)
        assert len(platforms) > 0
        # Should include YouTube and YouTube Music (enabled by default)
        assert TargetPlatform.YOUTUBE_MUSIC in platforms
        assert TargetPlatform.YOUTUBE in platforms

    def test_empty_preferences_returns_defaults(self) -> None:
        """Test empty preferences returns defaults."""
        platforms = get_enabled_audio_platforms([])
        assert len(platforms) > 0

    def test_custom_preferences_respected(self) -> None:
        """Test custom preferences are respected."""
        prefs = [
            {"id": "youtube", "enabled": True},
            {"id": "soundcloud", "enabled": True},
            {"id": "youtube_music", "enabled": False},
        ]
        platforms = get_enabled_audio_platforms(prefs)

        assert TargetPlatform.YOUTUBE in platforms
        assert TargetPlatform.SOUNDCLOUD in platforms
        assert TargetPlatform.YOUTUBE_MUSIC not in platforms

    def test_preference_order_preserved(self) -> None:
        """Test user preference order is preserved."""
        prefs = [
            {"id": "soundcloud", "enabled": True},
            {"id": "youtube", "enabled": True},
            {"id": "youtube_music", "enabled": True},
        ]
        platforms = get_enabled_audio_platforms(prefs)

        # Order should match preference order
        assert platforms[0] == TargetPlatform.SOUNDCLOUD
        assert platforms[1] == TargetPlatform.YOUTUBE
        assert platforms[2] == TargetPlatform.YOUTUBE_MUSIC

    def test_invalid_platform_id_filtered(self) -> None:
        """Test invalid platform IDs are filtered out."""
        prefs = [
            {"id": "youtube_music", "enabled": True},
            {"id": "invalid_platform", "enabled": True},
        ]
        platforms = get_enabled_audio_platforms(prefs)

        assert TargetPlatform.YOUTUBE_MUSIC in platforms
        assert len([p for p in platforms if hasattr(p, "value")]) == len(platforms)

    def test_all_disabled_returns_defaults(self) -> None:
        """Test all disabled preferences returns defaults."""
        prefs = [
            {"id": "youtube_music", "enabled": False},
            {"id": "youtube", "enabled": False},
            {"id": "soundcloud", "enabled": False},
        ]
        platforms = get_enabled_audio_platforms(prefs)
        # Should fall back to defaults when nothing enabled
        assert len(platforms) > 0


class TestGetEnabledMetadataProviderIds:
    """Tests for get_enabled_metadata_provider_ids function."""

    def test_none_preferences_returns_defaults(self) -> None:
        """Test None preferences returns default metadata providers."""
        result = get_enabled_metadata_provider_ids(None)

        assert "provider_ids" in result
        assert "enable_musicbrainz" in result
        assert "enable_discogs" in result
        assert isinstance(result["provider_ids"], list)
        assert len(result["provider_ids"]) > 0

    def test_custom_preferences_respected(self) -> None:
        """Test custom metadata preferences are respected."""
        prefs = [
            {"id": "spotify", "enabled": True},
            {"id": "musicbrainz", "enabled": True},
            {"id": "discogs", "enabled": False},
        ]
        result = get_enabled_metadata_provider_ids(prefs)

        assert "spotify" in result["provider_ids"]
        assert "musicbrainz" in result["provider_ids"]
        assert "discogs" not in result["provider_ids"]
        assert result["enable_musicbrainz"] is True
        assert result["enable_discogs"] is False

    def test_all_disabled_returns_defaults(self) -> None:
        """Test all disabled returns defaults."""
        prefs = [
            {"id": "spotify", "enabled": False},
            {"id": "musicbrainz", "enabled": False},
            {"id": "discogs", "enabled": False},
        ]
        result = get_enabled_metadata_provider_ids(prefs)
        # Should fall back to defaults
        assert len(result["provider_ids"]) > 0


class TestGetEnabledLyricsProviderIds:
    """Tests for get_enabled_lyrics_provider_ids function."""

    def test_none_preferences_returns_defaults(self) -> None:
        """Test None preferences returns default lyrics providers."""
        result = get_enabled_lyrics_provider_ids(None)

        assert "provider_ids" in result
        assert "provider_order" in result
        assert isinstance(result["provider_ids"], list)
        assert len(result["provider_ids"]) > 0

    def test_custom_preferences_respected(self) -> None:
        """Test custom lyrics preferences are respected."""
        prefs = [
            {"id": "synced", "enabled": True},
            {"id": "genius", "enabled": True},
            {"id": "musixmatch", "enabled": False},
        ]
        result = get_enabled_lyrics_provider_ids(prefs)

        assert "synced" in result["provider_ids"]
        assert "genius" in result["provider_ids"]
        assert "musixmatch" not in result["provider_ids"]

    def test_preference_order_matches(self) -> None:
        """Test provider order matches provider IDs."""
        prefs = [
            {"id": "genius", "enabled": True},
            {"id": "synced", "enabled": True},
        ]
        result = get_enabled_lyrics_provider_ids(prefs)

        assert result["provider_order"] == result["provider_ids"]
        assert result["provider_order"][0] == "genius"
        assert result["provider_order"][1] == "synced"


class TestGetAudioPlatformOrderFromPreferences:
    """Tests for get_audio_platform_order_from_preferences function."""

    def test_returns_string_ids(self) -> None:
        """Test function returns string IDs not enums."""
        prefs = [
            {"id": "youtube_music", "enabled": True},
            {"id": "youtube", "enabled": True},
        ]
        result = get_audio_platform_order_from_preferences(prefs)

        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)
        assert "youtube_music" in result
        assert "youtube" in result

    def test_none_preferences_returns_defaults(self) -> None:
        """Test None preferences returns default platform order."""
        result = get_audio_platform_order_from_preferences(None)
        assert len(result) > 0
        assert isinstance(result[0], str)

    def test_order_preserved_as_strings(self) -> None:
        """Test order is preserved when converting to strings."""
        prefs = [
            {"id": "soundcloud", "enabled": True},
            {"id": "youtube", "enabled": True},
        ]
        result = get_audio_platform_order_from_preferences(prefs)

        assert result[0] == "soundcloud"
        assert result[1] == "youtube"
