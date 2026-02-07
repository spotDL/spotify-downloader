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


class TestSongsEntities:
    """Tests for songs entity endpoints."""

    async def test_get_track(self, client: AsyncClient, mock_song: Song) -> None:
        """Test getting track details."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[mock_song])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/track/spotify/abc123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Song"
            assert data["platform"] == "spotify"
            assert data["platform_id"] == "abc123"

    async def test_get_track_not_found(self, client: AsyncClient) -> None:
        """Test getting non-existent track returns 404."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/track/spotify/notfound"
            )

            assert response.status_code == 404

    async def test_get_track_invalid_platform(self, client: AsyncClient) -> None:
        """Test getting track with invalid platform returns 400."""
        response = await client.get(
            "/api/v1/songs/entities/track/invalid_platform/abc123"
        )

        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]

    async def test_get_album(self, client: AsyncClient) -> None:
        """Test getting album details."""
        album_songs = [
            Song(
                name=f"Track {i}",
                artists=["Album Artist"],
                artist="Album Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
                album_name="Test Album",
                album_id="album123",
                track_number=i,
            )
            for i in range(1, 11)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=album_songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/album/spotify/album123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Album"
            assert data["artist_name"] == "Album Artist"
            assert data["total_tracks"] == 10
            assert len(data["songs"]) == 10

    async def test_get_playlist(self, client: AsyncClient, mock_song: Song) -> None:
        """Test getting playlist details."""
        playlist_songs = [mock_song] * 5

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=playlist_songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/playlist/spotify/playlist123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_tracks"] == 5
            assert len(data["songs"]) == 5
            assert data["platform"] == "spotify"

    async def test_get_artist(self, client: AsyncClient) -> None:
        """Test getting artist details."""
        artist_songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist Name"],
                artist="Artist Name",
                duration=200 + i * 10,
                platform=Platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://open.spotify.com/track/song{i}",
            )
            for i in range(20)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=artist_songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/artist/spotify/artist123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Artist Name"
            assert data["total_songs"] == 20
            assert len(data["songs"]) == 20


class TestSongsSearchEntities:
    """Tests for /api/v1/songs/search/entities endpoint."""

    async def test_search_entities_all_types(self, client: AsyncClient) -> None:
        """Test searching entities without type filter."""
        search_results = [
            Song(
                name="Test Song",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="track1",
                url="https://open.spotify.com/track/track1",
                album_name="Test Album",
                album_id="album1",
            )
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=search_results)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert data["query"] == "test"

    async def test_search_entities_tracks_only(self, client: AsyncClient) -> None:
        """Test searching for tracks only."""
        track_results = [
            Song(
                name=f"Track {i}",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
            )
            for i in range(5)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=track_results)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test", "entity_type": "track"},
            )

            assert response.status_code == 200
            data = response.json()
            # All results should be tracks
            for result in data["results"]:
                assert result["entity_type"] == "track"

    async def test_search_entities_albums_only(self, client: AsyncClient) -> None:
        """Test searching for albums only."""
        album_tracks = [
            Song(
                name=f"Track {i}",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
                album_name="Album Name",
                album_id="album1",
            )
            for i in range(3)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=album_tracks)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "album", "entity_type": "album"},
            )

            assert response.status_code == 200
            data = response.json()
            # All results should be albums
            for result in data["results"]:
                assert result["entity_type"] == "album"

    async def test_search_entities_artists_only(self, client: AsyncClient) -> None:
        """Test searching for artists only."""
        artist_tracks = [
            Song(
                name=f"Song {i}",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://open.spotify.com/track/song{i}",
            )
            for i in range(5)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=artist_tracks)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "artist", "entity_type": "artist"},
            )

            assert response.status_code == 200
            data = response.json()
            # All results should be artists
            for result in data["results"]:
                assert result["entity_type"] == "artist"

    async def test_search_entities_invalid_platform(self, client: AsyncClient) -> None:
        """Test searching entities with invalid platform."""
        response = await client.get(
            "/api/v1/songs/search/entities",
            params={"query": "test", "platform": "invalid_platform"},
        )

        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]

    async def test_search_entities_with_limit(self, client: AsyncClient) -> None:
        """Test searching entities with custom limit."""
        many_tracks = [
            Song(
                name=f"Track {i}",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
            )
            for i in range(50)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=many_tracks)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test", "limit": 20},
            )

            assert response.status_code == 200
            data = response.json()
            # Should be limited to 20
            assert len(data["results"]) <= 20
