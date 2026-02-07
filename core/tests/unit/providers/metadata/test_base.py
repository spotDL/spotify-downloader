"""Unit tests for spotdl_core.providers.metadata.base module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl_core.providers.metadata.base import (
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
)
from spotdl_core.types.song import Platform, Song


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def sample_result() -> MetadataResult:
    """Sample metadata result for testing."""
    return MetadataResult(
        name="Test Song",
        artists=["Test Artist", "Featured Artist"],
        album_name="Test Album",
        album_artist="Test Artist",
        isrc="USRC12345678",
        upc="123456789012",
        musicbrainz_id="mb-123",
        discogs_id="discogs-456",
        genres=["Pop", "Rock"],
        year=2024,
        date="2024-01-15",
        track_number=5,
        disc_number=1,
        total_tracks=10,
        total_discs=2,
        album_art_url="https://example.com/cover.jpg",
        label="Test Label",
        country="US",
        duration_ms=180000,
        bpm=120.0,
        key="C",
        source="test",
        confidence=0.95,
    )


@pytest.fixture
def sample_song() -> Song:
    """Sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="123",
        url="https://open.spotify.com/track/123",
        album_name="Test Album",
        isrc="USRC12345678",
        year=2024,
        genres=["Pop"],
        track_number=1,
        disc_number=1,
    )


@pytest.fixture
def mock_provider():
    """Create a mock metadata provider."""

    class MockProvider(MetadataProvider):
        name = "mock"
        display_name = "Mock Provider"

        async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
            return None

        async def lookup_by_name(
            self,
            track_name: str,
            artist_name: str,
            album_name: str | None = None,
        ) -> MetadataResult | None:
            return None

        async def search(
            self,
            query: str,
            limit: int = 10,
        ) -> list[MetadataResult]:
            return []

    return MockProvider()


# ── 1. MetadataResult Tests ─────────────────────────────────────────


class TestMetadataResult:
    """Test MetadataResult dataclass."""

    def test_create_minimal_result(self) -> None:
        """Test creating minimal metadata result."""
        result = MetadataResult()
        assert result.name is None
        assert result.artists is None
        assert result.genres == []
        assert result.source == ""
        assert result.confidence == 1.0

    def test_create_full_result(self, sample_result: MetadataResult) -> None:
        """Test creating complete metadata result."""
        assert sample_result.name == "Test Song"
        assert sample_result.artists == ["Test Artist", "Featured Artist"]
        assert sample_result.album_name == "Test Album"
        assert sample_result.isrc == "USRC12345678"
        assert sample_result.year == 2024
        assert sample_result.genres == ["Pop", "Rock"]
        assert sample_result.confidence == 0.95

    def test_result_with_identifiers(self, sample_result: MetadataResult) -> None:
        """Test metadata result with various identifiers."""
        assert sample_result.isrc == "USRC12345678"
        assert sample_result.upc == "123456789012"
        assert sample_result.musicbrainz_id == "mb-123"
        assert sample_result.discogs_id == "discogs-456"

    def test_result_with_track_info(self, sample_result: MetadataResult) -> None:
        """Test metadata result with track information."""
        assert sample_result.track_number == 5
        assert sample_result.disc_number == 1
        assert sample_result.total_tracks == 10
        assert sample_result.total_discs == 2

    def test_result_with_album_info(self, sample_result: MetadataResult) -> None:
        """Test metadata result with album information."""
        assert sample_result.album_art_url == "https://example.com/cover.jpg"
        assert sample_result.label == "Test Label"
        assert sample_result.country == "US"

    def test_result_with_audio_features(self, sample_result: MetadataResult) -> None:
        """Test metadata result with audio features."""
        assert sample_result.duration_ms == 180000
        assert sample_result.bpm == 120.0
        assert sample_result.key == "C"

    def test_result_default_genres(self) -> None:
        """Test default empty genres list."""
        result = MetadataResult(name="Test")
        assert result.genres == []
        assert isinstance(result.genres, list)

    def test_result_source_info(self, sample_result: MetadataResult) -> None:
        """Test metadata result source information."""
        assert sample_result.source == "test"
        assert sample_result.confidence == 0.95


