"""VCR tests for YouTube Music target provider."""

import pytest

from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.ytmusic import YouTubeMusicProvider


pytestmark = pytest.mark.asyncio


class TestYouTubeMusicTargetProviderVCR:
    """VCR tests for YouTubeMusicProvider (target) with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> YouTubeMusicProvider:
        """Create a YouTube Music target provider instance."""
        return YouTubeMusicProvider()

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

    @pytest.fixture
    def sample_song_with_isrc(self) -> Song:
        """Create a sample song with ISRC for testing."""
        return Song(
            name="Harder, Better, Faster, Stronger",
            artists=["Daft Punk"],
            artist="Daft Punk",
            duration=226,
            platform=Platform.DEEZER,
            platform_id="3135556",
            url="https://www.deezer.com/track/3135556",
            album_name="Discovery",
            isrc="GBDUW0000059",
        )

    @pytest.mark.vcr
    async def test_search(
        self, provider: YouTubeMusicProvider, sample_song: Song
    ) -> None:
        """Test searching for a song on YouTube Music."""
        results = await provider.search(sample_song, limit=5)

        assert len(results) > 0
        first_result = results[0]
        assert first_result.platform == TargetPlatform.YOUTUBE_MUSIC
        assert first_result.url.startswith("https://music.youtube.com/watch?v=")
        assert first_result.duration > 0

    @pytest.mark.vcr
    async def test_search_by_isrc(
        self, provider: YouTubeMusicProvider, sample_song_with_isrc: Song
    ) -> None:
        """Test searching by ISRC code on YouTube Music."""
        result = await provider.search_by_isrc(sample_song_with_isrc.isrc)

        if result is not None:
            # ISRC search may not always find results
            assert result.platform == TargetPlatform.YOUTUBE_MUSIC
            assert result.duration > 0

    @staticmethod
    def test_build_search_query() -> None:
        """Test building search query from song."""
        provider = YouTubeMusicProvider()
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

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = YouTubeMusicProvider()
        assert provider.name == "youtube_music"
        assert provider.display_name == "YouTube Music"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = YouTubeMusicProvider()
        # Should not raise
        await provider.close()
