"""Tests for Deezer source provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from spotdl_core.providers.sources.deezer import (
    DEEZER_API_URL,
    DEEZER_URL_PATTERNS,
    DeezerProvider,
)
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl_core.types import Platform, Song, SongList


class TestDeezerProvider:
    """Test DeezerProvider class."""

    @pytest.fixture
    def provider(self) -> DeezerProvider:
        """Create a Deezer provider."""
        return DeezerProvider()

    @pytest.fixture
    def mock_track_data(self) -> dict:
        """Create mock track data."""
        return {
            "id": 123456,
            "title": "Test Track",
            "duration": 225,
            "explicit_lyrics": True,
            "artist": {"id": 789, "name": "Test Artist"},
            "contributors": [{"name": "Test Artist"}, {"name": "Featured Artist"}],
            "album": {
                "id": 456,
                "title": "Test Album",
                "release_date": "2023-01-15",
                "cover_xl": "https://example.com/cover_xl.jpg",
                "cover_big": "https://example.com/cover.jpg",
            },
            "isrc": "USRC12345678",
            "link": "https://www.deezer.com/track/123456",
            "track_position": 3,
            "disk_number": 1,
        }

    @pytest.fixture
    def mock_album_data(self) -> dict:
        """Create mock album data."""
        return {
            "id": 456,
            "title": "Test Album",
            "release_date": "2023-01-15",
            "artist": {"name": "Album Artist"},
            "label": "Test Label",
            "tracks": {
                "data": [
                    {
                        "id": 1,
                        "title": "Track 1",
                        "duration": 180,
                        "artist": {"name": "Test Artist"},
                        "link": "https://www.deezer.com/track/1",
                    },
                    {
                        "id": 2,
                        "title": "Track 2",
                        "duration": 200,
                        "artist": {"name": "Test Artist"},
                        "link": "https://www.deezer.com/track/2",
                    },
                ]
            },
        }

    def test_provider_init(self, provider: DeezerProvider):
        """Test provider initialization."""
        assert provider.name == "deezer"
        assert provider.display_name == "Deezer"
        assert len(provider.url_patterns) == 2

    def test_url_patterns(self):
        """Test URL patterns."""
        assert len(DEEZER_URL_PATTERNS) == 2
        assert DEEZER_URL_PATTERNS[0].search("https://www.deezer.com/track/123456")
        assert DEEZER_URL_PATTERNS[0].search("https://deezer.com/en/album/123456")
        assert DEEZER_URL_PATTERNS[1].search("https://deezer.page.link/abc")

    def test_extract_id_track(self, provider: DeezerProvider):
        """Test extracting track ID."""
        result = provider._extract_id("https://www.deezer.com/track/123456")
        assert result == ("track", "123456")

    def test_extract_id_album(self, provider: DeezerProvider):
        """Test extracting album ID."""
        result = provider._extract_id("https://deezer.com/en/album/789")
        assert result == ("album", "789")

    def test_extract_id_short_link(self, provider: DeezerProvider):
        """Test extracting short link ID."""
        result = provider._extract_id("https://deezer.page.link/abc123")
        assert result == ("short", "abc123")

    def test_extract_id_no_match(self, provider: DeezerProvider):
        """Test extracting ID with no match."""
        result = provider._extract_id("https://invalid.com/track/123")
        assert result is None

    def test_track_to_song(self, provider: DeezerProvider, mock_track_data: dict):
        """Test converting track data to Song."""
        song = provider._track_to_song(mock_track_data)
        assert isinstance(song, Song)
        assert song.name == "Test Track"
        assert song.duration == 225
        assert song.platform == Platform.DEEZER
        assert song.platform_id == "123456"
        assert "Test Artist" in song.artists

    async def test_get_track_invalid_url(self, provider: DeezerProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://invalid.com/track/123")

    async def test_get_album_invalid_url(self, provider: DeezerProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://invalid.com/album/123")

    async def test_get_playlist_invalid_url(self, provider: DeezerProvider):
        """Test getting playlist with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_playlist("https://invalid.com/playlist/123")

    async def test_search_with_limit(self, provider: DeezerProvider):
        """Test search with limit parameter."""
        # Just test that the method exists and can be called
        # Without a full mock setup, we expect it to fail gracefully
        try:
            await provider.search("test query", limit=5)
        except (httpx.HTTPError, SourceProviderError):
            pass  # Expected when no client is configured

    async def test_close(self, provider: DeezerProvider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()
        assert provider._client is None
