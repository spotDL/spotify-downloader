"""Unit tests for Piped target provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from spotdl_core.providers.targets.base import SearchError
from spotdl_core.providers.targets.piped import (
    PIPED_URL_PATTERN,
    PipedProvider,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestPipedProvider:
    """Test PipedProvider class."""

    @pytest.fixture
    def provider(self) -> PipedProvider:
        """Create a Piped provider instance."""
        return PipedProvider()

    @pytest.fixture
    def provider_with_custom_instance(self) -> PipedProvider:
        """Create a Piped provider with custom instance."""
        return PipedProvider(piped_instance="https://custom.piped.com")

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing."""
        return Song(
            name="Test Video",
            artists=["Test Channel"],
            artist="Test Channel",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    @pytest.fixture
    def mock_piped_item(self) -> dict:
        """Create mock Piped search item."""
        return {
            "type": "stream",
            "url": "/watch?v=dQw4w9WgXcQ",
            "title": "Test Video",
            "uploaderName": "Test Channel",
            "uploader": "Test Channel",
            "duration": 213,
            "thumbnail": "https://example.com/thumb.jpg",
            "views": 1000000,
            "uploaderVerified": True,
        }

    def test_initialization(self, provider: PipedProvider):
        """Test provider initialization."""
        assert provider.name == "piped"
        assert provider.display_name == "Piped"
        assert provider._timeout == 30.0
        assert provider._client is None
        assert provider._working_instance is None

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        provider = PipedProvider(timeout=60.0)
        assert provider._timeout == 60.0

    def test_initialization_with_custom_instance(
        self, provider_with_custom_instance: PipedProvider
    ):
        """Test initialization with custom Piped instance."""
        assert (
            provider_with_custom_instance._piped_instance == "https://custom.piped.com"
        )

    def test_piped_instances_list(self):
        """Test that Piped instances list is defined."""
        assert len(PipedProvider.PIPED_INSTANCES) > 0
        assert all(isinstance(instance, str) for instance in PipedProvider.PIPED_INSTANCES)
        assert all(
            instance.startswith("https://") for instance in PipedProvider.PIPED_INSTANCES
        )

    @pytest.mark.asyncio
    async def test_get_client(self, provider: PipedProvider):
        """Test HTTP client creation."""
        client = await provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Second call should return same client
        client2 = await provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_get_client_recreates_if_closed(self, provider: PipedProvider):
        """Test that client is recreated if closed."""
        client1 = await provider._get_client()
        await client1.aclose()

        client2 = await provider._get_client()
        assert client2 is not client1
        assert not client2.is_closed

    @pytest.mark.asyncio
    async def test_close(self, provider: PipedProvider):
        """Test closing the provider."""
        client = await provider._get_client()
        assert not client.is_closed

        await provider.close()
        assert client.is_closed
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, provider: PipedProvider):
        """Test closing without creating client."""
        await provider.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_working_instance_with_custom_instance(
        self, provider_with_custom_instance: PipedProvider
    ):
        """Test getting working instance when custom instance is set."""
        instance = await provider_with_custom_instance._get_working_instance()
        assert instance == "https://custom.piped.com"

    @pytest.mark.asyncio
    async def test_get_working_instance_uses_cached(self, provider: PipedProvider):
        """Test that cached working instance is used."""
        provider._working_instance = "https://cached.piped.com"
        instance = await provider._get_working_instance()
        assert instance == "https://cached.piped.com"

    @pytest.mark.asyncio
    async def test_get_working_instance_finds_working(self, provider: PipedProvider):
        """Test finding a working instance."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            instance = await provider._get_working_instance()
            assert instance in PipedProvider.PIPED_INSTANCES
            assert provider._working_instance == instance

    @pytest.mark.asyncio
    async def test_get_working_instance_no_working(self, provider: PipedProvider):
        """Test when no working instance is found."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="No working Piped instance found"):
                await provider._get_working_instance()

    def test_item_to_result_full_data(
        self, provider: PipedProvider, mock_piped_item: dict
    ):
        """Test converting Piped item to Result with full data."""
        result = provider._item_to_result(mock_piped_item)

        assert isinstance(result, Result)
        assert result.name == "Test Video"
        assert result.artist == "Test Channel"
        assert result.artists == ("Test Channel",)
        assert result.duration == 213
        assert result.platform == TargetPlatform.PIPED
        assert result.platform_id == "dQw4w9WgXcQ"
        assert result.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result.cover_url == "https://example.com/thumb.jpg"
        assert result.views == 1000000
        assert result.verified is True

    def test_item_to_result_minimal_data(self, provider: PipedProvider):
        """Test converting Piped item with minimal data."""
        item = {
            "url": "/watch?v=test123",
            "title": "Test",
        }
        result = provider._item_to_result(item)

        assert result.name == "Test"
        assert result.artist == "Unknown"
        assert result.duration == 0
        assert result.platform_id == "test123"

    def test_item_to_result_no_video_id(self, provider: PipedProvider):
        """Test converting item without valid video ID."""
        item = {
            "url": "/invalid",
            "title": "Test",
        }
        result = provider._item_to_result(item)

        assert result.platform_id == ""
        assert result.url == ""

    def test_item_to_result_uploader_fallback(self, provider: PipedProvider):
        """Test uploader name fallback."""
        item = {
            "url": "/watch?v=test123",
            "title": "Test",
            "uploader": "Fallback Name",
        }
        result = provider._item_to_result(item)
        assert result.artist == "Fallback Name"

    @pytest.mark.asyncio
    async def test_search_success(
        self, provider: PipedProvider, sample_song: Song, mock_piped_item: dict
    ):
        """Test successful search."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [mock_piped_item]}
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=10)

            assert len(results) == 1
            assert results[0].name == "Test Video"
            assert results[0].platform == TargetPlatform.PIPED

    @pytest.mark.asyncio
    async def test_search_filters_non_streams(
        self, provider: PipedProvider, sample_song: Song
    ):
        """Test that non-stream results are filtered out."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"type": "channel", "url": "/channel/123"},
                {"type": "stream", "url": "/watch?v=test123", "title": "Video"},
                {"type": "playlist", "url": "/playlist/456"},
            ]
        }
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song)

            assert len(results) == 1
            assert results[0].platform_id == "test123"

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, provider: PipedProvider, sample_song: Song
    ):
        """Test that search respects limit parameter."""
        mock_items = [
            {"type": "stream", "url": f"/watch?v=video{i}", "title": f"Video {i}"}
            for i in range(20)
        ]

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": mock_items}
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=5)

            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_http_error(self, provider: PipedProvider, sample_song: Song):
        """Test search with HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="Piped search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_search_generic_error(
        self, provider: PipedProvider, sample_song: Song
    ):
        """Test search with generic error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Generic error")

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="Piped search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_get_video_info_success(self, provider: PipedProvider):
        """Test getting video info successfully."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 180,
            "thumbnailUrl": "https://example.com/thumb.jpg",
            "views": 1000,
            "uploaderVerified": True,
        }
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_video_info("test123")

            assert result is not None
            assert result.name == "Test Video"
            assert result.platform_id == "test123"

    @pytest.mark.asyncio
    async def test_get_video_info_error(self, provider: PipedProvider):
        """Test getting video info with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_video_info("test123")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_audio_stream_url_success(self, provider: PipedProvider):
        """Test getting audio stream URL successfully."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audioStreams": [
                {"url": "https://example.com/low.m4a", "bitrate": 128},
                {"url": "https://example.com/high.m4a", "bitrate": 256},
                {"url": "https://example.com/medium.m4a", "bitrate": 192},
            ]
        }
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            url = await provider.get_audio_stream_url("test123")

            assert url == "https://example.com/high.m4a"  # Highest bitrate

    @pytest.mark.asyncio
    async def test_get_audio_stream_url_no_streams(self, provider: PipedProvider):
        """Test getting audio stream URL with no streams."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"audioStreams": []}
        mock_client.get.return_value = mock_response

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            url = await provider.get_audio_stream_url("test123")
            assert url is None

    @pytest.mark.asyncio
    async def test_get_audio_stream_url_error(self, provider: PipedProvider):
        """Test getting audio stream URL with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        provider._working_instance = "https://test.piped.com"

        with patch.object(provider, "_get_client", return_value=mock_client):
            url = await provider.get_audio_stream_url("test123")
            assert url is None

    def test_extract_video_id_piped_url(self):
        """Test extracting video ID from Piped URL."""
        urls = [
            "https://piped.video/watch?v=dQw4w9WgXcQ",
            "https://piped.kavin.rocks/watch?v=dQw4w9WgXcQ",
            "https://piped.silkky.cloud/watch?v=dQw4w9WgXcQ",
        ]

        for url in urls:
            video_id = PipedProvider.extract_video_id(url)
            assert video_id == "dQw4w9WgXcQ", f"Failed for: {url}"

    def test_extract_video_id_youtube_url(self):
        """Test extracting video ID from YouTube URL."""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in urls:
            video_id = PipedProvider.extract_video_id(url)
            assert video_id == "dQw4w9WgXcQ", f"Failed for: {url}"

    def test_extract_video_id_short_youtube_url(self):
        """Test extracting video ID from short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = PipedProvider.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_params(self):
        """Test extracting video ID from URL with parameters."""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://piped.video/watch?v=dQw4w9WgXcQ&list=PLxxx",
        ]

        for url in urls:
            video_id = PipedProvider.extract_video_id(url)
            assert video_id == "dQw4w9WgXcQ", f"Failed for: {url}"

    def test_extract_video_id_invalid_url(self):
        """Test extracting video ID from invalid URL."""
        url = "https://www.example.com/video"
        video_id = PipedProvider.extract_video_id(url)
        assert video_id is None

    def test_extract_video_id_empty_string(self):
        """Test extracting video ID from empty string."""
        video_id = PipedProvider.extract_video_id("")
        assert video_id is None

    def test_piped_url_pattern(self):
        """Test Piped URL regex pattern."""
        valid_urls = [
            "https://piped.video/watch?v=dQw4w9WgXcQ",
            "https://piped.kavin.rocks/watch?v=dQw4w9WgXcQ",
            "https://piped.silkky.cloud/watch?v=dQw4w9WgXcQ",
            "https://pipedapi.kavin.rocks/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            match = PIPED_URL_PATTERN.search(url)
            assert match is not None, f"Failed to match: {url}"
            assert match.group(1) == "dQw4w9WgXcQ"

    def test_piped_url_pattern_invalid(self):
        """Test Piped URL pattern with invalid URLs."""
        invalid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/123456",
            "not a url",
            "",
        ]

        for url in invalid_urls:
            match = PIPED_URL_PATTERN.search(url)
            assert match is None, f"Should not match: {url}"
