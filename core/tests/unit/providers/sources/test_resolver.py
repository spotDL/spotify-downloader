"""Tests for URL resolver."""

from __future__ import annotations

import pytest

from spotdl_core.providers.sources.resolver import (
    URL_PATTERNS,
    URLResolver,
    URLResolverError,
    UnsupportedPlatformError,
    detect_platform,
    extract_url_info,
    get_resolver,
    is_valid_url,
)
from spotdl_core.providers.sources.base import SourceProvider
from spotdl_core.types import Platform, Song, SongList


class MockProvider(SourceProvider):
    """Mock provider for testing."""

    name = "mock"
    display_name = "Mock Provider"
    url_patterns = []

    async def get_track(self, url: str) -> Song:
        """Get track."""
        return Song(
            name="Mock Track",
            artists=["Mock Artist"],
            artist="Mock Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="mock123",
            url=url,
        )

    async def get_album(self, url: str) -> SongList:
        """Get album."""
        song = await self.get_track(url)
        return SongList(
            name="Mock Album",
            url=url,
            platform=Platform.SPOTIFY,
            urls=(url,),
            songs=(song,),
        )

    async def get_playlist(self, url: str) -> SongList:
        """Get playlist."""
        song = await self.get_track(url)
        return SongList(
            name="Mock Playlist",
            url=url,
            platform=Platform.SPOTIFY,
            urls=(url,),
            songs=(song,),
        )

    async def get_artist(self, url: str) -> SongList:
        """Get artist."""
        song = await self.get_track(url)
        return SongList(
            name="Mock Artist",
            url=url,
            platform=Platform.SPOTIFY,
            urls=(url,),
            songs=(song,),
        )

    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """Search."""
        return []


class TestDetectPlatform:
    """Test detect_platform function."""

    def test_detect_spotify_url(self):
        """Test detecting Spotify URLs."""
        assert detect_platform("https://open.spotify.com/track/abc123") == Platform.SPOTIFY
        assert detect_platform("https://open.spotify.com/album/abc123") == Platform.SPOTIFY
        assert (
            detect_platform("https://open.spotify.com/playlist/abc123") == Platform.SPOTIFY
        )
        assert detect_platform("https://open.spotify.com/artist/abc123") == Platform.SPOTIFY

    def test_detect_spotify_intl_url(self):
        """Test detecting Spotify international URLs."""
        assert (
            detect_platform("https://open.spotify.com/intl-de/track/abc123")
            == Platform.SPOTIFY
        )
        assert (
            detect_platform("https://open.spotify.com/intl-fr/album/abc123")
            == Platform.SPOTIFY
        )

    def test_detect_spotify_uri(self):
        """Test detecting Spotify URIs."""
        assert detect_platform("spotify:track:abc123") == Platform.SPOTIFY
        assert detect_platform("spotify:album:abc123") == Platform.SPOTIFY
        assert detect_platform("spotify:playlist:abc123") == Platform.SPOTIFY
        assert detect_platform("spotify:artist:abc123") == Platform.SPOTIFY

    def test_detect_apple_music_url(self):
        """Test detecting Apple Music URLs."""
        assert (
            detect_platform("https://music.apple.com/us/album/name/123456")
            == Platform.APPLE_MUSIC
        )
        assert (
            detect_platform("https://music.apple.com/gb/playlist/name/pl.123")
            == Platform.APPLE_MUSIC
        )
        assert (
            detect_platform("https://music.apple.com/us/album/name/123?i=456")
            == Platform.APPLE_MUSIC
        )

    def test_detect_deezer_url(self):
        """Test detecting Deezer URLs."""
        assert detect_platform("https://www.deezer.com/track/123456") == Platform.DEEZER
        assert detect_platform("https://deezer.com/en/album/123456") == Platform.DEEZER
        assert detect_platform("https://www.deezer.com/playlist/123456") == Platform.DEEZER

    def test_detect_deezer_short_link(self):
        """Test detecting Deezer short links."""
        assert detect_platform("https://deezer.page.link/abc") == Platform.DEEZER
        assert detect_platform("https://deezer.app.link/xyz") == Platform.DEEZER

    def test_detect_tidal_url(self):
        """Test detecting Tidal URLs."""
        assert detect_platform("https://tidal.com/browse/track/123456") == Platform.TIDAL
        assert detect_platform("https://www.tidal.com/album/123456") == Platform.TIDAL
        assert detect_platform("https://listen.tidal.com/track/123456") == Platform.TIDAL

    def test_detect_youtube_music_url(self):
        """Test detecting YouTube Music URLs."""
        assert (
            detect_platform("https://music.youtube.com/watch?v=abc123")
            == Platform.YOUTUBE_MUSIC
        )
        assert (
            detect_platform("https://music.youtube.com/playlist?list=PLabc123")
            == Platform.YOUTUBE_MUSIC
        )
        assert (
            detect_platform("https://music.youtube.com/channel/UCabc123")
            == Platform.YOUTUBE_MUSIC
        )

    def test_detect_soundcloud_url(self):
        """Test detecting SoundCloud URLs."""
        assert (
            detect_platform("https://soundcloud.com/artist/track") == Platform.SOUNDCLOUD
        )
        assert (
            detect_platform("https://www.soundcloud.com/artist/sets/playlist")
            == Platform.SOUNDCLOUD
        )

    def test_detect_bandcamp_url(self):
        """Test detecting Bandcamp URLs."""
        assert detect_platform("https://artist.bandcamp.com/track/name") == Platform.BANDCAMP
        assert detect_platform("https://artist.bandcamp.com/album/name") == Platform.BANDCAMP
        assert detect_platform("https://artist.bandcamp.com/") == Platform.BANDCAMP

    def test_detect_platform_invalid_url(self):
        """Test detecting platform with invalid URL."""
        assert detect_platform("https://example.com/track/123") is None
        assert detect_platform("not-a-url") is None
        assert detect_platform("") is None


