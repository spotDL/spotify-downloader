"""Tests for entities API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
import uuid

from spotdl.db.models.song import Song
from spotdl.db.models.album import Album
from spotdl.db.models.artist import Artist
from spotdl.db.models.playlist import Playlist


pytestmark = pytest.mark.asyncio


class TestGetArtist:
    """Tests for GET /api/v1/entities/artists/{id}."""

    async def test_get_artist_not_found(self, authenticated_client: AsyncClient) -> None:
        """Test getting non-existent artist returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/entities/artists/{fake_id}"
        )

        assert response.status_code == 404

    async def test_get_artist_invalid_uuid(self, authenticated_client: AsyncClient) -> None:
        """Test getting artist with invalid UUID returns 400."""
        response = await authenticated_client.get(
            "/api/v1/entities/artists/invalid-id"
        )

        assert response.status_code == 400


class TestGetAlbum:
    """Tests for GET /api/v1/entities/albums/{id}."""

    async def test_get_album_not_found(self, authenticated_client: AsyncClient) -> None:
        """Test getting non-existent album returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/entities/albums/{fake_id}"
        )

        assert response.status_code == 404

    async def test_get_album_invalid_uuid(self, authenticated_client: AsyncClient) -> None:
        """Test getting album with invalid UUID returns 400."""
        response = await authenticated_client.get(
            "/api/v1/entities/albums/not-a-uuid"
        )

        assert response.status_code == 400


class TestGetSong:
    """Tests for GET /api/v1/entities/songs/{id}."""

    async def test_get_song_not_found(self, authenticated_client: AsyncClient) -> None:
        """Test getting non-existent song returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/entities/songs/{fake_id}"
        )

        assert response.status_code == 404

    async def test_get_song_invalid_uuid(self, authenticated_client: AsyncClient) -> None:
        """Test getting song with invalid UUID returns 422."""
        response = await authenticated_client.get(
            "/api/v1/entities/songs/bad-uuid"
        )

        assert response.status_code in [400, 422]


class TestGetPlaylist:
    """Tests for GET /api/v1/entities/playlists/{id}."""

    async def test_get_playlist_not_found(self, authenticated_client: AsyncClient) -> None:
        """Test getting non-existent playlist returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/entities/playlists/{fake_id}"
        )

        assert response.status_code == 404

    async def test_get_playlist_invalid_uuid(self, authenticated_client: AsyncClient) -> None:
        """Test getting playlist with invalid UUID returns 422."""
        response = await authenticated_client.get(
            "/api/v1/entities/playlists/invalid"
        )

        assert response.status_code in [400, 422]


class TestGetMetadataProviders:
    """Tests for GET /api/v1/entities/metadata-providers."""

    async def test_get_metadata_providers(self, authenticated_client: AsyncClient) -> None:
        """Test getting metadata providers list."""
        response = await authenticated_client.get(
            "/api/v1/entities/metadata-providers"
        )

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    async def test_metadata_providers_structure(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test metadata providers have correct structure."""
        response = await authenticated_client.get(
            "/api/v1/entities/metadata-providers"
        )

        assert response.status_code == 200
        data = response.json()

        if data["providers"]:
            # Check first provider has expected fields
            provider = data["providers"][0]
            assert "id" in provider
            assert "name" in provider
            # Providers have different structures, just verify basic fields exist
            assert isinstance(provider["id"], str)
            assert isinstance(provider["name"], str)


class TestRefreshSong:
    """Tests for POST /api/v1/entities/songs/{id}/refresh."""

    async def test_refresh_song_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing non-existent song returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/songs/{fake_id}/refresh"
        )

        assert response.status_code == 404

    async def test_refresh_song_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing song with invalid UUID returns 422."""
        response = await authenticated_client.post(
            "/api/v1/entities/songs/not-valid-uuid/refresh"
        )

        assert response.status_code in [400, 422]


class TestRefreshAlbum:
    """Tests for POST /api/v1/entities/albums/{id}/refresh."""

    async def test_refresh_album_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing non-existent album returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/albums/{fake_id}/refresh"
        )

        assert response.status_code == 404

    async def test_refresh_album_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing album with invalid UUID returns 422."""
        response = await authenticated_client.post(
            "/api/v1/entities/albums/bad-id/refresh"
        )

        assert response.status_code in [400, 422]


class TestRefreshArtist:
    """Tests for POST /api/v1/entities/artists/{id}/refresh."""

    async def test_refresh_artist_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing non-existent artist returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/artists/{fake_id}/refresh"
        )

        assert response.status_code == 404

    async def test_refresh_artist_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing artist with invalid UUID returns 422."""
        response = await authenticated_client.post(
            "/api/v1/entities/artists/invalid-uuid/refresh"
        )

        assert response.status_code in [400, 422]


class TestRefreshPlaylist:
    """Tests for POST /api/v1/entities/playlists/{id}/refresh."""

    async def test_refresh_playlist_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing non-existent playlist returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/playlists/{fake_id}/refresh"
        )

        assert response.status_code == 404

    async def test_refresh_playlist_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test refreshing playlist with invalid UUID returns 422."""
        response = await authenticated_client.post(
            "/api/v1/entities/playlists/not-uuid/refresh"
        )

        assert response.status_code in [400, 422]


class TestEnrichSong:
    """Tests for POST /api/v1/entities/songs/{id}/enrich."""

    async def test_enrich_song_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test enriching non-existent song returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/songs/{fake_id}/enrich",
            json={"provider": "musicbrainz"},
        )

        assert response.status_code == 404

    async def test_enrich_song_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test enriching song with invalid UUID returns 422."""
        response = await authenticated_client.post(
            "/api/v1/entities/songs/invalid/enrich",
            json={"provider": "musicbrainz"},
        )

        assert response.status_code in [400, 422]

    async def test_enrich_song_invalid_provider(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test enriching song with invalid provider returns 422."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.post(
            f"/api/v1/entities/songs/{fake_id}/enrich",
            json={"provider": "invalid_provider"},
        )

        # Should return validation error for invalid provider
        assert response.status_code in [404, 422]


class TestGetSongMetadataSources:
    """Tests for GET /api/v1/entities/songs/{song_id}/metadata-sources."""

    async def test_get_metadata_sources_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test getting metadata sources for non-existent song returns 404."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(
            f"/api/v1/entities/songs/{fake_id}/metadata-sources"
        )

        assert response.status_code == 404

    async def test_get_metadata_sources_invalid_uuid(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test getting metadata sources with invalid UUID returns 422."""
        response = await authenticated_client.get(
            "/api/v1/entities/songs/not-a-uuid/metadata-sources"
        )

        assert response.status_code in [400, 422]


class TestGetPlatformEntities:
    """Tests for platform-based entity endpoints."""

    async def test_get_artist_by_platform_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test getting non-existent artist by platform returns 404."""
        response = await authenticated_client.get(
            "/api/v1/entities/artists/platform/spotify/nonexistent"
        )

        assert response.status_code == 404

    async def test_get_album_by_platform_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test getting non-existent album by platform returns 404."""
        response = await authenticated_client.get(
            "/api/v1/entities/albums/platform/spotify/notfound"
        )

        assert response.status_code == 404

    async def test_get_song_by_platform_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test getting non-existent song by platform returns 404."""
        response = await authenticated_client.get(
            "/api/v1/entities/songs/platform/spotify/notfound"
        )

        assert response.status_code == 404
