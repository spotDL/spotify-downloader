"""Tests for universal search API endpoint."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from spotdl.api.v1.search import is_url
from spotdl.core.types.song import Song, Platform


pytestmark = pytest.mark.asyncio


class TestIsUrl:
    """Tests for is_url helper function."""

    def test_is_url_http(self) -> None:
        """Test detection of http URLs."""
        assert is_url("http://example.com") is True
        assert is_url("https://example.com") is True

    def test_is_url_spotify(self) -> None:
        """Test detection of Spotify URLs."""
        assert is_url("spotify:track:123") is True
        assert is_url("open.spotify.com/track/123") is True
        assert is_url("https://open.spotify.com/track/123") is True

    def test_is_url_youtube(self) -> None:
        """Test detection of YouTube URLs."""
        assert is_url("youtube.com/watch?v=123") is True
        assert is_url("youtu.be/123") is True
        assert is_url("music.youtube.com/watch?v=123") is True

    def test_is_url_other_platforms(self) -> None:
        """Test detection of other platform URLs."""
        assert is_url("deezer.com/track/123") is True
        assert is_url("music.apple.com/us/album/123") is True
        assert is_url("tidal.com/track/123") is True
        assert is_url("soundcloud.com/artist/track") is True
        assert is_url("bandcamp.com/track/name") is True

    def test_is_not_url(self) -> None:
        """Test detection of non-URL text."""
        assert is_url("test search query") is False
        assert is_url("artist name") is False
        assert is_url("song title") is False
        assert is_url("") is False


class TestSearchGet:
    """Tests for GET /api/v1/search endpoint."""

    async def test_search_get_empty_query(self, authenticated_client: AsyncClient) -> None:
        """Test GET search with empty query returns 400."""
        response = await authenticated_client.get(
            "/api/v1/search",
            params={"q": ""},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    async def test_search_get_missing_query(self, authenticated_client: AsyncClient) -> None:
        """Test GET search without query parameter returns 422."""
        response = await authenticated_client.get("/api/v1/search")

        assert response.status_code == 422

    async def test_search_get_with_limit(self, authenticated_client: AsyncClient) -> None:
        """Test GET search with custom limit."""
        mock_song = Song(
            name="Test Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
            genres=(),
        )

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                # Setup mocks
                mock_svc = MagicMock()
                mock_svc.search = AsyncMock(return_value=[mock_song])
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                mock_persist.song_ids = {f"{mock_song.platform.value}:{mock_song.platform_id}": "uuid-123"}
                mock_persist.artist_ids = {}
                mock_persist.album_ids = {}
                mock_persist.total_created = 1
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity.return_value = mock_entity_inst

                response = await authenticated_client.get(
                    "/api/v1/search",
                    params={"q": "test query", "limit": 5},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["query"] == "test query"
                assert data["query_type"] == "text"

    async def test_search_get_with_entity_type_filter(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test GET search with entity type filter."""
        mock_song = Song(
            name="Test Track",
            artists=("Test Artist",),
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="track1",
            url="https://open.spotify.com/track/track1",
            genres=(),
        )

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                mock_svc = MagicMock()
                mock_svc.search = AsyncMock(return_value=[mock_song])
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                mock_persist.song_ids = {f"{mock_song.platform.value}:{mock_song.platform_id}": "uuid-track"}
                mock_persist.artist_ids = {"test artist": "uuid-artist"}
                mock_persist.album_ids = {}
                mock_persist.total_created = 1
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                mock_entity.return_value = mock_entity_inst
                mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                response = await authenticated_client.get(
                    "/api/v1/search",
                    params={"q": "test", "type": "track"},
                )

                assert response.status_code == 200
                data = response.json()
                # Should only include track results when filtered
                assert all(r["entity_type"] == "track" for r in data["results"])


