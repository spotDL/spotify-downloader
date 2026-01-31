"""VCR tests for YouTube Music source provider."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.ytmusic import YouTubeMusicProvider


pytestmark = pytest.mark.asyncio


class TestYouTubeMusicSourceProviderVCR:
    """VCR tests for YouTube Music source provider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> YouTubeMusicProvider:
        """Create a YouTube Music provider instance."""
        return YouTubeMusicProvider()

    @pytest.mark.vcr
    async def test_get_track(self, provider: YouTubeMusicProvider) -> None:
        """Test getting a track from YouTube Music."""
        # Using a well-known track
        song = await provider.get_track(
            "https://music.youtube.com/watch?v=gAjR4_CbPpQ"
        )

        assert song.name is not None
        assert len(song.name) > 0
        assert song.platform == Platform.YOUTUBE_MUSIC
        assert song.platform_id == "gAjR4_CbPpQ"
        assert song.duration > 0

    @pytest.mark.vcr
    async def test_search(self, provider: YouTubeMusicProvider) -> None:
        """Test searching for tracks on YouTube Music."""
        songs = await provider.search("Daft Punk Harder Better Faster Stronger", limit=10)

        assert len(songs) > 0
        first_song = songs[0]
        assert first_song.platform == Platform.YOUTUBE_MUSIC
        assert first_song.duration > 0

    @staticmethod
    def test_extract_video_id() -> None:
        """Test extracting video ID from YouTube Music URL."""
        result = YouTubeMusicProvider._extract_video_id(
            "https://music.youtube.com/watch?v=gAjR4_CbPpQ"
        )
        assert result == "gAjR4_CbPpQ"

    @staticmethod
    def test_extract_video_id_with_params() -> None:
        """Test extracting video ID from URL with extra params."""
        result = YouTubeMusicProvider._extract_video_id(
            "https://music.youtube.com/watch?v=gAjR4_CbPpQ&list=RDAMVM"
        )
        assert result == "gAjR4_CbPpQ"

    @staticmethod
    def test_extract_playlist_id() -> None:
        """Test extracting playlist ID from URL."""
        result = YouTubeMusicProvider._extract_playlist_id(
            "https://music.youtube.com/playlist?list=RDCLAK5uy_kmPRjHDECIcuVwnKsx2hzSC5TFJA5"
        )
        assert result == "RDCLAK5uy_kmPRjHDECIcuVwnKsx2hzSC5TFJA5"

    @staticmethod
    def test_extract_channel_id() -> None:
        """Test extracting channel ID from URL."""
        result = YouTubeMusicProvider._extract_channel_id(
            "https://music.youtube.com/channel/UCmDM6zuSTroGZsV9hMG4c4A"
        )
        assert result == "UCmDM6zuSTroGZsV9hMG4c4A"

    @staticmethod
    def test_matches_url() -> None:
        """Test URL matching."""
        assert YouTubeMusicProvider.matches_url(
            "https://music.youtube.com/watch?v=gAjR4_CbPpQ"
        )
        assert YouTubeMusicProvider.matches_url(
            "https://music.youtube.com/playlist?list=RDAMVM"
        )
        assert not YouTubeMusicProvider.matches_url(
            "https://www.youtube.com/watch?v=gAjR4_CbPpQ"
        )

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = YouTubeMusicProvider()
        assert provider.name == "youtube_music"
        assert provider.display_name == "YouTube Music"
