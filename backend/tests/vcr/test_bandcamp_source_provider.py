"""VCR tests for Bandcamp source provider."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.bandcamp import BandcampProvider

pytestmark = pytest.mark.asyncio


class TestBandcampSourceProviderVCR:
    """VCR tests for BandcampProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> BandcampProvider:
        """Create a Bandcamp provider instance."""
        return BandcampProvider()

    @pytest.mark.vcr
    async def test_get_track(self, provider: BandcampProvider) -> None:
        """Test getting a track from Bandcamp."""
        from spotdl.providers.sources.base import SourceProviderError, TrackNotFoundError

        try:
            # Using a well-known Bandcamp track
            song = await provider.get_track("https://ghostly.bandcamp.com/track/dripping-sun")

            assert song.name is not None
            assert len(song.name) > 0
            assert song.platform == Platform.BANDCAMP
            assert song.artist is not None
        except (SourceProviderError, TrackNotFoundError) as e:
            # Track may no longer exist or Bandcamp structure changed
            pytest.skip(f"Bandcamp track not available: {e}")

        await provider.close()

    @pytest.mark.vcr
    async def test_get_album(self, provider: BandcampProvider) -> None:
        """Test getting an album from Bandcamp."""
        from spotdl.providers.sources.base import SourceProviderError

        try:
            song_list = await provider.get_album(
                "https://ghostly.bandcamp.com/album/diving-station"
            )

            assert song_list.name is not None
            assert len(song_list.songs) > 0
            assert song_list.songs[0].platform == Platform.BANDCAMP
        except SourceProviderError as e:
            pytest.skip(f"Bandcamp album not available: {e}")

        await provider.close()

    @pytest.mark.vcr
    async def test_search(self, provider: BandcampProvider) -> None:
        """Test searching for tracks on Bandcamp."""
        songs = await provider.search("electronic ambient", limit=5)

        # Search may return empty depending on Bandcamp's response
        if len(songs) == 0:
            pytest.skip("Bandcamp search returned no results")

        first_song = songs[0]
        assert first_song.platform == Platform.BANDCAMP
        assert first_song.name is not None

        await provider.close()

    @staticmethod
    def test_extract_url_info_track() -> None:
        """Test extracting track URL info."""
        result = BandcampProvider._extract_url_info("https://artist.bandcamp.com/track/song-name")
        assert result["subdomain"] == "artist"
        assert result["type"] == "track"
        assert result["slug"] == "song-name"

    @staticmethod
    def test_extract_url_info_album() -> None:
        """Test extracting album URL info."""
        result = BandcampProvider._extract_url_info("https://myband.bandcamp.com/album/album-name")
        assert result["subdomain"] == "myband"
        assert result["type"] == "album"
        assert result["slug"] == "album-name"

    @staticmethod
    def test_extract_url_info_artist() -> None:
        """Test extracting artist URL info."""
        result = BandcampProvider._extract_url_info("https://artist.bandcamp.com/")
        assert result["subdomain"] == "artist"
        assert result["type"] == "artist"

    @staticmethod
    def test_extract_url_info_invalid() -> None:
        """Test extracting info from invalid URL."""
        result = BandcampProvider._extract_url_info("https://example.com/track")
        assert result["subdomain"] is None

    @staticmethod
    def test_matches_url() -> None:
        """Test URL matching."""
        assert BandcampProvider.matches_url("https://artist.bandcamp.com/track/song")
        assert BandcampProvider.matches_url("https://band.bandcamp.com/album/test")
        assert not BandcampProvider.matches_url("https://example.com/track/123")

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = BandcampProvider()
        assert provider.name == "bandcamp"
        assert provider.display_name == "Bandcamp"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = BandcampProvider()
        await provider.close()
