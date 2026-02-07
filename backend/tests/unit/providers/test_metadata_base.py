"""Tests for metadata provider base classes."""

import pytest

from spotdl.core.types.song import Platform, Song
from spotdl.providers.metadata.base import (
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
)


class TestMetadataProviderError:
    """Tests for MetadataProviderError."""

    def test_metadata_provider_error(self) -> None:
        """Test MetadataProviderError creation."""
        error = MetadataProviderError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestMetadataResult:
    """Tests for MetadataResult dataclass."""

    def test_metadata_result_creation(self) -> None:
        """Test creating MetadataResult with basic fields."""
        result = MetadataResult(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            album_name="Test Album",
            isrc="USABC1234567",
        )

        assert result.name == "Test Song"
        assert result.artists == ["Artist 1", "Artist 2"]
        assert result.album_name == "Test Album"
        assert result.isrc == "USABC1234567"
        assert result.confidence == 1.0  # Default value

    def test_metadata_result_defaults(self) -> None:
        """Test MetadataResult default values."""
        result = MetadataResult()

        assert result.name is None
        assert result.artists is None
        assert result.album_name is None
        assert result.genres == []
        assert result.year is None
        assert result.source == ""
        assert result.confidence == 1.0

    def test_metadata_result_to_dict_with_values(self) -> None:
        """Test converting MetadataResult to dict with values."""
        result = MetadataResult(
            name="Test Song",
            artists=["Artist"],
            album_name="Test Album",
            isrc="USABC1234567",
            genres=["rock", "indie"],
            year=2024,
            track_number=5,
            confidence=0.95,
        )

        result_dict = result.to_dict()

        assert result_dict["name"] == "Test Song"
        assert result_dict["artists"] == ["Artist"]
        assert result_dict["album_name"] == "Test Album"
        assert result_dict["isrc"] == "USABC1234567"
        assert result_dict["genres"] == ["rock", "indie"]
        assert result_dict["year"] == 2024
        assert result_dict["track_number"] == 5
        assert result_dict["confidence"] == 0.95

    def test_metadata_result_to_dict_skips_none(self) -> None:
        """Test to_dict skips None values."""
        result = MetadataResult(
            name="Test Song",
            year=None,
            artists=None,
        )

        result_dict = result.to_dict()

        assert "name" in result_dict
        assert "year" not in result_dict
        assert "artists" not in result_dict

    def test_metadata_result_to_dict_skips_empty_lists(self) -> None:
        """Test to_dict skips empty lists."""
        result = MetadataResult(
            name="Test Song",
            genres=[],
        )

        result_dict = result.to_dict()

        assert "name" in result_dict
        assert "genres" not in result_dict

    def test_metadata_result_to_dict_includes_non_empty_lists(self) -> None:
        """Test to_dict includes non-empty lists."""
        result = MetadataResult(
            name="Test Song",
            genres=["rock"],
        )

        result_dict = result.to_dict()

        assert "genres" in result_dict
        assert result_dict["genres"] == ["rock"]

    def test_metadata_result_all_fields(self) -> None:
        """Test MetadataResult with all fields populated."""
        result = MetadataResult(
            name="Complete Song",
            artists=["Artist 1", "Artist 2"],
            album_name="Complete Album",
            album_artist="Album Artist",
            isrc="USABC1234567",
            upc="123456789012",
            musicbrainz_id="mb-abc-123",
            discogs_id="discogs-456",
            genres=["rock", "alternative"],
            year=2024,
            date="2024-06-15",
            track_number=5,
            disc_number=1,
            total_tracks=12,
            total_discs=1,
            album_art_url="https://example.com/art.jpg",
            label="Test Label",
            country="US",
            duration_ms=240000,
            bpm=120.5,
            key="C major",
            source="test_provider",
            confidence=0.98,
        )

        assert result.name == "Complete Song"
        assert result.upc == "123456789012"
        assert result.musicbrainz_id == "mb-abc-123"
        assert result.discogs_id == "discogs-456"
        assert result.total_tracks == 12
        assert result.label == "Test Label"
        assert result.bpm == 120.5

        result_dict = result.to_dict()
        assert len(result_dict) > 15  # Many fields populated


