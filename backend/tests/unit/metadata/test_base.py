"""Tests for metadata provider base class."""

from __future__ import annotations

import pytest

from spotdl.core.types.song import Platform, Song
from spotdl.providers.metadata.base import MetadataProvider, MetadataResult


class MockMetadataProvider(MetadataProvider):
    """Mock implementation for testing."""

    name = "mock"
    display_name = "Mock Provider"

    def __init__(self) -> None:
        super().__init__()
        self.lookup_isrc_called = False
        self.lookup_name_called = False
        self.search_called = False

    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        self.lookup_isrc_called = True
        if isrc == "USRC17607839":
            return MetadataResult(
                name="Test Track",
                artists=["Test Artist"],
                album_name="Test Album",
                isrc=isrc,
                genres=["Rock", "Pop"],
                year=2020,
                source="mock",
            )
        return None

    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        self.lookup_name_called = True
        if track_name == "Known Track":
            return MetadataResult(
                name=track_name,
                artists=[artist_name],
                album_name=album_name or "Found Album",
                genres=["Electronic"],
                year=2021,
                source="mock",
            )
        return None

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        self.search_called = True
        return [
            MetadataResult(
                name=f"Result {i}",
                artists=["Artist"],
                source="mock",
            )
            for i in range(min(limit, 3))
        ]


class TestMetadataResult:
    """Tests for MetadataResult dataclass."""

    def test_default_values(self) -> None:
        """Test MetadataResult has correct defaults."""
        result = MetadataResult()
        assert result.name is None
        assert result.artists is None
        assert result.album_name is None
        assert result.isrc is None
        assert result.genres == []
        assert result.year is None
        assert result.source == ""
        assert result.confidence == 1.0

    def test_with_values(self) -> None:
        """Test MetadataResult with provided values."""
        result = MetadataResult(
            name="Track",
            artists=["Artist1", "Artist2"],
            album_name="Album",
            isrc="ABC123",
            genres=["Rock"],
            year=2020,
            source="test",
            confidence=0.9,
        )
        assert result.name == "Track"
        assert result.artists == ["Artist1", "Artist2"]
        assert result.album_name == "Album"
        assert result.isrc == "ABC123"
        assert result.genres == ["Rock"]
        assert result.year == 2020
        assert result.source == "test"
        assert result.confidence == 0.9


class TestMetadataProvider:
    """Tests for MetadataProvider base class."""

    @pytest.fixture
    def provider(self) -> MockMetadataProvider:
        """Create a mock provider for testing."""
        return MockMetadataProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
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

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_found(self, provider: MockMetadataProvider) -> None:
        """Test ISRC lookup returns result when found."""
        result = await provider.lookup_by_isrc("USRC17607839")
        assert result is not None
        assert result.name == "Test Track"
        assert result.isrc == "USRC17607839"
        assert provider.lookup_isrc_called

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_found(self, provider: MockMetadataProvider) -> None:
        """Test ISRC lookup returns None when not found."""
        result = await provider.lookup_by_isrc("UNKNOWN123")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_found(self, provider: MockMetadataProvider) -> None:
        """Test name lookup returns result when found."""
        result = await provider.lookup_by_name("Known Track", "Some Artist")
        assert result is not None
        assert result.name == "Known Track"
        assert provider.lookup_name_called

    @pytest.mark.asyncio
    async def test_lookup_by_name_not_found(self, provider: MockMetadataProvider) -> None:
        """Test name lookup returns None when not found."""
        result = await provider.lookup_by_name("Unknown Track", "Unknown Artist")
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, provider: MockMetadataProvider) -> None:
        """Test search returns results."""
        results = await provider.search("test query", limit=5)
        assert len(results) == 3  # Mock returns max 3
        assert provider.search_called

    @pytest.mark.asyncio
    async def test_enrich_song_with_isrc(
        self, provider: MockMetadataProvider, sample_song: Song
    ) -> None:
        """Test enriching song when ISRC is available."""
        sample_song.isrc = "USRC17607839"
        enriched = await provider.enrich_song(sample_song)

        assert enriched is sample_song  # Same instance
        assert provider.lookup_isrc_called
        assert sample_song.album_name == "Test Album"
        assert "Rock" in sample_song.genres
        assert sample_song.year == 2020

    @pytest.mark.asyncio
    async def test_enrich_song_without_isrc(self, provider: MockMetadataProvider) -> None:
        """Test enriching song falls back to name lookup."""
        song = Song(
            name="Known Track",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        enriched = await provider.enrich_song(song)

        assert provider.lookup_name_called
        assert song.album_name == "Found Album"
        assert "Electronic" in song.genres

    @pytest.mark.asyncio
    async def test_enrich_song_not_found(
        self, provider: MockMetadataProvider, sample_song: Song
    ) -> None:
        """Test enriching song when metadata not found."""
        sample_song.name = "Unknown Track"
        enriched = await provider.enrich_song(sample_song)

        assert enriched is sample_song
        # Song should remain unchanged (album_name defaults to "")
        assert sample_song.album_name == ""

    @pytest.mark.asyncio
    async def test_merge_metadata_preserves_existing(self, provider: MockMetadataProvider) -> None:
        """Test that merge doesn't overwrite existing data."""
        song = Song(
            name="Track",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://example.com",
            album_name="Existing Album",  # Already has album
            year=2019,  # Already has year
        )

        result = MetadataResult(
            album_name="New Album",  # Different album
            year=2020,  # Different year
            genres=["Jazz"],
        )

        provider._merge_metadata(song, result)

        # Should preserve existing values
        assert song.album_name == "Existing Album"
        assert song.year == 2019
        # But add new data
        assert "Jazz" in song.genres

    @pytest.mark.asyncio
    async def test_merge_metadata_fills_missing(self, provider: MockMetadataProvider) -> None:
        """Test that merge fills in missing data."""
        song = Song(
            name="Track",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://example.com",
        )

        result = MetadataResult(
            album_name="Found Album",
            isrc="ABC123",
            year=2020,
            date="2020-05-15",
            track_number=5,
            disc_number=2,  # Non-default value
            album_art_url="https://example.com/cover.jpg",
            genres=["Pop", "Rock"],
        )

        provider._merge_metadata(song, result)

        assert song.album_name == "Found Album"
        assert song.isrc == "ABC123"
        assert song.year == 2020
        assert song.date == "2020-05-15"
        assert song.track_number == 5
        assert song.disc_number == 2
        assert song.cover_url == "https://example.com/cover.jpg"
        assert "Pop" in song.genres
        assert "Rock" in song.genres

    @pytest.mark.asyncio
    async def test_close(self, provider: MockMetadataProvider) -> None:
        """Test close method exists and doesn't error."""
        await provider.close()  # Should not raise