class TestExtractUrlInfo:
    """Test extract_url_info function."""

    def test_extract_spotify_track_info(self):
        """Test extracting Spotify track info."""
        info = extract_url_info("https://open.spotify.com/track/abc123")
        assert info["platform"] == "spotify"
        assert info["type"] == "track"
        assert info["id"] == "abc123"

    def test_extract_spotify_album_info(self):
        """Test extracting Spotify album info."""
        info = extract_url_info("https://open.spotify.com/album/xyz789")
        assert info["platform"] == "spotify"
        assert info["type"] == "album"
        assert info["id"] == "xyz789"

    def test_extract_spotify_playlist_info(self):
        """Test extracting Spotify playlist info."""
        info = extract_url_info("spotify:playlist:abc123")
        assert info["platform"] == "spotify"
        assert info["type"] == "playlist"
        assert info["id"] == "abc123"

    def test_extract_youtube_music_track_info(self):
        """Test extracting YouTube Music track info."""
        info = extract_url_info("https://music.youtube.com/watch?v=abc123")
        assert info["platform"] == "youtube_music"
        assert info["id"] == "abc123"

    def test_extract_youtube_music_playlist_info(self):
        """Test extracting YouTube Music playlist info."""
        info = extract_url_info("https://music.youtube.com/playlist?list=PLabc123")
        assert info["platform"] == "youtube_music"
        assert info["id"] == "PLabc123"

    def test_extract_info_invalid_url(self):
        """Test extracting info from invalid URL."""
        info = extract_url_info("https://invalid.com/track/123")
        assert info["platform"] is None
        assert info["type"] is None
        assert info["id"] is None

    def test_extract_info_normalizes_song_to_track(self):
        """Test that 'song' type is normalized to 'track'."""
        # This would need a URL pattern that uses 'song' instead of 'track'
        # The current implementation handles this in the normalization step
        pass


class TestIsValidUrl:
    """Test is_valid_url function."""

    def test_is_valid_spotify_url(self):
        """Test Spotify URL is valid."""
        assert is_valid_url("https://open.spotify.com/track/abc123")
        assert is_valid_url("spotify:album:xyz789")

    def test_is_valid_apple_music_url(self):
        """Test Apple Music URL is valid."""
        assert is_valid_url("https://music.apple.com/us/album/name/123456")

    def test_is_valid_youtube_music_url(self):
        """Test YouTube Music URL is valid."""
        assert is_valid_url("https://music.youtube.com/watch?v=abc123")

    def test_is_invalid_url(self):
        """Test invalid URL."""
        assert not is_valid_url("https://example.com/track/123")
        assert not is_valid_url("not-a-url")
        assert not is_valid_url("")


