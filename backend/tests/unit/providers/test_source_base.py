"""Tests for base source provider."""

import re

import pytest

from spotdl.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)


class TestSourceProviderErrors:
    """Tests for source provider exceptions."""

    def test_source_provider_error(self) -> None:
        """Test SourceProviderError."""
        error = SourceProviderError("Test error")
        assert str(error) == "Test error"

    def test_invalid_url_error(self) -> None:
        """Test InvalidURLError inherits from SourceProviderError."""
        error = InvalidURLError("Invalid URL")
        assert isinstance(error, SourceProviderError)
        assert str(error) == "Invalid URL"

    def test_track_not_found_error(self) -> None:
        """Test TrackNotFoundError inherits from SourceProviderError."""
        error = TrackNotFoundError("Track not found")
        assert isinstance(error, SourceProviderError)
        assert str(error) == "Track not found"


class ConcreteProvider(SourceProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"
    url_patterns = [
        re.compile(r"https://test\.com/(track|album|playlist|artist)/(\w+)"),
    ]

    async def get_track(self, url: str):
        pass

    async def get_album(self, url: str):
        pass

    async def get_playlist(self, url: str):
        pass

    async def get_artist(self, url: str):
        pass

    async def search(self, query: str, limit: int = 10):
        return []


class TestSourceProviderBase:
    """Tests for SourceProvider base class."""

    def test_matches_url(self) -> None:
        """Test URL matching."""
        assert ConcreteProvider.matches_url("https://test.com/track/abc123")
        assert ConcreteProvider.matches_url("https://test.com/album/xyz789")
        assert not ConcreteProvider.matches_url("https://other.com/track/abc123")

    def test_extract_id(self) -> None:
        """Test ID extraction from URL."""
        assert ConcreteProvider.extract_id("https://test.com/track/abc123") == "track"
        assert ConcreteProvider.extract_id("https://other.com/track/123") is None

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://test.com/track/abc", "track"),
            ("https://test.com/album/xyz", "album"),
            ("https://test.com/playlist/list", "playlist"),
            ("https://test.com/artist/art", "artist"),
            ("https://test.com/song/abc", "track"),  # song normalized to track
            ("https://test.com/other/xyz", None),
        ],
    )
    def test_get_url_type(self, url: str, expected: str | None) -> None:
        """Test URL type detection."""
        assert ConcreteProvider.get_url_type(url) == expected

    def test_provider_attributes(self) -> None:
        """Test provider has required attributes."""
        provider = ConcreteProvider()
        assert provider.name == "test"
        assert provider.display_name == "Test Provider"
        assert len(provider.url_patterns) > 0

    def test_extract_id_no_groups(self) -> None:
        """Test extract_id returns None when pattern has no groups."""

        class NoGroupProvider(SourceProvider):
            name = "nogroup"
            display_name = "No Group"
            url_patterns = [re.compile(r"https://nogroup\.com/track")]

            async def get_track(self, url: str):
                pass

            async def get_album(self, url: str):
                pass

            async def get_playlist(self, url: str):
                pass

            async def get_artist(self, url: str):
                pass

            async def search(self, query: str, limit: int = 10):
                return []

        # Match but no capture groups
        result = NoGroupProvider.extract_id("https://nogroup.com/track")
        assert result is None


class TestSourceProviderGetSongsFromUrl:
    """Tests for get_songs_from_url method."""

    @pytest.mark.asyncio
    async def test_get_songs_from_track_url(self) -> None:
        """Test getting songs from track URL."""
        from unittest.mock import AsyncMock, MagicMock

        provider = ConcreteProvider()
        mock_song = MagicMock()
        provider.get_track = AsyncMock(return_value=mock_song)

        result = await provider.get_songs_from_url("https://test.com/track/abc")

        assert result == [mock_song]
        provider.get_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_songs_from_album_url(self) -> None:
        """Test getting songs from album URL."""
        from unittest.mock import AsyncMock, MagicMock

        provider = ConcreteProvider()
        mock_song1 = MagicMock()
        mock_song2 = MagicMock()
        mock_album = MagicMock()
        mock_album.songs = [mock_song1, mock_song2]
        provider.get_album = AsyncMock(return_value=mock_album)

        result = await provider.get_songs_from_url("https://test.com/album/xyz")

        assert len(result) == 2
        provider.get_album.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_songs_from_playlist_url(self) -> None:
        """Test getting songs from playlist URL."""
        from unittest.mock import AsyncMock, MagicMock

        provider = ConcreteProvider()
        mock_song = MagicMock()
        mock_playlist = MagicMock()
        mock_playlist.songs = [mock_song]
        provider.get_playlist = AsyncMock(return_value=mock_playlist)

        result = await provider.get_songs_from_url("https://test.com/playlist/list")

        assert len(result) == 1
        provider.get_playlist.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_songs_from_artist_url(self) -> None:
        """Test getting songs from artist URL."""
        from unittest.mock import AsyncMock, MagicMock

        provider = ConcreteProvider()
        mock_song = MagicMock()
        mock_artist = MagicMock()
        mock_artist.songs = [mock_song]
        provider.get_artist = AsyncMock(return_value=mock_artist)

        result = await provider.get_songs_from_url("https://test.com/artist/art")

        assert len(result) == 1
        provider.get_artist.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_songs_from_unknown_url_type(self) -> None:
        """Test getting songs from unknown URL type defaults to track."""
        from unittest.mock import AsyncMock, MagicMock

        provider = ConcreteProvider()
        mock_song = MagicMock()
        provider.get_track = AsyncMock(return_value=mock_song)

        # URL doesn't contain track/album/playlist/artist
        result = await provider.get_songs_from_url("https://test.com/other/123")

        assert result == [mock_song]
        provider.get_track.assert_called_once()
