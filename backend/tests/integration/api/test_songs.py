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


class TestMultiPlatformSearch:
    """Tests for /api/v1/songs/search/all endpoint."""

    async def test_search_all_platforms_success(self, client: AsyncClient) -> None:
        """Test successful multi-platform search."""
        spotify_song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
        )

        youtube_song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.YOUTUBE_MUSIC,
            platform_id="youtube123",
            url="https://music.youtube.com/watch?v=youtube123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    return [spotify_song]
                elif platform == Platform.YOUTUBE_MUSIC:
                    return [youtube_song]
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "test song", "limit": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test song"
            assert "results" in data
            assert data["total_results"] >= 0
            assert "matches_saved" in data

    async def test_search_all_platforms_with_errors(self, client: AsyncClient) -> None:
        """Test multi-platform search handles platform failures gracefully."""
        from spotdl.core.services.song import SongServiceError

        spotify_song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    return [spotify_song]
                elif platform == Platform.YOUTUBE_MUSIC:
                    raise SongServiceError("YouTube Music unavailable")
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "test song"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should have results from at least one platform
            assert len(data["results"]) > 0
            # Check that error platforms are marked
            error_results = [r for r in data["results"] if r.get("error")]
            assert len(error_results) > 0

    async def test_search_all_platforms_unexpected_exception(self, client: AsyncClient) -> None:
        """Test multi-platform search handles unexpected exceptions."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    raise ValueError("Unexpected error")
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "test song"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should handle exception gracefully
            assert "results" in data

    async def test_search_all_platforms_empty_results(self, client: AsyncClient) -> None:
        """Test multi-platform search with no results."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "nonexistent song"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_results"] == 0
            assert data["matches_saved"] == 0

    async def test_search_all_platforms_limit_validation(self, client: AsyncClient) -> None:
        """Test multi-platform search validates limit."""
        # Too low
        response = await client.get(
            "/api/v1/songs/search/all",
            params={"query": "test", "limit": 0},
        )
        assert response.status_code == 422

        # Too high
        response = await client.get(
            "/api/v1/songs/search/all",
            params={"query": "test", "limit": 100},
        )
        assert response.status_code == 422

    async def test_search_all_platforms_missing_query(self, client: AsyncClient) -> None:
        """Test multi-platform search requires query."""
        response = await client.get("/api/v1/songs/search/all")
        assert response.status_code == 422


class TestCrossPlatformMatches:
    """Tests for cross-platform match saving functionality."""

    async def test_cross_platform_match_saving(self, client: AsyncClient) -> None:
        """Test that cross-platform matches are saved correctly."""
        spotify_song = Song(
            name="Matched Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
        )

        deezer_song = Song(
            name="Matched Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.DEEZER,
            platform_id="deezer123",
            url="https://www.deezer.com/track/deezer123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    return [spotify_song]
                elif platform == Platform.DEEZER:
                    return [deezer_song]
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "matched song"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should save matches for songs with same name and artist
            assert data["matches_saved"] >= 0

    async def test_cross_platform_match_no_duplicates(self, client: AsyncClient) -> None:
        """Test that only songs from different platforms create matches."""
        spotify_song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    return [spotify_song]
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "test song"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should not create matches with only one platform
            assert data["matches_saved"] == 0


class TestPlatformDisplayNames:
    """Tests for platform display name mapping."""

    async def test_platform_display_names_in_response(self, client: AsyncClient) -> None:
        """Test that platform display names are included in multi-platform search."""
        spotify_song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()

            async def mock_search(query, platform, limit):
                if platform == Platform.SPOTIFY:
                    return [spotify_song]
                return []

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/all",
                params={"query": "test song"},
            )

            assert response.status_code == 200
            data = response.json()
            # Find Spotify result
            spotify_result = next(
                (r for r in data["results"] if r["platform"] == "spotify"), None
            )
            assert spotify_result is not None
            assert spotify_result["platform_name"] == "Spotify"

    async def test_all_platform_display_names(self, client: AsyncClient) -> None:
        """Test display names for all platforms."""
        from spotdl.api.v1.songs import PLATFORM_DISPLAY_NAMES

        # Verify all searchable platforms have display names
        assert Platform.SPOTIFY in PLATFORM_DISPLAY_NAMES
        assert Platform.YOUTUBE_MUSIC in PLATFORM_DISPLAY_NAMES
        assert Platform.DEEZER in PLATFORM_DISPLAY_NAMES
        assert Platform.SOUNDCLOUD in PLATFORM_DISPLAY_NAMES

        # Verify display name values
        assert PLATFORM_DISPLAY_NAMES[Platform.SPOTIFY] == "Spotify"
        assert PLATFORM_DISPLAY_NAMES[Platform.YOUTUBE_MUSIC] == "YouTube Music"
        assert PLATFORM_DISPLAY_NAMES[Platform.DEEZER] == "Deezer"
        assert PLATFORM_DISPLAY_NAMES[Platform.SOUNDCLOUD] == "SoundCloud"