# ── 2. MetadataProviderError Tests ──────────────────────────────────


class TestMetadataProviderError:
    """Test MetadataProviderError exception."""

    def test_create_error(self) -> None:
        """Test creating metadata provider error."""
        error = MetadataProviderError("Test error")
        assert str(error) == "Test error"

    def test_error_inheritance(self) -> None:
        """Test error inherits from Exception."""
        error = MetadataProviderError("Test")
        assert isinstance(error, Exception)

    def test_raise_error(self) -> None:
        """Test raising metadata provider error."""
        with pytest.raises(MetadataProviderError, match="Test error"):
            raise MetadataProviderError("Test error")


# ── 3. MetadataProvider Abstract Class Tests ────────────────────────


class TestMetadataProviderAbstract:
    """Test MetadataProvider abstract base class."""

    def test_provider_attributes(self, mock_provider) -> None:
        """Test provider has required attributes."""
        assert hasattr(mock_provider, "name")
        assert hasattr(mock_provider, "display_name")
        assert hasattr(mock_provider, "requests_per_second")

    def test_provider_default_values(self, mock_provider) -> None:
        """Test provider default attribute values."""
        assert mock_provider.name == "mock"
        assert mock_provider.display_name == "Mock Provider"
        assert mock_provider.requests_per_second == 1.0

    def test_provider_initialization(self, mock_provider) -> None:
        """Test provider initialization."""
        assert mock_provider is not None

    def test_cannot_instantiate_base_class(self) -> None:
        """Test cannot instantiate abstract base class."""
        with pytest.raises(TypeError):
            MetadataProvider()

    def test_requires_lookup_by_isrc_implementation(self) -> None:
        """Test requires lookup_by_isrc implementation."""

        class IncompleteProvider(MetadataProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_requires_lookup_by_name_implementation(self) -> None:
        """Test requires lookup_by_name implementation."""

        class PartialProvider(MetadataProvider):
            async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
                return None

        with pytest.raises(TypeError):
            PartialProvider()


# ── 4. Lookup Methods Tests ─────────────────────────────────────────


class TestLookupMethods:
    """Test lookup method interfaces."""

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_signature(self, mock_provider) -> None:
        """Test lookup_by_isrc method signature."""
        result = await mock_provider.lookup_by_isrc("USRC12345678")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_signature(self, mock_provider) -> None:
        """Test lookup_by_name method signature."""
        result = await mock_provider.lookup_by_name("Song", "Artist")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_with_album(self, mock_provider) -> None:
        """Test lookup_by_name with optional album."""
        result = await mock_provider.lookup_by_name("Song", "Artist", "Album")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_signature(self, mock_provider) -> None:
        """Test search method signature."""
        results = await mock_provider.search("query")
        assert results == []
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, mock_provider) -> None:
        """Test search method with limit parameter."""
        results = await mock_provider.search("query", limit=5)
        assert results == []


# ── 5. Enrich Song Tests ────────────────────────────────────────────


