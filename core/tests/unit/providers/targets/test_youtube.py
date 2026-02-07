"""Unit tests for YouTube target provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from spotdl_core.providers.targets.base import SearchError
from spotdl_core.providers.targets.youtube import (
    YOUTUBE_URL_PATTERN,
    YouTubeProvider,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestYouTubeProvider:
    """Test YouTubeProvider class."""

    @pytest.fixture
    def provider(self) -> YouTubeProvider:
        """Create a YouTube provider instance."""
        return YouTubeProvider()

    @pytest.fixture
    def provider_with_custom_instance(self) -> YouTubeProvider:
        """Create a YouTube provider with custom instance."""
        return YouTubeProvider(invidious_instance="https://custom.instance.com")

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing."""
        return Song(
            name="Never Gonna Give You Up",
            artists=["Rick Astley"],
            artist="Rick Astley",
            duration=213,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    @pytest.fixture
    def mock_invidious_video(self) -> dict:
        """Create mock Invidious video data."""
        return {
            "type": "video",
            "videoId": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "author": "Rick Astley",
            "lengthSeconds": 213,
            "viewCount": 1000000,
            "isVerified": True,
            "videoThumbnails": [
                {"url": "https://example.com/thumb1.jpg", "width": 120, "height": 90},
                {"url": "https://example.com/thumb2.jpg", "width": 320, "height": 180},
                {"url": "https://example.com/thumb3.jpg", "width": 1280, "height": 720},
            ],
        }

    def test_initialization(self, provider: YouTubeProvider):
        """Test provider initialization."""
        assert provider.name == "youtube"
        assert provider.display_name == "YouTube"
        assert provider._timeout == 30.0
        assert provider._client is None
        assert provider._working_instance is None

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        provider = YouTubeProvider(timeout=60.0)
        assert provider._timeout == 60.0

    def test_initialization_with_custom_instance(
        self, provider_with_custom_instance: YouTubeProvider
    ):
        """Test initialization with custom Invidious instance."""
        assert (
            provider_with_custom_instance._invidious_instance
            == "https://custom.instance.com"
        )

    def test_invidious_instances_list(self):
        """Test that Invidious instances list is defined."""
        assert len(YouTubeProvider.INVIDIOUS_INSTANCES) > 0
        assert all(
            isinstance(instance, str) for instance in YouTubeProvider.INVIDIOUS_INSTANCES
        )
        assert all(
            instance.startswith("https://")
            for instance in YouTubeProvider.INVIDIOUS_INSTANCES
        )

    @pytest.mark.asyncio
    async def test_get_client(self, provider: YouTubeProvider):
        """Test HTTP client creation."""
        client = await provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Second call should return same client
        client2 = await provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_get_client_recreates_if_closed(self, provider: YouTubeProvider):
        """Test that client is recreated if closed."""
        client1 = await provider._get_client()
        await client1.aclose()

        client2 = await provider._get_client()
        assert client2 is not client1
        assert not client2.is_closed

    @pytest.mark.asyncio
    async def test_close(self, provider: YouTubeProvider):
        """Test closing the provider."""
        client = await provider._get_client()
        assert not client.is_closed

        await provider.close()
        assert client.is_closed
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, provider: YouTubeProvider):
        """Test closing without creating client."""
        await provider.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_working_instance_with_custom_instance(
        self, provider_with_custom_instance: YouTubeProvider
    ):
        """Test getting working instance when custom instance is set."""
        instance = await provider_with_custom_instance._get_working_instance()
        assert instance == "https://custom.instance.com"

    @pytest.mark.asyncio
    async def test_get_working_instance_uses_cached(self, provider: YouTubeProvider):
        """Test that cached working instance is used."""
        provider._working_instance = "https://cached.instance.com"
        instance = await provider._get_working_instance()
        assert instance == "https://cached.instance.com"

    @pytest.mark.asyncio
    async def test_get_working_instance_finds_working(self, provider: YouTubeProvider):
        """Test finding a working instance."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            instance = await provider._get_working_instance()
            assert instance in YouTubeProvider.INVIDIOUS_INSTANCES
            assert provider._working_instance == instance

    @pytest.mark.asyncio
    async def test_get_working_instance_no_working(self, provider: YouTubeProvider):
        """Test when no working instance is found."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="No working Invidious instance found"):
                await provider._get_working_instance()

    def test_result_to_result_full_data(
        self, provider: YouTubeProvider, mock_invidious_video: dict
    ):
        """Test converting Invidious video to Result with full data."""
        result = provider._result_to_result(mock_invidious_video)

        assert isinstance(result, Result)
        assert result.name == "Rick Astley - Never Gonna Give You Up"
        assert result.artist == "Rick Astley"
        assert result.artists == ("Rick Astley",)
        assert result.duration == 213
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.platform_id == "dQw4w9WgXcQ"
        assert result.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result.views == 1000000
        assert result.verified is True
        assert result.cover_url == "https://example.com/thumb3.jpg"

    def test_result_to_result_minimal_data(self, provider: YouTubeProvider):
        """Test converting Invidious video with minimal data."""
        video = {
            "videoId": "test123",
            "title": "Test Video",
        }
        result = provider._result_to_result(video)

        assert result.name == "Test Video"
        assert result.artist == "Unknown"
        assert result.duration == 0
        assert result.platform_id == "test123"
        assert result.cover_url is None

    def test_result_to_result_no_thumbnails(self, provider: YouTubeProvider):
        """Test converting video without thumbnails."""
        video = {
            "videoId": "test123",
            "title": "Test Video",
            "author": "Test Author",
            "videoThumbnails": [],
        }
        result = provider._result_to_result(video)
        assert result.cover_url is None

    def test_result_to_result_selects_highest_quality_thumbnail(
        self, provider: YouTubeProvider
    ):
        """Test that highest quality thumbnail is selected."""
        video = {
            "videoId": "test123",
            "title": "Test",
            "videoThumbnails": [
                {"url": "small.jpg", "width": 120, "height": 90},
                {"url": "large.jpg", "width": 1920, "height": 1080},
                {"url": "medium.jpg", "width": 640, "height": 480},
            ],
        }
        result = provider._result_to_result(video)
        assert result.cover_url == "large.jpg"

    @pytest.mark.asyncio
    async def test_search_success(
        self, provider: YouTubeProvider, sample_song: Song, mock_invidious_video: dict
    ):
        """Test successful search."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_invidious_video]
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=10)

            assert len(results) == 1
            assert results[0].name == "Rick Astley - Never Gonna Give You Up"
            assert results[0].platform == TargetPlatform.YOUTUBE

    @pytest.mark.asyncio
    async def test_search_filters_non_videos(
        self, provider: YouTubeProvider, sample_song: Song
    ):
        """Test that non-video results are filtered out."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type": "channel", "videoId": "channel123"},
            {"type": "video", "videoId": "video123", "title": "Test Video"},
            {"type": "playlist", "videoId": "playlist123"},
        ]
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song)

            assert len(results) == 1
            assert results[0].platform_id == "video123"

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, provider: YouTubeProvider, sample_song: Song
    ):
        """Test that search respects limit parameter."""
        mock_videos = [
            {"type": "video", "videoId": f"video{i}", "title": f"Video {i}"}
            for i in range(20)
        ]

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_videos
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=5)

            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_http_error(
        self, provider: YouTubeProvider, sample_song: Song
    ):
        """Test search with HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="YouTube search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_search_by_isrc_success(self, provider: YouTubeProvider):
        """Test successful ISRC search."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type": "video", "videoId": "test123", "title": "Test"}
        ]
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")

            assert result is not None
            assert result.platform_id == "test123"

    @pytest.mark.asyncio
    async def test_search_by_isrc_no_results(self, provider: YouTubeProvider):
        """Test ISRC search with no results."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_by_isrc_error(self, provider: YouTubeProvider):
        """Test ISRC search with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.search_by_isrc("USRC12345678")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_video_info_success(self, provider: YouTubeProvider):
        """Test getting video info successfully."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videoId": "test123",
            "title": "Test Video",
            "author": "Test Author",
        }
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_video_info("test123")

            assert result is not None
            assert result.platform_id == "test123"
            assert result.name == "Test Video"

    @pytest.mark.asyncio
    async def test_get_video_info_error(self, provider: YouTubeProvider):
        """Test getting video info with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        provider._working_instance = "https://test.instance.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_video_info("test123")
            assert result is None

    def test_extract_video_id_standard_url(self):
        """Test extracting video ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = YouTubeProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self):
        """Test extracting video ID from short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = YouTubeProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_no_protocol(self):
        """Test extracting video ID from URL without protocol."""
        url = "youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = YouTubeProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_timestamp(self):
        """Test extracting video ID from URL with timestamp."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"
        video_id = YouTubeProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test extracting video ID from invalid URL."""
        url = "https://www.example.com/video"
        video_id = YouTubeProvider.extract_video_id(url)
        assert video_id is None

    def test_extract_video_id_empty_string(self):
        """Test extracting video ID from empty string."""
        video_id = YouTubeProvider.extract_video_id("")
        assert video_id is None

    def test_youtube_url_pattern(self):
        """Test YouTube URL regex pattern."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            match = YOUTUBE_URL_PATTERN.search(url)
            assert match is not None, f"Failed to match: {url}"
            assert match.group(1) == "dQw4w9WgXcQ"

    def test_youtube_url_pattern_invalid(self):
        """Test YouTube URL pattern with invalid URLs."""
        invalid_urls = [
            "https://vimeo.com/123456",
            "https://www.youtube.com/channel/UCxxx",
            "not a url",
            "",
        ]

        for url in invalid_urls:
            match = YOUTUBE_URL_PATTERN.search(url)
            assert match is None, f"Should not match: {url}"