class ConcreteMetadataProvider(MetadataProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"

    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        if isrc == "USABC1234567":
            return MetadataResult(
                name="Test Song",
                artists=["Test Artist"],
                isrc=isrc,
                source=self.name,
            )
        return None

    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        if track_name == "Test Song" and artist_name == "Test Artist":
            return MetadataResult(
                name=track_name,
                artists=[artist_name],
                album_name=album_name,
                source=self.name,
            )
        return None

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        if "test" in query.lower():
            return [
                MetadataResult(
                    name="Test Result 1",
                    artists=["Artist 1"],
                    source=self.name,
                ),
                MetadataResult(
                    name="Test Result 2",
                    artists=["Artist 2"],
                    source=self.name,
                ),
            ]
        return []


class TestMetadataProviderBase:
    """Tests for MetadataProvider base class."""

    def test_provider_initialization(self) -> None:
        """Test provider initialization."""
        provider = ConcreteMetadataProvider()
        assert provider.name == "test"
        assert provider.display_name == "Test Provider"
        assert provider.requests_per_second == 1.0

    @pytest.mark.asyncio
    async def test_lookup_by_isrc(self) -> None:
        """Test looking up metadata by ISRC."""
        provider = ConcreteMetadataProvider()
        result = await provider.lookup_by_isrc("USABC1234567")

        assert result is not None
        assert result.name == "Test Song"
        assert result.artists == ["Test Artist"]
        assert result.isrc == "USABC1234567"

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_found(self) -> None:
        """Test ISRC lookup returns None when not found."""
        provider = ConcreteMetadataProvider()
        result = await provider.lookup_by_isrc("INVALID123")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name(self) -> None:
        """Test looking up metadata by name and artist."""
        provider = ConcreteMetadataProvider()
        result = await provider.lookup_by_name("Test Song", "Test Artist")

        assert result is not None
        assert result.name == "Test Song"
        assert result.artists == ["Test Artist"]

    @pytest.mark.asyncio
    async def test_lookup_by_name_with_album(self) -> None:
        """Test name lookup with album."""
        provider = ConcreteMetadataProvider()
        result = await provider.lookup_by_name(
            "Test Song", "Test Artist", "Test Album"
        )

        assert result is not None
        assert result.album_name == "Test Album"

    @pytest.mark.asyncio
    async def test_lookup_by_name_not_found(self) -> None:
        """Test name lookup returns None when not found."""
        provider = ConcreteMetadataProvider()
        result = await provider.lookup_by_name("Unknown", "Unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        """Test searching for metadata."""
        provider = ConcreteMetadataProvider()
        results = await provider.search("test query")

        assert len(results) == 2
        assert results[0].name == "Test Result 1"
        assert results[1].name == "Test Result 2"

    @pytest.mark.asyncio
    async def test_search_no_results(self) -> None:
        """Test search returns empty list when no results."""
        provider = ConcreteMetadataProvider()
        results = await provider.search("nomatch")
        assert results == []

    @pytest.mark.asyncio
    async def test_lookup_with_raw_default_implementation(self) -> None:
        """Test default lookup_with_raw implementation."""
        provider = ConcreteMetadataProvider()

        # With ISRC
        raw, result = await provider.lookup_with_raw(isrc="USABC1234567")
        assert raw is None  # Default doesn't return raw
        assert result is not None
        assert result.isrc == "USABC1234567"

    @pytest.mark.asyncio
    async def test_lookup_with_raw_fallback_to_name(self) -> None:
        """Test lookup_with_raw falls back to name lookup."""
        provider = ConcreteMetadataProvider()

        raw, result = await provider.lookup_with_raw(
            isrc="INVALID",
            name="Test Song",
            artist="Test Artist",
        )

        assert result is not None
        assert result.name == "Test Song"

    @pytest.mark.asyncio
    async def test_enrich_song_with_isrc(self) -> None:
        """Test enriching song with ISRC lookup."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Original Song",
            artist="Original Artist",
            artists=["Original Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
            isrc="USABC1234567",
        )

        enriched = await provider.enrich_song(song)

        # Should be the same instance
        assert enriched is song
        # ISRC should remain (not overwritten)
        assert song.isrc == "USABC1234567"

    @pytest.mark.asyncio
    async def test_enrich_song_fallback_to_name(self) -> None:
        """Test enriching song falls back to name lookup."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        enriched = await provider.enrich_song(song)
        assert enriched is song

    @pytest.mark.asyncio
    async def test_enrich_song_no_results(self) -> None:
        """Test enriching song when no metadata found."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Unknown Song",
            artist="Unknown Artist",
            artists=["Unknown Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="xyz",
            url="https://open.spotify.com/track/xyz",
        )

        enriched = await provider.enrich_song(song)
        assert enriched is song

    def test_merge_metadata_isrc(self) -> None:
        """Test merging ISRC into song."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
        )

        result = MetadataResult(isrc="USABC1234567")
        provider._merge_metadata(song, result)

        assert song.isrc == "USABC1234567"

    def test_merge_metadata_doesnt_overwrite_isrc(self) -> None:
        """Test merge doesn't overwrite existing ISRC."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            isrc="EXISTING123",
        )

        result = MetadataResult(isrc="USABC1234567")
        provider._merge_metadata(song, result)

        # Should keep original
        assert song.isrc == "EXISTING123"

    def test_merge_metadata_album(self) -> None:
        """Test merging album name."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
        )

        result = MetadataResult(album_name="New Album")
        provider._merge_metadata(song, result)

        assert song.album_name == "New Album"

    def test_merge_metadata_genres(self) -> None:
        """Test merging genres."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            genres=["rock"],
        )

        result = MetadataResult(genres=["indie", "rock"])
        provider._merge_metadata(song, result)

        # Should merge, not replace
        assert set(song.genres) == {"rock", "indie"}

    def test_merge_metadata_year(self) -> None:
        """Test merging year."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            year=0,  # Missing
        )

        result = MetadataResult(year=2024)
        provider._merge_metadata(song, result)

        assert song.year == 2024

    def test_merge_metadata_doesnt_overwrite_year(self) -> None:
        """Test merge doesn't overwrite existing year."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            year=2023,
        )

        result = MetadataResult(year=2024)
        provider._merge_metadata(song, result)

        assert song.year == 2023

    def test_merge_metadata_date(self) -> None:
        """Test merging date."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
        )

        result = MetadataResult(date="2024-06-15")
        provider._merge_metadata(song, result)

        assert song.date == "2024-06-15"

    def test_merge_metadata_track_number(self) -> None:
        """Test merging track number."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            track_number=1,  # Default
        )

        result = MetadataResult(track_number=5)
        provider._merge_metadata(song, result)

        assert song.track_number == 5

    def test_merge_metadata_doesnt_overwrite_track_number(self) -> None:
        """Test merge doesn't overwrite non-default track number."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            track_number=3,
        )

        result = MetadataResult(track_number=5)
        provider._merge_metadata(song, result)

        assert song.track_number == 3

    def test_merge_metadata_disc_number(self) -> None:
        """Test merging disc number."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            disc_number=1,  # Default
        )

        result = MetadataResult(disc_number=2)
        provider._merge_metadata(song, result)

        assert song.disc_number == 2

    def test_merge_metadata_cover_url(self) -> None:
        """Test merging cover URL."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
        )

        result = MetadataResult(album_art_url="https://example.com/art.jpg")
        provider._merge_metadata(song, result)

        assert song.cover_url == "https://example.com/art.jpg"

    def test_merge_metadata_doesnt_overwrite_cover_url(self) -> None:
        """Test merge doesn't overwrite existing cover URL."""
        provider = ConcreteMetadataProvider()

        song = Song(
            name="Test",
            artist="Artist",
            artists=["Artist"],
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
            cover_url="https://existing.com/cover.jpg",
        )

        result = MetadataResult(album_art_url="https://example.com/art.jpg")
        provider._merge_metadata(song, result)

        assert song.cover_url == "https://existing.com/cover.jpg"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing provider."""
        provider = ConcreteMetadataProvider()
        await provider.close()  # Should not raise