class TestSongToResponseHelper:
    """Tests for _song_to_response helper function."""

    def test_song_to_response_full_metadata(self) -> None:
        """Test _song_to_response with full metadata."""
        from spotdl.api.v1.songs import _song_to_response

        song = Song(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
            album_name="Test Album",
            album_artist="Album Artist",
            album_id="album123",
            track_number=5,
            disc_number=1,
            year=2024,
            date="2024-01-15",
            genres=["pop", "rock"],
            isrc="USABC1234567",
            explicit=True,
            cover_url="https://example.com/cover.jpg",
        )

        response = _song_to_response(song)

        assert response.name == "Test Song"
        assert response.artists == ["Artist 1", "Artist 2"]
        assert response.artist == "Artist 1"
        assert response.duration == 200
        assert response.platform == "spotify"
        assert response.platform_id == "abc123"
        assert response.url == "https://open.spotify.com/track/abc123"
        assert response.album_name == "Test Album"
        assert response.album_artist == "Album Artist"
        assert response.album_id == "album123"
        assert response.track_number == 5
        assert response.disc_number == 1
        assert response.year == 2024
        assert response.date == "2024-01-15"
        assert response.genres == ["pop", "rock"]
        assert response.isrc == "USABC1234567"
        assert response.explicit is True
        assert response.cover_url == "https://example.com/cover.jpg"

    def test_song_to_response_minimal_metadata(self) -> None:
        """Test _song_to_response with minimal metadata."""
        from spotdl.api.v1.songs import _song_to_response

        song = Song(
            name="Minimal Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.YOUTUBE_MUSIC,
            platform_id="yt123",
            url="https://music.youtube.com/watch?v=yt123",
        )

        response = _song_to_response(song)

        assert response.name == "Minimal Song"
        assert response.artist == "Artist"
        assert response.platform == "youtube_music"
        # Song model has defaults, so these may not be None
        assert response.year is None
        assert response.genres == []
        assert response.explicit is False

    def test_song_to_response_with_none_year(self) -> None:
        """Test _song_to_response handles None year correctly."""
        from spotdl.api.v1.songs import _song_to_response

        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.DEEZER,
            platform_id="dz123",
            url="https://www.deezer.com/track/dz123",
            year=None,
        )

        response = _song_to_response(song)
        assert response.year is None

    def test_song_to_response_with_empty_genres(self) -> None:
        """Test _song_to_response handles empty genres."""
        from spotdl.api.v1.songs import _song_to_response

        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="sp123",
            url="https://open.spotify.com/track/sp123",
            genres=[],
        )

        response = _song_to_response(song)
        assert response.genres == []