class TestEnrichSong:
    """Test enrich_song functionality."""

    @pytest.mark.asyncio
    async def test_enrich_song_with_isrc(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test enriching song with ISRC lookup."""
        mock_provider.lookup_by_isrc = AsyncMock(return_value=sample_result)
        mock_provider.lookup_by_name = AsyncMock(return_value=None)

        enriched = await mock_provider.enrich_song(sample_song)

        mock_provider.lookup_by_isrc.assert_called_once_with("USRC12345678")
        mock_provider.lookup_by_name.assert_not_called()
        assert enriched is sample_song

    @pytest.mark.asyncio
    async def test_enrich_song_fallback_to_name(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test falling back to name lookup when ISRC fails."""
        mock_provider.lookup_by_isrc = AsyncMock(return_value=None)
        mock_provider.lookup_by_name = AsyncMock(return_value=sample_result)

        await mock_provider.enrich_song(sample_song)

        mock_provider.lookup_by_isrc.assert_called_once()
        mock_provider.lookup_by_name.assert_called_once_with(
            track_name="Test Song",
            artist_name="Test Artist",
            album_name="Test Album",
        )

    @pytest.mark.asyncio
    async def test_enrich_song_no_isrc(
        self, mock_provider, sample_result: MetadataResult
    ) -> None:
        """Test enriching song without ISRC."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            isrc=None,
        )

        mock_provider.lookup_by_isrc = AsyncMock()
        mock_provider.lookup_by_name = AsyncMock(return_value=sample_result)

        await mock_provider.enrich_song(song)

        mock_provider.lookup_by_isrc.assert_not_called()
        mock_provider.lookup_by_name.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_song_no_results(self, mock_provider, sample_song: Song) -> None:
        """Test enriching song when no results found."""
        mock_provider.lookup_by_isrc = AsyncMock(return_value=None)
        mock_provider.lookup_by_name = AsyncMock(return_value=None)

        enriched = await mock_provider.enrich_song(sample_song)

        assert enriched is sample_song

    @pytest.mark.asyncio
    async def test_enrich_song_calls_merge_metadata(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test enrich_song calls _merge_metadata."""
        mock_provider.lookup_by_isrc = AsyncMock(return_value=sample_result)

        with patch.object(mock_provider, "_merge_metadata") as mock_merge:
            await mock_provider.enrich_song(sample_song)
            mock_merge.assert_called_once_with(sample_song, sample_result)


# ── 6. Merge Metadata Tests ─────────────────────────────────────────


class TestMergeMetadata:
    """Test _merge_metadata functionality."""

    def test_merge_isrc_when_missing(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging ISRC when song doesn't have one."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            isrc=None,
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.isrc == "USRC12345678"

    def test_merge_does_not_overwrite_isrc(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test existing ISRC is not overwritten."""
        original_isrc = sample_song.isrc
        mock_provider._merge_metadata(sample_song, sample_result)
        assert sample_song.isrc == original_isrc

    def test_merge_album_name_when_missing(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging album name when missing."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            album_name="",
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.album_name == "Test Album"

    def test_merge_does_not_overwrite_album(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test existing album is not overwritten."""
        original_album = sample_song.album_name
        mock_provider._merge_metadata(sample_song, sample_result)
        assert sample_song.album_name == original_album

    def test_merge_genres(self, mock_provider, sample_song: Song, sample_result: MetadataResult) -> None:
        """Test merging genres."""
        mock_provider._merge_metadata(sample_song, sample_result)
        assert "Pop" in sample_song.genres
        assert "Rock" in sample_song.genres

    def test_merge_genres_no_duplicates(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging genres without duplicates."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            genres=["Pop", "Electronic"],
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.genres.count("Pop") == 1
        assert "Rock" in song.genres
        assert "Electronic" in song.genres

    def test_merge_year_when_zero(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging year when song has 0."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            year=0,
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.year == 2024

    def test_merge_does_not_overwrite_year(
        self, mock_provider, sample_song: Song, sample_result: MetadataResult
    ) -> None:
        """Test existing year is not overwritten."""
        original_year = sample_song.year
        mock_provider._merge_metadata(sample_song, sample_result)
        assert sample_song.year == original_year

    def test_merge_date_when_missing(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging date when missing."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            date="",
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.date == "2024-01-15"

    def test_merge_track_number_when_default(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging track number when it's default (1)."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            track_number=1,
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.track_number == 5

    def test_merge_does_not_update_track_number_to_one(
        self, mock_provider, sample_song: Song
    ) -> None:
        """Test track number 1 in result doesn't override."""
        result = MetadataResult(track_number=1)
        original_track = sample_song.track_number
        mock_provider._merge_metadata(sample_song, result)
        assert sample_song.track_number == original_track

    def test_merge_disc_number_when_default(self, mock_provider) -> None:
        """Test merging disc number when it's default (1)."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            disc_number=1,
        )

        result = MetadataResult(disc_number=2)
        mock_provider._merge_metadata(song, result)
        assert song.disc_number == 2

    def test_merge_cover_url_when_missing(self, mock_provider, sample_result: MetadataResult) -> None:
        """Test merging cover URL when missing."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            cover_url=None,
        )

        mock_provider._merge_metadata(song, sample_result)
        assert song.cover_url == "https://example.com/cover.jpg"

    def test_merge_does_not_overwrite_cover_url(
        self, mock_provider, sample_result: MetadataResult
    ) -> None:
        """Test existing cover URL is not overwritten."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            cover_url="https://existing.com/cover.jpg",
        )

        original_url = song.cover_url
        mock_provider._merge_metadata(song, sample_result)
        assert song.cover_url == original_url

    def test_merge_with_empty_result(self, mock_provider, sample_song: Song) -> None:
        """Test merging with empty result."""
        result = MetadataResult()
        original_data = {
            "isrc": sample_song.isrc,
            "album_name": sample_song.album_name,
            "year": sample_song.year,
        }

        mock_provider._merge_metadata(sample_song, result)

        assert sample_song.isrc == original_data["isrc"]
        assert sample_song.album_name == original_data["album_name"]
        assert sample_song.year == original_data["year"]

    def test_merge_partial_result(self, mock_provider, sample_song: Song) -> None:
        """Test merging with partial result."""
        song = Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://open.spotify.com/track/123",
            album_name="",
            year=0,
        )

        result = MetadataResult(
            album_name="New Album",
            year=2024,
        )

        mock_provider._merge_metadata(song, result)
        assert song.album_name == "New Album"
        assert song.year == 2024


# ── 7. Close Method Tests ───────────────────────────────────────────


class TestCloseMethod:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_method_exists(self, mock_provider) -> None:
        """Test close method exists."""
        await mock_provider.close()

    @pytest.mark.asyncio
    async def test_close_method_no_error(self, mock_provider) -> None:
        """Test close method doesn't raise errors."""
        await mock_provider.close()
        await mock_provider.close()


# ── 8. Edge Cases and Error Handling ────────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_merge_with_none_values_in_result(self, mock_provider, sample_song: Song) -> None:
        """Test merging when result has None values."""
        result = MetadataResult(
            name=None,
            artists=None,
            album_name=None,
            isrc=None,
            year=None,
        )

        original_data = {
            "name": sample_song.name,
            "album_name": sample_song.album_name,
        }

        mock_provider._merge_metadata(sample_song, result)

        assert sample_song.name == original_data["name"]
        assert sample_song.album_name == original_data["album_name"]

    def test_merge_empty_genres_list(self, mock_provider, sample_song: Song) -> None:
        """Test merging with empty genres list."""
        result = MetadataResult(genres=[])
        original_genres = sample_song.genres.copy()

        mock_provider._merge_metadata(sample_song, result)
        assert sample_song.genres == original_genres

    @pytest.mark.asyncio
    async def test_enrich_song_returns_same_instance(
        self, mock_provider, sample_song: Song
    ) -> None:
        """Test enrich_song returns the same song instance."""
        mock_provider.lookup_by_isrc = AsyncMock(return_value=None)
        mock_provider.lookup_by_name = AsyncMock(return_value=None)

        result = await mock_provider.enrich_song(sample_song)
        assert result is sample_song

    def test_metadata_result_confidence_default(self) -> None:
        """Test metadata result default confidence value."""
        result = MetadataResult()
        assert result.confidence == 1.0

    def test_metadata_result_source_default(self) -> None:
        """Test metadata result default source value."""
        result = MetadataResult()
        assert result.source == ""