class TestSearchPost:
    """Tests for POST /api/v1/search endpoint."""

    async def test_search_post_text_query(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test POST search with text query."""
        mock_songs = [
            Song(
                name=f"Song {i}",
                artists=("Artist",),
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://open.spotify.com/track/song{i}",
                genres=(),
            )
            for i in range(3)
        ]

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                mock_svc = MagicMock()
                mock_svc.search = AsyncMock(return_value=mock_songs)
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                mock_persist.song_ids = {
                    f"{s.platform.value}:{s.platform_id}": f"uuid-{i}"
                    for i, s in enumerate(mock_songs)
                }
                mock_persist.artist_ids = {"artist": "uuid-artist"}
                mock_persist.album_ids = {}
                mock_persist.total_created = 4
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                mock_entity.return_value = mock_entity_inst
                mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                response = await authenticated_client.post(
                    "/api/v1/search",
                    json={"query": "test search"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["query"] == "test search"
                assert data["query_type"] == "text"
                assert data["total"] > 0

    async def test_search_post_with_entity_types(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test POST search with entity type filters."""
        mock_song = Song(
            name="Album Track",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="track1",
            url="https://open.spotify.com/track/track1",
            album_name="Test Album",
            album_id="album1",
            genres=(),
        )

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                mock_svc = MagicMock()
                mock_svc.search = AsyncMock(return_value=[mock_song])
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                mock_persist.song_ids = {f"{mock_song.platform.value}:{mock_song.platform_id}": "uuid-song"}
                mock_persist.artist_ids = {"artist": "uuid-artist"}
                mock_persist.album_ids = {"artist:test album": "uuid-album"}
                mock_persist.total_created = 3
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                mock_entity.return_value = mock_entity_inst
                mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                response = await authenticated_client.post(
                    "/api/v1/search",
                    json={
                        "query": "test",
                        "entity_types": ["album"],
                    },
                )

                assert response.status_code == 200
                data = response.json()
                # Should only have album results
                assert all(r["entity_type"] == "album" for r in data["results"])

    async def test_search_post_empty_query(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test POST search with empty query returns 400."""
        response = await authenticated_client.post(
            "/api/v1/search",
            json={"query": "  "},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


class TestSearchUrl:
    """Tests for URL search functionality."""

    async def test_search_url_detection(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test that URLs are properly detected and routed."""
        mock_song = Song(
            name="Track Name",
            artists=("Artist",),
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
            genres=(),
        )

        with patch("spotdl.api.v1.search.detect_platform") as mock_detect:
            with patch("spotdl.api.v1.search.get_song_service") as mock_service:
                with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                    mock_detect.return_value = Platform.SPOTIFY

                    mock_svc = MagicMock()
                    mock_svc.resolve_url = AsyncMock(return_value=[mock_song])
                    mock_service.return_value = mock_svc

                    mock_persist = MagicMock()
                    mock_persist.song_ids = {f"{mock_song.platform.value}:{mock_song.platform_id}": "uuid-123"}
                    mock_persist.artist_ids = {"artist": "uuid-artist"}
                    mock_persist.album_ids = {}
                    mock_persist.total_created = 2
                    mock_entity_inst = AsyncMock()
                    mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                    mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                    mock_entity.return_value = mock_entity_inst
                    mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                    response = await authenticated_client.get(
                        "/api/v1/search",
                        params={"q": "https://open.spotify.com/track/abc123"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["query_type"] == "url"
                    assert data["total"] > 0

    async def test_search_unsupported_url(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test search with unsupported URL."""
        with patch("spotdl.api.v1.search.detect_platform") as mock_detect:
            mock_detect.return_value = None

            response = await authenticated_client.get(
                "/api/v1/search",
                params={"q": "https://unsupported.com/track/123"},
            )

            assert response.status_code == 400
            assert "Unsupported URL" in response.json()["detail"]

    async def test_search_url_no_results(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test URL search that returns no results."""
        with patch("spotdl.api.v1.search.detect_platform") as mock_detect:
            with patch("spotdl.api.v1.search.get_song_service") as mock_service:
                with patch("spotdl.api.v1.search.EntityPersistenceService"):
                    mock_detect.return_value = Platform.SPOTIFY

                    mock_svc = MagicMock()
                    mock_svc.resolve_url = AsyncMock(return_value=[])
                    mock_service.return_value = mock_svc

                    response = await authenticated_client.get(
                        "/api/v1/search",
                        params={"q": "https://open.spotify.com/track/notfound"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == 0
                    assert data["results"] == []


class TestSearchDeduplication:
    """Tests for search result deduplication."""

    async def test_search_deduplicates_by_isrc(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test that search deduplicates songs with same ISRC."""
        # Two songs with same ISRC from different platforms
        song1 = Song(
            name="Same Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="spotify123",
            url="https://open.spotify.com/track/spotify123",
            isrc="USABC1234567",
            genres=(),
        )

        song2 = Song(
            name="Same Song",
            artists=("Artist",),
            artist="Artist",
            duration=180,
            platform=Platform.YOUTUBE_MUSIC,
            platform_id="yt123",
            url="https://music.youtube.com/watch?v=yt123",
            isrc="USABC1234567",
            genres=(),
        )

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                mock_svc = MagicMock()
                # Return both songs from the search
                mock_svc.search = AsyncMock(side_effect=[[song1], [song2], [], []])
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                # Only one song should be persisted
                mock_persist.song_ids = {f"{song1.platform.value}:{song1.platform_id}": "uuid-1"}
                mock_persist.artist_ids = {"artist": "uuid-artist"}
                mock_persist.album_ids = {}
                mock_persist.total_created = 1
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                mock_entity.return_value = mock_entity_inst
                mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                response = await authenticated_client.get(
                    "/api/v1/search",
                    params={"q": "same song"},
                )

                assert response.status_code == 200
                data = response.json()
                # Should only have one track result (deduplicated)
                track_results = [r for r in data["results"] if r["entity_type"] == "track"]
                assert len(track_results) == 1

    async def test_search_deduplicates_artists(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test that search deduplicates artists."""
        # Multiple songs from same artist
        songs = [
            Song(
                name=f"Song {i}",
                artists=("Same Artist",),
                artist="Same Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id=f"song{i}",
                url=f"https://open.spotify.com/track/song{i}",
                genres=(),
            )
            for i in range(3)
        ]

        with patch("spotdl.api.v1.search.get_song_service") as mock_service:
            with patch("spotdl.api.v1.search.EntityPersistenceService") as mock_entity:
                mock_svc = MagicMock()
                mock_svc.search = AsyncMock(return_value=songs)
                mock_service.return_value = mock_svc

                mock_persist = MagicMock()
                mock_persist.song_ids = {f"{s.platform.value}:{s.platform_id}": f"uuid-{i}" for i, s in enumerate(songs)}
                mock_persist.artist_ids = {"same artist": "uuid-artist"}
                mock_persist.album_ids = {}
                mock_persist.total_created = 4
                mock_entity_inst = AsyncMock()
                mock_entity_inst.persist_from_search = AsyncMock(return_value=mock_persist)
                mock_entity_inst.normalize_name = MagicMock(side_effect=lambda x: x.lower())
                mock_entity.return_value = mock_entity_inst
                mock_entity.normalize_name = MagicMock(side_effect=lambda x: x.lower())

                response = await authenticated_client.get(
                    "/api/v1/search",
                    params={"q": "same artist"},
                )

                assert response.status_code == 200
                data = response.json()
                # Should only have one artist result
                artist_results = [r for r in data["results"] if r["entity_type"] == "artist"]
                assert len(artist_results) == 1
                assert artist_results[0]["name"] == "Same Artist"