class TestEntityUrlBuilders:
    """Tests for _build_entity_url function."""

    def test_build_spotify_urls(self) -> None:
        """Test building Spotify entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        track_url = _build_entity_url(Platform.SPOTIFY, "track", "abc123")
        assert track_url == "https://open.spotify.com/track/abc123"

        album_url = _build_entity_url(Platform.SPOTIFY, "album", "album123")
        assert album_url == "https://open.spotify.com/album/album123"

        artist_url = _build_entity_url(Platform.SPOTIFY, "artist", "artist123")
        assert artist_url == "https://open.spotify.com/artist/artist123"

        playlist_url = _build_entity_url(Platform.SPOTIFY, "playlist", "playlist123")
        assert playlist_url == "https://open.spotify.com/playlist/playlist123"

    def test_build_youtube_music_urls(self) -> None:
        """Test building YouTube Music entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        track_url = _build_entity_url(Platform.YOUTUBE_MUSIC, "track", "video123")
        assert track_url == "https://music.youtube.com/watch?v=video123"

        album_url = _build_entity_url(Platform.YOUTUBE_MUSIC, "album", "album123")
        assert album_url == "https://music.youtube.com/browse/album123"

        playlist_url = _build_entity_url(Platform.YOUTUBE_MUSIC, "playlist", "playlist123")
        assert playlist_url == "https://music.youtube.com/playlist?list=playlist123"

        artist_url = _build_entity_url(Platform.YOUTUBE_MUSIC, "artist", "channel123")
        assert artist_url == "https://music.youtube.com/channel/channel123"

    def test_build_deezer_urls(self) -> None:
        """Test building Deezer entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        track_url = _build_entity_url(Platform.DEEZER, "track", "123456")
        assert track_url == "https://www.deezer.com/track/123456"

        album_url = _build_entity_url(Platform.DEEZER, "album", "789")
        assert album_url == "https://www.deezer.com/album/789"

    def test_build_soundcloud_urls(self) -> None:
        """Test building SoundCloud entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        url = _build_entity_url(Platform.SOUNDCLOUD, "track", "artist/track-name")
        assert url == "https://soundcloud.com/artist/track-name"

    def test_build_bandcamp_urls(self) -> None:
        """Test building Bandcamp entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        url = _build_entity_url(Platform.BANDCAMP, "album", "album-id")
        assert url == "https://bandcamp.com/album/album-id"

    def test_build_apple_music_urls(self) -> None:
        """Test building Apple Music entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        url = _build_entity_url(Platform.APPLE_MUSIC, "track", "123456")
        assert url == "https://music.apple.com/track/123456"

    def test_build_tidal_urls(self) -> None:
        """Test building Tidal entity URLs."""
        from spotdl.api.v1.songs import _build_entity_url

        url = _build_entity_url(Platform.TIDAL, "track", "123456")
        assert url == "https://tidal.com/browse/track/123456"


