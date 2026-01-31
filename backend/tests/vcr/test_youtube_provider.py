"""VCR tests for YouTube target provider."""

import pytest

from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.base import SearchError
from spotdl.providers.targets.youtube import YouTubeProvider


pytestmark = pytest.mark.asyncio


class TestYouTubeProviderVCR:
    """VCR tests for YouTubeProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> YouTubeProvider:
        """Create a YouTube provider instance."""
        return YouTubeProvider()

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

    @pytest.mark.vcr
    async def test_search(self, provider: YouTubeProvider, sample_song: Song) -> None:
        """Test searching for a song on YouTube.

        Note: This test depends on Invidious instances which can be unreliable.
        The test will be skipped if no working instance is available.
        """
        try:
            results = await provider.search(sample_song, limit=5)
        except SearchError as e:
            if "No working Invidious instance" in str(e) or "search failed" in str(e):
                pytest.skip("Invidious instances unavailable")
            raise

        assert len(results) > 0
        first_result = results[0]
        assert first_result.platform == TargetPlatform.YOUTUBE
        assert first_result.url.startswith("https://www.youtube.com/watch?v=")
        assert first_result.duration > 0

        await provider.close()

    @staticmethod
    def test_extract_video_id_standard() -> None:
        """Test extracting video ID from standard YouTube URL."""
        result = YouTubeProvider.extract_video_id(
            "https://www.youtube.com/watch?v=gAjR4_CbPpQ"
        )
        assert result == "gAjR4_CbPpQ"

    @staticmethod
    def test_extract_video_id_short() -> None:
        """Test extracting video ID from short YouTube URL."""
        result = YouTubeProvider.extract_video_id("https://youtu.be/gAjR4_CbPpQ")
        assert result == "gAjR4_CbPpQ"

    @staticmethod
    def test_extract_video_id_with_params() -> None:
        """Test extracting video ID from URL with extra params."""
        result = YouTubeProvider.extract_video_id(
            "https://www.youtube.com/watch?v=gAjR4_CbPpQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        )
        assert result == "gAjR4_CbPpQ"

    @staticmethod
    def test_extract_video_id_invalid() -> None:
        """Test extracting video ID from invalid URL."""
        result = YouTubeProvider.extract_video_id("https://example.com/watch?v=abc")
        assert result is None

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = YouTubeProvider()
        assert provider.name == "youtube"
        assert provider.display_name == "YouTube"
