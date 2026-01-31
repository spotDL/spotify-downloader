"""VCR tests for Deezer provider."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.deezer import DeezerProvider


pytestmark = pytest.mark.asyncio


class TestDeezerProviderVCR:
    """VCR tests for DeezerProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> DeezerProvider:
        """Create a Deezer provider instance."""
        return DeezerProvider()

    @pytest.mark.vcr
    async def test_get_track(self, provider: DeezerProvider) -> None:
        """Test getting a track from Deezer."""
        song = await provider.get_track("https://www.deezer.com/track/3135556")

        assert song.name == "Harder, Better, Faster, Stronger"
        assert song.artist == "Daft Punk"
        assert "Daft Punk" in song.artists
        assert song.duration == 226  # Duration from recorded cassette
        assert song.platform == Platform.DEEZER
        assert song.platform_id == "3135556"
        assert song.album_name == "Discovery"
        assert song.year == 2001
        assert song.isrc == "GBDUW0000059"
        assert song.explicit is False

        await provider.close()

    @pytest.mark.vcr
    async def test_search(self, provider: DeezerProvider) -> None:
        """Test searching for tracks on Deezer."""
        songs = await provider.search("Daft Punk Harder Better Faster Stronger", limit=10)

        assert len(songs) > 0
        first_song = songs[0]
        assert first_song.platform == Platform.DEEZER
        # The search should return relevant results
        assert any("Daft Punk" in s.artist or "Daft Punk" in s.artists for s in songs)

        await provider.close()

    @pytest.mark.vcr
    async def test_get_album(self, provider: DeezerProvider) -> None:
        """Test getting an album from Deezer."""
        song_list = await provider.get_album("https://www.deezer.com/album/302127")

        assert song_list.name == "Discovery"
        assert len(song_list.songs) > 0
        assert song_list.songs[0].platform == Platform.DEEZER
        assert song_list.songs[0].album_name == "Discovery"

        await provider.close()

    async def test_extract_id_track(self) -> None:
        """Test extracting track ID from URL."""
        result = DeezerProvider._extract_id("https://www.deezer.com/track/3135556")
        assert result == ("track", "3135556")

    async def test_extract_id_album(self) -> None:
        """Test extracting album ID from URL."""
        result = DeezerProvider._extract_id("https://www.deezer.com/album/302127")
        assert result == ("album", "302127")

    async def test_extract_id_with_locale(self) -> None:
        """Test extracting ID from URL with locale."""
        result = DeezerProvider._extract_id("https://www.deezer.com/en/track/3135556")
        assert result == ("track", "3135556")

    async def test_extract_id_playlist(self) -> None:
        """Test extracting playlist ID from URL."""
        result = DeezerProvider._extract_id("https://www.deezer.com/playlist/908622995")
        assert result == ("playlist", "908622995")

    async def test_extract_id_artist(self) -> None:
        """Test extracting artist ID from URL."""
        result = DeezerProvider._extract_id("https://www.deezer.com/artist/27")
        assert result == ("artist", "27")

    async def test_extract_id_invalid(self) -> None:
        """Test extracting ID from invalid URL."""
        result = DeezerProvider._extract_id("https://example.com/track/123")
        assert result is None

    async def test_matches_url(self) -> None:
        """Test URL matching."""
        assert DeezerProvider.matches_url("https://www.deezer.com/track/3135556")
        assert DeezerProvider.matches_url("https://deezer.com/album/302127")
        assert DeezerProvider.matches_url("https://www.deezer.com/en/playlist/908622995")
        assert not DeezerProvider.matches_url("https://example.com/track/123")

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = DeezerProvider()
        assert provider.name == "deezer"
        assert provider.display_name == "Deezer"
