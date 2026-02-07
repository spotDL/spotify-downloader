"""Unit tests for YouTube Music target provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from spotdl_core.providers.targets.base import SearchError
from spotdl_core.providers.targets.ytmusic import (
    YTMUSIC_URL_PATTERN,
    YouTubeMusicProvider,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestYouTubeMusicProvider:
    """Test YouTubeMusicProvider class."""

    @pytest.fixture
    def provider(self) -> YouTubeMusicProvider:
        """Create a YouTube Music provider instance."""
        return YouTubeMusicProvider()

    @pytest.fixture
    def provider_with_auth(self) -> YouTubeMusicProvider:
        """Create a YouTube Music provider with auth file."""
        return YouTubeMusicProvider(auth_file="/path/to/auth.json")

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing."""
        return Song(
            name="Bohemian Rhapsody",
            artists=["Queen"],
            artist="Queen",
            duration=354,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    @pytest.fixture
    def mock_ytmusic_song(self) -> dict:
        """Create mock YouTube Music song data."""
        return {
            "videoId": "fJ9rUzIMcZQ",
            "title": "Bohemian Rhapsody",
            "artists": [{"name": "Queen"}],
            "duration": "5:54",
            "duration_seconds": 354,
            "album": {"name": "A Night at the Opera"},
            "thumbnails": [
                {"url": "https://example.com/thumb1.jpg", "width": 60, "height": 60},
                {"url": "https://example.com/thumb2.jpg", "width": 120, "height": 120},
                {"url": "https://example.com/thumb3.jpg", "width": 480, "height": 480},
            ],
            "isExplicit": False,
        }

    def test_initialization(self, provider: YouTubeMusicProvider):
        """Test provider initialization."""
        assert provider.name == "youtube_music"
        assert provider.display_name == "YouTube Music"
        assert provider._auth_file is None
        assert provider._client is None

    def test_initialization_with_auth(self, provider_with_auth: YouTubeMusicProvider):
        """Test initialization with auth file."""
        assert provider_with_auth._auth_file == "/path/to/auth.json"

    def test_get_client(self, provider: YouTubeMusicProvider):
        """Test YTMusic client creation."""
        with patch("spotdl_core.providers.targets.ytmusic.YTMusic") as mock_ytmusic:
            mock_ytmusic.return_value = MagicMock()
            client = provider._get_client()
            assert client is not None
            mock_ytmusic.assert_called_once_with()

            # Second call should return same client
            client2 = provider._get_client()
            assert client2 is client

    def test_get_client_with_auth(self, provider_with_auth: YouTubeMusicProvider):
        """Test YTMusic client creation with auth."""
        with patch("spotdl_core.providers.targets.ytmusic.YTMusic") as mock_ytmusic:
            mock_ytmusic.return_value = MagicMock()
            provider_with_auth._get_client()
            mock_ytmusic.assert_called_once_with("/path/to/auth.json")

    def test_result_to_result_full_data(
        self, provider: YouTubeMusicProvider, mock_ytmusic_song: dict
    ):
        """Test converting YouTube Music data to Result with full data."""
        result = provider._result_to_result(mock_ytmusic_song)

        assert isinstance(result, Result)
        assert result.name == "Bohemian Rhapsody"
        assert result.artist == "Queen"
        assert result.artists == ("Queen",)
        assert result.duration == 354
        assert result.platform == TargetPlatform.YOUTUBE_MUSIC
        assert result.platform_id == "fJ9rUzIMcZQ"
        assert result.url == "https://music.youtube.com/watch?v=fJ9rUzIMcZQ"
        assert result.album_name == "A Night at the Opera"
        assert result.explicit is False
        assert result.cover_url == "https://example.com/thumb3.jpg"

    def test_result_to_result_minimal_data(self, provider: YouTubeMusicProvider):
        """Test converting YouTube Music data with minimal data."""
        song_data = {
            "videoId": "test123",
            "title": "Test Song",
        }
        result = provider._result_to_result(song_data)

        assert result.name == "Test Song"
        assert result.artist == "Unknown"
        assert result.duration == 0
        assert result.platform_id == "test123"

    def test_result_to_result_duration_from_string_mm_ss(
        self, provider: YouTubeMusicProvider
    ):
        """Test duration parsing from MM:SS string."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "duration": "3:45",
        }
        result = provider._result_to_result(song_data)
        assert result.duration == 225  # 3*60 + 45

    def test_result_to_result_duration_from_string_hh_mm_ss(
        self, provider: YouTubeMusicProvider
    ):
        """Test duration parsing from HH:MM:SS string."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "duration": "1:30:45",
        }
        result = provider._result_to_result(song_data)
        assert result.duration == 5445  # 1*3600 + 30*60 + 45

    def test_result_to_result_duration_invalid_string(
        self, provider: YouTubeMusicProvider
    ):
        """Test duration parsing with invalid string."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "duration": "invalid",
        }
        result = provider._result_to_result(song_data)
        assert result.duration == 0

    def test_result_to_result_duration_seconds_takes_precedence(
        self, provider: YouTubeMusicProvider
    ):
        """Test that duration_seconds takes precedence over duration string."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "duration": "3:45",
            "duration_seconds": 300,
        }
        result = provider._result_to_result(song_data)
        assert result.duration == 300

    def test_result_to_result_artists_from_artists_list(
        self, provider: YouTubeMusicProvider
    ):
        """Test artists extraction from artists list."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
        }
        result = provider._result_to_result(song_data)
        assert result.artists == ("Artist 1", "Artist 2")
        assert result.artist == "Artist 1"

    def test_result_to_result_artists_fallback_to_author(
        self, provider: YouTubeMusicProvider
    ):
        """Test artists fallback to author field."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "author": "Test Author",
        }
        result = provider._result_to_result(song_data)
        assert result.artists == ("Test Author",)
        assert result.artist == "Test Author"

    def test_result_to_result_artists_empty_list(self, provider: YouTubeMusicProvider):
        """Test artists with empty list."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "artists": [],
        }
        result = provider._result_to_result(song_data)
        assert result.artist == "Unknown"

    def test_result_to_result_album_none(self, provider: YouTubeMusicProvider):
        """Test album handling when None."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "album": None,
        }
        result = provider._result_to_result(song_data)
        assert result.album_name == ""

    def test_result_to_result_no_thumbnails(self, provider: YouTubeMusicProvider):
        """Test result with no thumbnails."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "thumbnails": [],
        }
        result = provider._result_to_result(song_data)
        assert result.cover_url is None

    def test_result_to_result_selects_highest_quality_thumbnail(
        self, provider: YouTubeMusicProvider
    ):
        """Test that highest quality thumbnail is selected."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "thumbnails": [
                {"url": "small.jpg", "width": 60, "height": 60},
                {"url": "large.jpg", "width": 1200, "height": 1200},
                {"url": "medium.jpg", "width": 480, "height": 480},
            ],
        }
        result = provider._result_to_result(song_data)
        assert result.cover_url == "large.jpg"

    def test_result_to_result_explicit_true(self, provider: YouTubeMusicProvider):
        """Test explicit flag when true."""
        song_data = {
            "videoId": "test123",
            "title": "Test",
            "isExplicit": True,
        }
        result = provider._result_to_result(song_data)
        assert result.explicit is True

    @pytest.mark.asyncio
    async def test_search_success(
        self,
        provider: YouTubeMusicProvider,
        sample_song: Song,
        mock_ytmusic_song: dict,
    ):
        """Test successful search."""
        mock_client = MagicMock()
        mock_client.search.return_value = [mock_ytmusic_song]

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=10)

            assert len(results) == 1
            assert results[0].name == "Bohemian Rhapsody"
            assert results[0].platform == TargetPlatform.YOUTUBE_MUSIC
            mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_filters_no_video_id(
        self, provider: YouTubeMusicProvider, sample_song: Song
    ):
        """Test that results without videoId are filtered out."""
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"videoId": None, "title": "No ID"},
            {"videoId": "test123", "title": "Has ID"},
            {"title": "Missing videoId"},
        ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song)

            assert len(results) == 1
            assert results[0].platform_id == "test123"

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, provider: YouTubeMusicProvider, sample_song: Song
    ):
        """Test that search respects limit parameter."""
        mock_songs = [
            {"videoId": f"video{i}", "title": f"Song {i}"} for i in range(20)
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_songs

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=5)

            # YTMusic limit is passed to client.search
            call_args = mock_client.search.call_args
            assert call_args[1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_error(
        self, provider: YouTubeMusicProvider, sample_song: Song
    ):
        """Test search with error."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Search failed")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="YouTube Music search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_search_by_isrc_success(self, provider: YouTubeMusicProvider):
        """Test successful ISRC search."""
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"videoId": "test123", "title": "Test Song"}
        ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")

            assert result is not None
            assert result.platform_id == "test123"
            mock_client.search.assert_called_once_with(
                "USRC12345678", filter="songs", limit=1
            )

    @pytest.mark.asyncio
    async def test_search_by_isrc_no_results(self, provider: YouTubeMusicProvider):
        """Test ISRC search with no results."""
        mock_client = MagicMock()
        mock_client.search.return_value = []

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_by_isrc_error(self, provider: YouTubeMusicProvider):
        """Test ISRC search with error."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_song_info_success(self, provider: YouTubeMusicProvider):
        """Test getting song info successfully."""
        mock_client = MagicMock()
        mock_client.get_song.return_value = {
            "videoDetails": {
                "videoId": "test123",
                "title": "Test Song",
                "author": "Test Artist",
                "lengthSeconds": 180,
                "thumbnail": {
                    "thumbnails": [{"url": "test.jpg", "width": 120, "height": 120}]
                },
            }
        }

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_song_info("test123")

            assert result is not None
            assert result.platform_id == "test123"
            assert result.name == "Test Song"

    @pytest.mark.asyncio
    async def test_get_song_info_none_response(self, provider: YouTubeMusicProvider):
        """Test getting song info with None response."""
        mock_client = MagicMock()
        mock_client.get_song.return_value = None

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_song_info("test123")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_song_info_error(self, provider: YouTubeMusicProvider):
        """Test getting song info with error."""
        mock_client = MagicMock()
        mock_client.get_song.side_effect = Exception("Error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_song_info("test123")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_albums_success(self, provider: YouTubeMusicProvider):
        """Test successful album search."""
        mock_albums = [
            {"browseId": "album1", "title": "Album 1"},
            {"browseId": "album2", "title": "Album 2"},
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_albums

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search_albums("test query", limit=5)

            assert len(results) == 2
            assert results[0]["title"] == "Album 1"
            mock_client.search.assert_called_once_with(
                "test query", filter="albums", limit=5
            )

    @pytest.mark.asyncio
    async def test_search_albums_error(self, provider: YouTubeMusicProvider):
        """Test album search with error."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search_albums("test query")
            assert results == []

    def test_extract_video_id_ytmusic_url(self):
        """Test extracting video ID from YouTube Music URL."""
        url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = YouTubeMusicProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_standard_youtube_url(self):
        """Test extracting video ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = YouTubeMusicProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_params(self):
        """Test extracting video ID from URL with parameters."""
        url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx"
        video_id = YouTubeMusicProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test extracting video ID from invalid URL."""
        url = "https://www.example.com/video"
        video_id = YouTubeMusicProvider.extract_video_id(url)
        assert video_id is None

    def test_extract_video_id_empty_string(self):
        """Test extracting video ID from empty string."""
        video_id = YouTubeMusicProvider.extract_video_id("")
        assert video_id is None

    def test_ytmusic_url_pattern(self):
        """Test YouTube Music URL regex pattern."""
        valid_urls = [
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "music.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            match = YTMUSIC_URL_PATTERN.search(url)
            assert match is not None, f"Failed to match: {url}"
            assert match.group(1) == "dQw4w9WgXcQ"

    def test_ytmusic_url_pattern_invalid(self):
        """Test YouTube Music URL pattern with invalid URLs."""
        invalid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/123456",
            "not a url",
            "",
        ]

        for url in invalid_urls:
            match = YTMUSIC_URL_PATTERN.search(url)
            assert match is None, f"Should not match: {url}"
