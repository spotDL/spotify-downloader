"""Tests for API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from spotdl_cli.config import Settings
from spotdl_cli.core.api_client import (
    APIClient,
    APIError,
    ConnectionError,
    NotFoundError,
)
from spotdl_cli.core.types import Platform, TargetPlatform


class TestAPIClient:
    """Tests for APIClient class."""

    @pytest.fixture
    def client(self, settings: Settings) -> APIClient:
        """Create test API client."""
        return APIClient(settings)

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: APIClient) -> None:
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: APIClient) -> None:
        """Test failed health check."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_get.return_value = mock_http

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_online_offline_mode(self, settings: Settings) -> None:
        """Test is_online returns False in offline mode."""
        settings.offline_mode = True
        client = APIClient(settings)

        result = await client.is_online()
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_url_success(self, client: APIClient) -> None:
        """Test successful URL resolution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "songs": [
                {
                    "name": "Test Song",
                    "artists": ["Artist1"],
                    "artist": "Artist1",
                    "duration": 180,
                    "platform": "spotify",
                    "platform_id": "test123",
                    "url": "https://spotify.com/track/test123",
                }
            ]
        }

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            songs = await client.resolve_url("https://spotify.com/track/test123")

            assert len(songs) == 1
            assert songs[0].name == "Test Song"
            assert songs[0].platform == Platform.SPOTIFY

    @pytest.mark.asyncio
    async def test_resolve_url_not_found(self, client: APIClient) -> None:
        """Test URL resolution with not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.resolve_url("https://invalid.url/xyz")

    @pytest.mark.asyncio
    async def test_resolve_url_connection_error(self, client: APIClient) -> None:
        """Test URL resolution with connection error."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("Failed"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError):
                await client.resolve_url("https://spotify.com/track/test")

    @pytest.mark.asyncio
    async def test_search_success(self, client: APIClient) -> None:
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "songs": [
                {
                    "name": "Found Song",
                    "artists": ["Artist"],
                    "artist": "Artist",
                    "duration": 200,
                    "platform": "spotify",
                    "platform_id": "found123",
                    "url": "https://spotify.com/track/found123",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            songs = await client.search("test query")

            assert len(songs) == 1
            assert songs[0].name == "Found Song"

    @pytest.mark.asyncio
    async def test_find_matches_success(
        self, client: APIClient, sample_song
    ) -> None:
        """Test successful match finding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {
                    "name": "Test Song",
                    "artists": ["Artist"],
                    "artist": "Artist",
                    "duration": 182,
                    "target_platform": "youtube",
                    "platform_id": "abc123",
                    "url": "https://youtube.com/watch?v=abc123",
                    "verified": True,
                    "score": 95.0,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.find_matches(sample_song)

            assert len(matches) == 1
            assert matches[0].platform == TargetPlatform.YOUTUBE
            assert matches[0].verified is True
            assert matches[0].score == 95.0

    @pytest.mark.asyncio
    async def test_find_matches_no_results(
        self, client: APIClient, sample_song
    ) -> None:
        """Test match finding with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.find_matches(sample_song)
            assert matches == []

    @pytest.mark.asyncio
    async def test_close(self, client: APIClient) -> None:
        """Test closing the client."""
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._client is None
