"""VCR tests for Piped target provider."""

import pytest

from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.base import SearchError
from spotdl.providers.targets.piped import PipedProvider

pytestmark = pytest.mark.asyncio


class TestPipedTargetProviderVCR:
    """VCR tests for PipedProvider (target) with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> PipedProvider:
        """Create a Piped target provider instance."""
        return PipedProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing search."""
        return Song(
            name="Harder, Better, Faster, Stronger",
            artists=["Daft Punk"],
            artist="Daft Punk",
            duration=226,
            platform=Platform.DEEZER,
            platform_id="3135556",
            url="https://www.deezer.com/track/3135556",
            album_name="Discovery",
        )

    @pytest.mark.skip(reason="All public Piped API instances are shut down or blocked")
    @pytest.mark.vcr
    async def test_search(self, provider: PipedProvider, sample_song: Song) -> None:
        """Test searching for a song on Piped."""
        results = await provider.search(sample_song, limit=5)
        assert len(results) > 0
        assert results[0].platform == TargetPlatform.PIPED
        assert "youtube.com" in results[0].url
        await provider.close()

    @staticmethod
    def test_build_search_query() -> None:
        """Test building search query from song."""
        provider = PipedProvider()
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
    def test_extract_video_id_youtube() -> None:
        """Test extracting video ID from YouTube URL."""
        result = PipedProvider.extract_video_id("https://www.youtube.com/watch?v=abc123xyz12")
        assert result == "abc123xyz12"

    @staticmethod
    def test_extract_video_id_short() -> None:
        """Test extracting video ID from short URL."""
        result = PipedProvider.extract_video_id("https://youtu.be/xyz789abc12")
        assert result == "xyz789abc12"

    @staticmethod
    def test_extract_video_id_invalid() -> None:
        """Test extracting video ID from invalid URL."""
        result = PipedProvider.extract_video_id("https://example.com/video/abc")
        assert result is None

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = PipedProvider()
        assert provider.name == "piped"
        assert provider.display_name == "Piped"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = PipedProvider()
        await provider.close()
