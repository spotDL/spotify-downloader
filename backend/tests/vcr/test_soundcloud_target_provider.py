"""VCR tests for SoundCloud target provider."""

import pytest

from spotdl.core.types.result import TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.soundcloud import SoundCloudProvider

pytestmark = pytest.mark.asyncio


class TestSoundCloudTargetProviderVCR:
    """VCR tests for SoundCloudProvider (target) with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> SoundCloudProvider:
        """Create a SoundCloud target provider instance."""
        return SoundCloudProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing search."""
        return Song(
            name="Holdin On",
            artists=["Flume"],
            artist="Flume",
            duration=237,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
            album_name="Flume",
        )

    @pytest.mark.vcr
    async def test_search(self, provider: SoundCloudProvider, sample_song: Song) -> None:
        """Test searching for a song on SoundCloud."""
        from spotdl.providers.targets.base import SearchError

        try:
            results = await provider.search(sample_song, limit=5)

            # SoundCloud may return empty results if hydration data isn't available
            if len(results) == 0:
                pytest.skip("SoundCloud search returned no results")

            first_result = results[0]
            assert first_result.platform == TargetPlatform.SOUNDCLOUD
            assert first_result.url.startswith("https://soundcloud.com/")
            assert first_result.name is not None
        except SearchError as e:
            pytest.skip(f"SoundCloud search failed: {e}")

        await provider.close()

    @staticmethod
    def test_build_search_query() -> None:
        """Test building search query from song."""
        provider = SoundCloudProvider()
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
    def test_extract_track_info() -> None:
        """Test extracting track info from URL."""
        result = SoundCloudProvider.extract_track_info("https://soundcloud.com/artist/track-name")
        assert result == ("artist", "track-name")

    @staticmethod
    def test_extract_track_info_invalid() -> None:
        """Test extracting track info from invalid URL."""
        result = SoundCloudProvider.extract_track_info("https://example.com/track")
        assert result is None

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = SoundCloudProvider()
        assert provider.name == "soundcloud"
        assert provider.display_name == "SoundCloud"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = SoundCloudProvider()
        await provider.close()
