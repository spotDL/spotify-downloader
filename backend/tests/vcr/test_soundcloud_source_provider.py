"""VCR tests for SoundCloud source provider."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.soundcloud import SoundCloudProvider

pytestmark = pytest.mark.asyncio


class TestSoundCloudSourceProviderVCR:
    """VCR tests for SoundCloudProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> SoundCloudProvider:
        """Create a SoundCloud provider instance."""
        return SoundCloudProvider()

    @pytest.mark.skip(reason="SoundCloud removed __sc_hydration track data; provider needs API rewrite")
    @pytest.mark.vcr
    async def test_get_track(self, provider: SoundCloudProvider) -> None:
        """Test getting a track from SoundCloud."""
        song = await provider.get_track("https://soundcloud.com/flaborblanding/flume-holdin-on")
        assert song.name is not None
        assert song.platform == Platform.SOUNDCLOUD
        await provider.close()

    @pytest.mark.skip(reason="SoundCloud removed __sc_hydration track data; provider needs API rewrite")
    @pytest.mark.vcr
    async def test_search(self, provider: SoundCloudProvider) -> None:
        """Test searching for tracks on SoundCloud."""
        songs = await provider.search("Flume Holdin On", limit=5)
        assert len(songs) > 0
        assert songs[0].platform == Platform.SOUNDCLOUD
        await provider.close()

    @staticmethod
    def test_extract_url_info_track() -> None:
        """Test extracting track URL info."""
        result = SoundCloudProvider._extract_url_info("https://soundcloud.com/artist/track-name")
        assert result["user"] == "artist"
        assert result["slug"] == "track-name"
        assert result["type"] == "track"

    @staticmethod
    def test_extract_url_info_playlist() -> None:
        """Test extracting playlist URL info."""
        result = SoundCloudProvider._extract_url_info(
            "https://soundcloud.com/artist/sets/playlist-name"
        )
        assert result["user"] == "artist"
        assert result["slug"] == "playlist-name"
        assert result["type"] == "playlist"

    @staticmethod
    def test_extract_url_info_artist() -> None:
        """Test extracting artist URL info."""
        result = SoundCloudProvider._extract_url_info("https://soundcloud.com/artist/tracks")
        assert result["user"] == "artist"
        assert result["type"] == "artist"

    @staticmethod
    def test_extract_url_info_invalid() -> None:
        """Test extracting info from invalid URL."""
        result = SoundCloudProvider._extract_url_info("https://example.com/track")
        assert result["user"] is None

    @staticmethod
    def test_matches_url() -> None:
        """Test URL matching."""
        assert SoundCloudProvider.matches_url("https://soundcloud.com/artist/track")
        assert SoundCloudProvider.matches_url("https://www.soundcloud.com/user/song")
        assert not SoundCloudProvider.matches_url("https://example.com/track/123")

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = SoundCloudProvider()
        assert provider.name == "soundcloud"
        assert provider.display_name == "SoundCloud"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = SoundCloudProvider()
        await provider.close()
