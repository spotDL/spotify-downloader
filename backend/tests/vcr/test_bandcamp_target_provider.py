"""VCR tests for Bandcamp target provider."""

import pytest

from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.bandcamp import BandcampProvider


pytestmark = pytest.mark.asyncio


class TestBandcampTargetProviderVCR:
    """VCR tests for BandcampProvider (target) with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> BandcampProvider:
        """Create a Bandcamp target provider instance."""
        return BandcampProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing search."""
        return Song(
            name="First Light",
            artists=["CFR"],
            artist="CFR",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

    @pytest.mark.vcr
    async def test_search(
        self, provider: BandcampProvider, sample_song: Song
    ) -> None:
        """Test searching for a song on Bandcamp."""
        results = await provider.search(sample_song, limit=5)

        # Bandcamp search might not always return results
        assert isinstance(results, list)
        if len(results) > 0:
            first_result = results[0]
            assert first_result.platform == TargetPlatform.BANDCAMP
            assert first_result.name is not None

        await provider.close()

    @staticmethod
    def test_build_search_query() -> None:
        """Test building search query from song."""
        provider = BandcampProvider()
        song = Song(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        query = provider.build_search_query(song)
        assert "Test Song" in query
        assert "Artist 1" in query

    @staticmethod
    def test_extract_url_info() -> None:
        """Test extracting URL info from Bandcamp URL."""
        result = BandcampProvider.extract_url_info(
            "https://artist.bandcamp.com/track/song-name"
        )
        assert result == {"subdomain": "artist", "type": "track", "slug": "song-name"}

    @staticmethod
    def test_extract_url_info_invalid() -> None:
        """Test extracting URL info from invalid URL."""
        result = BandcampProvider.extract_url_info("https://example.com/track/abc")
        assert result is None

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = BandcampProvider()
        assert provider.name == "bandcamp"
        assert provider.display_name == "Bandcamp"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = BandcampProvider()
        await provider.close()
