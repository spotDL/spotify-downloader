"""Tests for SongService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.services.song import (
    SongService,
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.types.song import Platform, Song, SongList
from spotdl.providers.sources.base import SourceProviderError


@pytest.fixture
def song_service() -> SongService:
    """Create a song service instance for testing."""
    return SongService()


@pytest.fixture
def mock_song() -> Song:
    """Create a mock song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
    )


class TestSongServiceInit:
    """Tests for SongService initialization."""

    def test_init_creates_providers(self) -> None:
        """Test that init creates all providers."""
        service = SongService()

        assert service.get_provider(Platform.SPOTIFY) is not None
        assert service.get_provider(Platform.YOUTUBE_MUSIC) is not None
        assert service.get_provider(Platform.DEEZER) is not None
        assert service.get_provider(Platform.APPLE_MUSIC) is not None
        assert service.get_provider(Platform.TIDAL) is not None
        assert service.get_provider(Platform.SOUNDCLOUD) is not None
        assert service.get_provider(Platform.BANDCAMP) is not None

    def test_supported_platforms(self) -> None:
        """Test supported_platforms property."""
        service = SongService()
        platforms = service.supported_platforms

        assert Platform.SPOTIFY in platforms
        assert Platform.YOUTUBE_MUSIC in platforms
        assert Platform.DEEZER in platforms
        assert len(platforms) == 7


class TestSongServiceErrors:
    """Tests for SongService error handling."""

    def test_song_service_error(self) -> None:
        """Test SongServiceError."""
        error = SongServiceError("Test error")
        assert str(error) == "Test error"

    def test_unsupported_url_error(self) -> None:
        """Test UnsupportedURLError inherits from SongServiceError."""
        error = UnsupportedURLError("Unsupported URL")
        assert isinstance(error, SongServiceError)
        assert str(error) == "Unsupported URL"


class TestSongServiceResolve:
    """Tests for SongService URL resolution."""

    @pytest.mark.asyncio
    async def test_resolve_url_unsupported(self, song_service: SongService) -> None:
        """Test resolving unsupported URL raises error."""
        with pytest.raises(UnsupportedURLError):
            await song_service.resolve_url("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_track_unsupported(self, song_service: SongService) -> None:
        """Test getting track from unsupported URL raises error."""
        with pytest.raises(UnsupportedURLError):
            await song_service.get_track("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_album_unsupported(self, song_service: SongService) -> None:
        """Test getting album from unsupported URL raises error."""
        with pytest.raises(UnsupportedURLError):
            await song_service.get_album("https://example.com/album/123")

    @pytest.mark.asyncio
    async def test_get_playlist_unsupported(self, song_service: SongService) -> None:
        """Test getting playlist from unsupported URL raises error."""
        with pytest.raises(UnsupportedURLError):
            await song_service.get_playlist("https://example.com/playlist/123")

    @pytest.mark.asyncio
    async def test_get_artist_unsupported(self, song_service: SongService) -> None:
        """Test getting artist from unsupported URL raises error."""
        with pytest.raises(UnsupportedURLError):
            await song_service.get_artist("https://example.com/artist/123")


class TestSongServiceSearch:
    """Tests for SongService search."""

    @pytest.mark.asyncio
    async def test_search_unsupported_platform(self, song_service: SongService) -> None:
        """Test searching on platform without provider raises error."""
        # Clear the providers to simulate no provider for a platform
        song_service._providers = {}

        with pytest.raises(UnsupportedURLError):
            await song_service.search("test query", platform=Platform.SPOTIFY)


class TestGetSongService:
    """Tests for get_song_service function."""

    def test_get_song_service_returns_instance(self) -> None:
        """Test get_song_service returns a SongService."""
        # Reset global instance
        import spotdl.core.services.song as song_module
        song_module._song_service = None

        service = get_song_service()
        assert isinstance(service, SongService)

    def test_get_song_service_singleton(self) -> None:
        """Test get_song_service returns same instance."""
        import spotdl.core.services.song as song_module
        song_module._song_service = None

        service1 = get_song_service()
        service2 = get_song_service()
        assert service1 is service2
