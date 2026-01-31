"""Tests for songs API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from spotdl.core.types.song import Platform, Song


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_song() -> Song:
    """Create a mock song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist 1", "Artist 2"],
        artist="Artist 1",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
        album_name="Test Album",
        year=2024,
        isrc="USABC1234567",
        explicit=True,
        cover_url="https://example.com/cover.jpg",
    )


class TestSongsEndpoints:
    """Tests for songs API endpoints."""

    async def test_get_platforms(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/platforms returns supported platforms."""
        response = await client.get("/api/v1/songs/platforms")

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "spotify" in data["platforms"]
        assert "youtube_music" in data["platforms"]
        assert "deezer" in data["platforms"]

    async def test_resolve_url_missing_param(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/resolve without URL returns 422."""
        response = await client.get("/api/v1/songs/resolve")
        assert response.status_code == 422

    async def test_resolve_url_unsupported(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/resolve with unsupported URL returns 400."""
        response = await client.get(
            "/api/v1/songs/resolve",
            params={"url": "https://example.com/track/123"},
        )
        assert response.status_code == 400

    async def test_search_missing_query(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/search without query returns 422."""
        response = await client.get("/api/v1/songs/search")
        assert response.status_code == 422

    async def test_search_invalid_platform(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/search with invalid platform returns 400."""
        response = await client.get(
            "/api/v1/songs/search",
            params={"query": "test", "platform": "invalid_platform"},
        )
        assert response.status_code == 400

    async def test_search_limit_validation(self, client: AsyncClient) -> None:
        """Test GET /api/v1/songs/search validates limit range."""
        # Too low
        response = await client.get(
            "/api/v1/songs/search",
            params={"query": "test", "limit": 0},
        )
        assert response.status_code == 422

        # Too high
        response = await client.get(
            "/api/v1/songs/search",
            params={"query": "test", "limit": 100},
        )
        assert response.status_code == 422


class TestSongsResolveWithMock:
    """Tests for songs resolve with mocked service."""

    async def test_resolve_url_success(
        self, client: AsyncClient, mock_song: Song
    ) -> None:
        """Test successful URL resolution."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[mock_song])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["songs"][0]["name"] == "Test Song"
            assert data["songs"][0]["artist"] == "Artist 1"
            assert data["songs"][0]["platform"] == "spotify"

    async def test_resolve_url_empty_result(self, client: AsyncClient) -> None:
        """Test URL resolution with no results."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["songs"] == []


class TestSongsSearchWithMock:
    """Tests for songs search with mocked service."""

    async def test_search_success(
        self, client: AsyncClient, mock_song: Song
    ) -> None:
        """Test successful search."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=[mock_song])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "test song", "platform": "spotify", "limit": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["songs"][0]["name"] == "Test Song"

    async def test_search_empty_result(self, client: AsyncClient) -> None:
        """Test search with no results."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "nonexistent song"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0


class TestSongsResolveErrors:
    """Tests for songs resolve error handling."""

    async def test_resolve_url_service_error(self, client: AsyncClient) -> None:
        """Test URL resolution when service throws an error."""
        from spotdl.core.services.song import SongServiceError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(
                side_effect=SongServiceError("Service error")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 500
            assert "Service error" in response.json()["detail"]


class TestSongsSearchErrors:
    """Tests for songs search error handling."""

    async def test_search_service_error(self, client: AsyncClient) -> None:
        """Test search when service throws an error."""
        from spotdl.core.services.song import SongServiceError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(
                side_effect=SongServiceError("Search failed")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "test", "platform": "spotify"},
            )

            assert response.status_code == 500
            assert "Search failed" in response.json()["detail"]

    async def test_search_unsupported_url_error(self, client: AsyncClient) -> None:
        """Test search when service throws UnsupportedURLError."""
        from spotdl.core.services.song import UnsupportedURLError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(
                side_effect=UnsupportedURLError("Unsupported")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "test", "platform": "spotify"},
            )

            assert response.status_code == 400
            assert "Unsupported" in response.json()["detail"]
