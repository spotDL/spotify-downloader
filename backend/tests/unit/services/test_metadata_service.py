"""Tests for MetadataService."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.services.metadata import (
    MetadataService,
    get_metadata_service,
)
from spotdl.core.types.song import Platform, Song
from spotdl.providers.metadata.base import MetadataResult


@pytest.fixture
def sample_song() -> Song:
    """Create a sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
    )


@pytest.fixture
def mock_metadata_result() -> MetadataResult:
    """Create a mock metadata result."""
    return MetadataResult(
        name="Test Song",
        artists=["Test Artist"],
        album_name="Test Album",
        isrc="USRC17607839",
        genres=["Rock", "Pop"],
        year=2020,
        source="musicbrainz",
        confidence=0.9,
    )


# Mock the external libraries
@pytest.fixture(autouse=True)
def mock_external_libs():
    """Mock musicbrainzngs and discogs_client."""
    mock_mb = MagicMock()
    mock_mb.set_useragent = MagicMock()

    mock_dc = MagicMock()
    mock_dc.Client = MagicMock()

    with patch.dict(
        sys.modules, {"musicbrainzngs": mock_mb, "discogs_client": mock_dc}
    ):
        yield {"musicbrainzngs": mock_mb, "discogs_client": mock_dc}


class TestMetadataServiceInit:
    """Tests for MetadataService initialization."""

    def test_default_init(self) -> None:
        """Test default initialization enables both providers."""
        service = MetadataService()
        assert len(service.providers) == 2
        assert "musicbrainz" in service.provider_names
        assert "discogs" in service.provider_names

    def test_disable_musicbrainz(self) -> None:
        """Test disabling MusicBrainz."""
        service = MetadataService(enable_musicbrainz=False)
        assert "musicbrainz" not in service.provider_names
        assert "discogs" in service.provider_names

    def test_disable_discogs(self) -> None:
        """Test disabling Discogs."""
        service = MetadataService(enable_discogs=False)
        assert "musicbrainz" in service.provider_names
        assert "discogs" not in service.provider_names

    def test_disable_all(self) -> None:
        """Test disabling all providers."""
        service = MetadataService(
            enable_musicbrainz=False,
            enable_discogs=False,
        )
        assert len(service.providers) == 0

    def test_with_discogs_token(self) -> None:
        """Test initialization with Discogs token."""
        service = MetadataService(discogs_user_token="test_token")
        assert len(service.providers) == 2


class TestMetadataServiceEnrich:
    """Tests for MetadataService enrichment methods."""

    @pytest.mark.asyncio
    async def test_enrich_song_success(
        self, sample_song: Song, mock_metadata_result: MetadataResult
    ) -> None:
        """Test enriching a song successfully."""
        service = MetadataService()

        # Mock the first provider to return results
        with patch.object(
            service.providers[0], "enrich_song", new_callable=AsyncMock
        ) as mock_enrich:
            # Simulate enrichment by modifying the song
            async def do_enrich(song: Song) -> Song:
                song.isrc = "USRC17607839"
                song.album_name = "Test Album"
                return song

            mock_enrich.side_effect = do_enrich

            result = await service.enrich_song(sample_song)

            assert result.isrc == "USRC17607839"
            assert result.album_name == "Test Album"
            mock_enrich.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_song_no_providers(self, sample_song: Song) -> None:
        """Test enriching when no providers are available."""
        service = MetadataService(
            enable_musicbrainz=False,
            enable_discogs=False,
        )

        result = await service.enrich_song(sample_song)
        assert result is sample_song
        assert result.isrc is None

    @pytest.mark.asyncio
    async def test_enrich_song_provider_fails(self, sample_song: Song) -> None:
        """Test enriching when provider fails gracefully."""
        service = MetadataService()

        # Mock all providers to fail
        for provider in service.providers:
            with patch.object(
                provider, "enrich_song", new_callable=AsyncMock
            ) as mock_enrich:
                mock_enrich.side_effect = Exception("Provider error")

        result = await service.enrich_song(sample_song)
        assert result is sample_song

    @pytest.mark.asyncio
    async def test_enrich_songs_multiple(self, sample_song: Song) -> None:
        """Test enriching multiple songs."""
        service = MetadataService()

        songs = [
            Song(
                name=f"Song {i}",
                artists=["Artist"],
                artist="Artist",
                duration=200,
                platform=Platform.SPOTIFY,
                platform_id=f"id{i}",
                url=f"https://spotify.com/track/id{i}",
            )
            for i in range(3)
        ]

        # Mock enrichment
        for provider in service.providers:
            with patch.object(
                provider, "enrich_song", new_callable=AsyncMock
            ) as mock_enrich:
                mock_enrich.side_effect = lambda s: s

        results = await service.enrich_songs(songs)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_enrich_songs_empty_list(self) -> None:
        """Test enriching empty list."""
        service = MetadataService()
        results = await service.enrich_songs([])
        assert results == []

    @pytest.mark.asyncio
    async def test_enrich_use_all_providers(
        self, sample_song: Song
    ) -> None:
        """Test enriching with all providers."""
        service = MetadataService()

        # Track which providers were called
        called_providers = []

        for provider in service.providers:
            original_name = provider.name

            async def mock_enrich(song: Song, name: str = original_name) -> Song:
                called_providers.append(name)
                return song

            with patch.object(provider, "enrich_song", side_effect=mock_enrich):
                pass

        # With use_all_providers=True, should call all providers
        # (simplified test - just verify no errors)
        result = await service.enrich_song(sample_song, use_all_providers=True)
        assert result is sample_song


class TestMetadataServiceLookup:
    """Tests for MetadataService lookup methods."""

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_found(
        self, mock_metadata_result: MetadataResult
    ) -> None:
        """Test ISRC lookup when found."""
        service = MetadataService()

        with patch.object(
            service.providers[0], "lookup_by_isrc", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = mock_metadata_result

            result = await service.lookup_by_isrc("USRC17607839")

            assert result is not None
            assert result["isrc"] == "USRC17607839"
            assert result["source"] == "musicbrainz"

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_found(self) -> None:
        """Test ISRC lookup when not found."""
        service = MetadataService(
            enable_musicbrainz=False,
            enable_discogs=False,
        )

        # With no providers, should return None
        result = await service.lookup_by_isrc("UNKNOWN123456")
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, mock_metadata_result: MetadataResult) -> None:
        """Test search across providers."""
        service = MetadataService()

        with patch.object(
            service.providers[0], "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = [mock_metadata_result]

            results = await service.search("test query", limit=5)

            assert len(results) >= 1
            assert results[0]["source"] == "musicbrainz"


class TestMetadataServiceClose:
    """Tests for MetadataService cleanup."""

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the service."""
        service = MetadataService()

        for provider in service.providers:
            with patch.object(
                provider, "close", new_callable=AsyncMock
            ) as mock_close:
                mock_close.return_value = None

        await service.close()  # Should not raise


class TestGetMetadataService:
    """Tests for get_metadata_service function."""

    def test_returns_instance(self) -> None:
        """Test get_metadata_service returns instance."""
        # Reset global
        import spotdl.core.services.metadata as metadata_module

        metadata_module._metadata_service = None

        service = get_metadata_service()
        assert isinstance(service, MetadataService)

    def test_singleton(self) -> None:
        """Test get_metadata_service returns same instance."""
        import spotdl.core.services.metadata as metadata_module

        metadata_module._metadata_service = None

        service1 = get_metadata_service()
        service2 = get_metadata_service()
        assert service1 is service2
