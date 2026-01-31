"""Tests for URL resolver and platform detection."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.resolver import (
    URLResolver,
    UnsupportedPlatformError,
    detect_platform,
    extract_url_info,
    is_valid_url,
)


class TestDetectPlatform:
    """Tests for platform detection from URLs."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            # Spotify URLs
            ("https://open.spotify.com/track/abc123", Platform.SPOTIFY),
            ("https://open.spotify.com/album/xyz789", Platform.SPOTIFY),
            ("https://open.spotify.com/playlist/list123", Platform.SPOTIFY),
            ("https://open.spotify.com/artist/art456", Platform.SPOTIFY),
            ("https://open.spotify.com/intl-us/track/abc123", Platform.SPOTIFY),
            ("spotify:track:abc123", Platform.SPOTIFY),
            # YouTube Music URLs
            ("https://music.youtube.com/watch?v=abc123", Platform.YOUTUBE_MUSIC),
            ("https://music.youtube.com/playlist?list=PLxyz", Platform.YOUTUBE_MUSIC),
            ("https://music.youtube.com/channel/UCxyz", Platform.YOUTUBE_MUSIC),
            # Deezer URLs
            ("https://www.deezer.com/track/123456", Platform.DEEZER),
            ("https://deezer.com/album/789012", Platform.DEEZER),
            ("https://www.deezer.com/en/playlist/345678", Platform.DEEZER),
            # Apple Music URLs
            ("https://music.apple.com/us/album/test-album/123456", Platform.APPLE_MUSIC),
            ("https://music.apple.com/gb/playlist/test/pl.123", Platform.APPLE_MUSIC),
            # Tidal URLs
            ("https://tidal.com/track/12345678", Platform.TIDAL),
            ("https://www.tidal.com/album/87654321", Platform.TIDAL),
            ("https://listen.tidal.com/track/11111111", Platform.TIDAL),
            ("https://tidal.com/browse/track/12345678", Platform.TIDAL),
            # SoundCloud URLs
            ("https://soundcloud.com/artist/track-name", Platform.SOUNDCLOUD),
            ("https://www.soundcloud.com/artist/sets/playlist-name", Platform.SOUNDCLOUD),
            # Bandcamp URLs
            ("https://artist.bandcamp.com/track/song-name", Platform.BANDCAMP),
            ("https://artist.bandcamp.com/album/album-name", Platform.BANDCAMP),
            ("https://artist.bandcamp.com", Platform.BANDCAMP),
        ],
    )
    def test_detect_platform(self, url: str, expected: Platform) -> None:
        """Test platform detection from various URLs."""
        assert detect_platform(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/track/123",
            "https://google.com",
            "not a url",
            "",
            "https://spotify.com/track/123",  # Wrong domain
        ],
    )
    def test_detect_platform_unsupported(self, url: str) -> None:
        """Test that unsupported URLs return None."""
        assert detect_platform(url) is None


class TestExtractUrlInfo:
    """Tests for extracting URL information."""

    def test_extract_spotify_track(self) -> None:
        """Test extracting info from Spotify track URL."""
        info = extract_url_info("https://open.spotify.com/track/abc123def")
        assert info["platform"] == "spotify"
        assert info["type"] == "track"
        assert info["id"] == "abc123def"

    def test_extract_spotify_album(self) -> None:
        """Test extracting info from Spotify album URL."""
        info = extract_url_info("https://open.spotify.com/album/xyz789ghi")
        assert info["platform"] == "spotify"
        assert info["type"] == "album"
        assert info["id"] == "xyz789ghi"

    def test_extract_deezer_track(self) -> None:
        """Test extracting info from Deezer track URL."""
        info = extract_url_info("https://www.deezer.com/track/123456789")
        assert info["platform"] == "deezer"
        assert info["type"] == "track"
        assert info["id"] == "123456789"

    def test_extract_youtube_music(self) -> None:
        """Test extracting info from YouTube Music URL."""
        info = extract_url_info("https://music.youtube.com/watch?v=abc123xyz")
        assert info["platform"] == "youtube_music"
        assert info["id"] == "abc123xyz"

    def test_extract_unsupported(self) -> None:
        """Test extracting info from unsupported URL."""
        info = extract_url_info("https://example.com/track/123")
        assert info["platform"] is None
        assert info["type"] is None
        assert info["id"] is None


class TestIsValidUrl:
    """Tests for URL validation."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://open.spotify.com/track/abc123", True),
            ("https://music.youtube.com/watch?v=xyz", True),
            ("https://www.deezer.com/track/123456", True),
            ("https://example.com/track/123", False),
            ("not a url", False),
            ("", False),
        ],
    )
    def test_is_valid_url(self, url: str, expected: bool) -> None:
        """Test URL validation."""
        assert is_valid_url(url) == expected


class TestURLResolver:
    """Tests for URLResolver class."""

    def test_register_provider(self) -> None:
        """Test registering a provider."""
        from unittest.mock import MagicMock

        resolver = URLResolver()
        mock_provider = MagicMock()

        resolver.register_provider(Platform.SPOTIFY, mock_provider)

        assert resolver.get_provider(Platform.SPOTIFY) == mock_provider

    def test_get_provider_not_registered(self) -> None:
        """Test getting unregistered provider returns None."""
        resolver = URLResolver()
        assert resolver.get_provider(Platform.SPOTIFY) is None

    def test_get_provider_for_url(self) -> None:
        """Test getting provider for a URL."""
        from unittest.mock import MagicMock

        resolver = URLResolver()
        mock_provider = MagicMock()
        resolver.register_provider(Platform.SPOTIFY, mock_provider)

        provider = resolver.get_provider_for_url("https://open.spotify.com/track/abc")
        assert provider == mock_provider

    def test_get_provider_for_url_not_found(self) -> None:
        """Test getting provider for unsupported URL."""
        resolver = URLResolver()
        provider = resolver.get_provider_for_url("https://example.com/track/123")
        assert provider is None

    def test_supported_platforms(self) -> None:
        """Test listing supported platforms."""
        from unittest.mock import MagicMock

        resolver = URLResolver()
        resolver.register_provider(Platform.SPOTIFY, MagicMock())
        resolver.register_provider(Platform.DEEZER, MagicMock())

        platforms = resolver.supported_platforms
        assert Platform.SPOTIFY in platforms
        assert Platform.DEEZER in platforms
        assert len(platforms) == 2

    @pytest.mark.asyncio
    async def test_resolve_unsupported_platform(self) -> None:
        """Test resolving unsupported URL raises error."""
        resolver = URLResolver()

        with pytest.raises(UnsupportedPlatformError):
            await resolver.resolve("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_resolve_no_provider(self) -> None:
        """Test resolving URL without registered provider raises error."""
        resolver = URLResolver()

        with pytest.raises(UnsupportedPlatformError):
            await resolver.resolve("https://open.spotify.com/track/abc123")