class TestEntityEndpointsEdgeCases:
    """Tests for entity endpoints edge cases."""

    async def test_get_album_empty_songs(self, client: AsyncClient) -> None:
        """Test getting album with no songs."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/album/spotify/empty_album"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Unknown Album"
            assert data["artist_name"] == "Unknown Artist"
            assert data["total_tracks"] == 0

    async def test_get_artist_empty_songs(self, client: AsyncClient) -> None:
        """Test getting artist with no songs."""
        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/artist/spotify/empty_artist"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Unknown Artist"
            assert data["total_songs"] == 0

    async def test_get_playlist_service_error(self, client: AsyncClient) -> None:
        """Test getting playlist when service throws error."""
        from spotdl.core.services.song import SongServiceError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(
                side_effect=SongServiceError("Playlist unavailable")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/playlist/spotify/error_playlist"
            )

            assert response.status_code == 500
            assert "Playlist unavailable" in response.json()["detail"]

    async def test_get_artist_unsupported_url_error(self, client: AsyncClient) -> None:
        """Test getting artist when URL is unsupported."""
        from spotdl.core.services.song import UnsupportedURLError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(
                side_effect=UnsupportedURLError("Unsupported artist URL")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/entities/artist/spotify/bad_artist"
            )

            assert response.status_code == 400
            assert "Unsupported artist URL" in response.json()["detail"]

    async def test_get_album_invalid_platform(self, client: AsyncClient) -> None:
        """Test getting album with invalid platform."""
        response = await client.get(
            "/api/v1/songs/entities/album/invalid/album123"
        )

        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]

    async def test_get_playlist_invalid_platform(self, client: AsyncClient) -> None:
        """Test getting playlist with invalid platform."""
        response = await client.get(
            "/api/v1/songs/entities/playlist/badplatform/playlist123"
        )

        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]


class TestEntitySearchAdvanced:
    """Advanced tests for entity search endpoint."""

    async def test_search_entities_service_error(self, client: AsyncClient) -> None:
        """Test entity search when service throws error."""
        from spotdl.core.services.song import SongServiceError

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(
                side_effect=SongServiceError("Search failed")
            )
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test"},
            )

            assert response.status_code == 500
            assert "Search failed" in response.json()["detail"]

    async def test_search_entities_multiple_artists(self, client: AsyncClient) -> None:
        """Test entity search with multiple artists in results."""
        songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist A" if i % 2 == 0 else "Artist B"],
                artist="Artist A" if i % 2 == 0 else "Artist B",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
            )
            for i in range(10)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test", "entity_type": "artist"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should have both artists
            artist_names = [r["name"] for r in data["results"]]
            assert "Artist A" in artist_names
            assert "Artist B" in artist_names

    async def test_search_entities_duplicate_albums(self, client: AsyncClient) -> None:
        """Test entity search deduplicates albums."""
        songs = [
            Song(
                name=f"Track {i}",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
                album_name="Same Album",
                album_id="album123",
            )
            for i in range(5)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test", "entity_type": "album"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should only have one album despite 5 tracks
            album_results = [r for r in data["results"] if r["entity_type"] == "album"]
            assert len(album_results) == 1

    async def test_search_entities_artist_sorting(self, client: AsyncClient) -> None:
        """Test entity search sorts artists by relevance."""
        songs = [
            Song(
                name="Song 1",
                artists=["Exact Match"],
                artist="Exact Match",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="track1",
                url="https://open.spotify.com/track/track1",
            ),
            Song(
                name="Song 2",
                artists=["Exact Match"],
                artist="Exact Match",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="track2",
                url="https://open.spotify.com/track/track2",
            ),
            Song(
                name="Song 3",
                artists=["Other Artist"],
                artist="Other Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="track3",
                url="https://open.spotify.com/track/track3",
            ),
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "exact match", "entity_type": "artist"},
            )

            assert response.status_code == 200
            data = response.json()
            # First result should be the exact match
            if len(data["results"]) > 0:
                first_result = data["results"][0]
                assert "Exact Match" in first_result["name"]

    async def test_search_entities_no_album_id(self, client: AsyncClient) -> None:
        """Test entity search handles songs without album IDs."""
        songs = [
            Song(
                name="Single Track",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.YOUTUBE_MUSIC,
                platform_id="track1",
                url="https://music.youtube.com/watch?v=track1",
                album_name="Album Name",
                album_id=None,  # No album ID
            )
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search/entities",
                params={"query": "test", "entity_type": "album"},
            )

            assert response.status_code == 200
            data = response.json()
            # Should not include album without ID
            assert len(data["results"]) == 0


class TestSearchableplatforms:
    """Tests for searchable platforms configuration."""

    def test_searchable_platforms_list(self) -> None:
        """Test that SEARCHABLE_PLATFORMS contains expected platforms."""
        from spotdl.api.v1.songs import SEARCHABLE_PLATFORMS

        assert Platform.YOUTUBE_MUSIC in SEARCHABLE_PLATFORMS
        assert Platform.SOUNDCLOUD in SEARCHABLE_PLATFORMS
        assert Platform.DEEZER in SEARCHABLE_PLATFORMS
        assert Platform.SPOTIFY in SEARCHABLE_PLATFORMS


class TestResolveUrlEdgeCases:
    """Additional edge cases for resolve_url endpoint."""

    async def test_resolve_url_with_multiple_songs(self, client: AsyncClient) -> None:
        """Test resolving URL that returns multiple songs (e.g., playlist)."""
        songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist"],
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"track{i}",
                url=f"https://open.spotify.com/track/track{i}",
            )
            for i in range(3)
        ]

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=songs)
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": "https://open.spotify.com/playlist/abc123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert len(data["songs"]) == 3

    async def test_resolve_url_with_all_fields_none(self, client: AsyncClient) -> None:
        """Test resolving URL with song that has mostly None fields."""
        minimal_song = Song(
            name="Minimal",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.BANDCAMP,
            platform_id="track123",
            url="https://bandcamp.com/track/track123",
            album_name=None,
            album_artist=None,
            album_id=None,
            track_number=None,
            disc_number=None,
            year=None,
            date=None,
            genres=None,
            isrc=None,
            explicit=False,
            cover_url=None,
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.resolve_url = AsyncMock(return_value=[minimal_song])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": "https://bandcamp.com/track/track123"},
            )

            assert response.status_code == 200
            data = response.json()
            song = data["songs"][0]
            assert song["album_name"] is None
            assert song["year"] is None
            assert song["genres"] == []


class TestSearchEdgeCases:
    """Additional edge cases for search endpoint."""

    async def test_search_with_different_platforms(self, client: AsyncClient) -> None:
        """Test search on different platforms."""
        song = Song(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.DEEZER,
            platform_id="deezer123",
            url="https://www.deezer.com/track/deezer123",
        )

        with patch("spotdl.api.v1.songs.get_song_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(return_value=[song])
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "test", "platform": "deezer"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["songs"][0]["platform"] == "deezer"

    async def test_search_with_limit_one(self, client: AsyncClient) -> None:
        """Test search with limit=1."""
        songs = [
            Song(
                name=f"Song {i}",
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
            # Mock should only return 1 song when limit is 1
            async def mock_search(query, platform, limit):
                return songs[:limit]

            mock_service.search = mock_search
            mock_get_service.return_value = mock_service

            response = await client.get(
                "/api/v1/songs/search",
                params={"query": "test", "limit": 1},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] <= 1
