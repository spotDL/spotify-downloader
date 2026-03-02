"""Tests for providers API endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProvidersEndpoints:
    """Tests for /api/v1/providers endpoints."""

    async def test_get_all_providers(self, client: AsyncClient) -> None:
        """Test GET /api/v1/providers returns all provider categories."""
        response = await client.get("/api/v1/providers")

        assert response.status_code == 200
        data = response.json()
        assert "audio_sources" in data
        assert "metadata_sources" in data
        assert "lyrics_sources" in data
        assert isinstance(data["audio_sources"], list)
        assert isinstance(data["metadata_sources"], list)
        assert isinstance(data["lyrics_sources"], list)

    async def test_providers_audio_sources_structure(self, client: AsyncClient) -> None:
        """Test audio sources have correct structure."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        for provider in data["audio_sources"]:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider
            assert isinstance(provider["id"], str)
            assert isinstance(provider["name"], str)
            assert isinstance(provider["default_enabled"], bool)

    async def test_providers_metadata_sources_structure(self, client: AsyncClient) -> None:
        """Test metadata sources have correct structure."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        for provider in data["metadata_sources"]:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider

    async def test_providers_lyrics_sources_structure(self, client: AsyncClient) -> None:
        """Test lyrics sources have correct structure."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        for provider in data["lyrics_sources"]:
            assert "id" in provider
            assert "name" in provider
            assert "icon" in provider
            assert "default_enabled" in provider

    async def test_providers_contains_expected_audio_sources(self, client: AsyncClient) -> None:
        """Test providers contains expected audio sources."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        audio_ids = [p["id"] for p in data["audio_sources"]]
        assert "youtube_music" in audio_ids
        assert "youtube" in audio_ids
        assert "soundcloud" in audio_ids

    async def test_providers_contains_expected_metadata_sources(self, client: AsyncClient) -> None:
        """Test providers contains expected metadata sources."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        metadata_ids = [p["id"] for p in data["metadata_sources"]]
        assert "spotify" in metadata_ids
        assert "musicbrainz" in metadata_ids
        assert "discogs" in metadata_ids

    async def test_providers_contains_expected_lyrics_sources(self, client: AsyncClient) -> None:
        """Test providers contains expected lyrics sources."""
        response = await client.get("/api/v1/providers")
        data = response.json()

        lyrics_ids = [p["id"] for p in data["lyrics_sources"]]
        assert "synced" in lyrics_ids
        assert "genius" in lyrics_ids
        assert "musixmatch" in lyrics_ids