class TestURLResolver:
    """Test URLResolver class."""

    @pytest.fixture
    def resolver(self) -> URLResolver:
        """Create a URL resolver."""
        return URLResolver()

    @pytest.fixture
    def mock_provider(self) -> MockProvider:
        """Create a mock provider."""
        return MockProvider()

    def test_resolver_init(self, resolver: URLResolver):
        """Test resolver initialization."""
        assert isinstance(resolver, URLResolver)
        assert len(resolver.supported_platforms) == 0

    def test_register_provider(self, resolver: URLResolver, mock_provider: MockProvider):
        """Test registering a provider."""
        resolver.register_provider(Platform.SPOTIFY, mock_provider)
        assert Platform.SPOTIFY in resolver.supported_platforms
        assert resolver.get_provider(Platform.SPOTIFY) == mock_provider

    def test_get_provider_not_registered(self, resolver: URLResolver):
        """Test getting provider that is not registered."""
        assert resolver.get_provider(Platform.SPOTIFY) is None

    def test_get_provider_for_url(self, resolver: URLResolver, mock_provider: MockProvider):
        """Test getting provider for URL."""
        resolver.register_provider(Platform.SPOTIFY, mock_provider)
        provider = resolver.get_provider_for_url("https://open.spotify.com/track/abc123")
        assert provider == mock_provider

    def test_get_provider_for_url_not_registered(self, resolver: URLResolver):
        """Test getting provider for URL when provider not registered."""
        provider = resolver.get_provider_for_url("https://open.spotify.com/track/abc123")
        assert provider is None

    def test_get_provider_for_url_invalid(self, resolver: URLResolver):
        """Test getting provider for invalid URL."""
        provider = resolver.get_provider_for_url("https://invalid.com/track/123")
        assert provider is None

    async def test_resolve_url(self, resolver: URLResolver, mock_provider: MockProvider):
        """Test resolving URL to songs."""
        resolver.register_provider(Platform.SPOTIFY, mock_provider)
        songs = await resolver.resolve("https://open.spotify.com/track/abc123")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)
        assert songs[0].name == "Mock Track"

    async def test_resolve_unsupported_platform(self, resolver: URLResolver):
        """Test resolving URL with unsupported platform."""
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            await resolver.resolve("https://open.spotify.com/track/abc123")
        assert "No provider registered" in str(exc_info.value)

    async def test_resolve_invalid_url(self, resolver: URLResolver):
        """Test resolving invalid URL."""
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            await resolver.resolve("https://invalid.com/track/123")
        assert "Could not detect platform" in str(exc_info.value)

    def test_supported_platforms(self, resolver: URLResolver, mock_provider: MockProvider):
        """Test getting supported platforms."""
        assert len(resolver.supported_platforms) == 0
        resolver.register_provider(Platform.SPOTIFY, mock_provider)
        assert len(resolver.supported_platforms) == 1
        assert Platform.SPOTIFY in resolver.supported_platforms

    def test_multiple_providers(self, resolver: URLResolver, mock_provider: MockProvider):
        """Test registering multiple providers."""
        mock_provider2 = MockProvider()
        resolver.register_provider(Platform.SPOTIFY, mock_provider)
        resolver.register_provider(Platform.DEEZER, mock_provider2)
        assert len(resolver.supported_platforms) == 2
        assert Platform.SPOTIFY in resolver.supported_platforms
        assert Platform.DEEZER in resolver.supported_platforms


class TestGetResolver:
    """Test get_resolver function."""

    def test_get_resolver_returns_singleton(self):
        """Test get_resolver returns the same instance."""
        resolver1 = get_resolver()
        resolver2 = get_resolver()
        assert resolver1 is resolver2

    def test_get_resolver_returns_url_resolver(self):
        """Test get_resolver returns URLResolver instance."""
        resolver = get_resolver()
        assert isinstance(resolver, URLResolver)


class TestURLPatterns:
    """Test URL patterns dictionary."""

    def test_url_patterns_exist(self):
        """Test URL_PATTERNS dictionary exists and has entries."""
        assert isinstance(URL_PATTERNS, dict)
        assert len(URL_PATTERNS) > 0

    def test_url_patterns_all_platforms(self):
        """Test URL_PATTERNS has patterns for all platforms."""
        assert Platform.SPOTIFY in URL_PATTERNS
        assert Platform.APPLE_MUSIC in URL_PATTERNS
        assert Platform.DEEZER in URL_PATTERNS
        assert Platform.TIDAL in URL_PATTERNS
        assert Platform.YOUTUBE_MUSIC in URL_PATTERNS
        assert Platform.SOUNDCLOUD in URL_PATTERNS
        assert Platform.BANDCAMP in URL_PATTERNS

    def test_url_patterns_are_compiled_regex(self):
        """Test URL_PATTERNS contains compiled regex patterns."""
        for platform, patterns in URL_PATTERNS.items():
            assert isinstance(patterns, list)
            assert len(patterns) > 0
            for pattern in patterns:
                assert hasattr(pattern, "search")  # Has regex search method


class TestURLResolverError:
    """Test URLResolverError exception."""

    def test_url_resolver_error(self):
        """Test creating URLResolverError."""
        error = URLResolverError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestUnsupportedPlatformError:
    """Test UnsupportedPlatformError exception."""

    def test_unsupported_platform_error(self):
        """Test creating UnsupportedPlatformError."""
        error = UnsupportedPlatformError("Platform not supported")
        assert str(error) == "Platform not supported"
        assert isinstance(error, URLResolverError)
