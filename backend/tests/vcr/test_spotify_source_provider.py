"""VCR tests for Spotify source provider."""

import os

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.spotify import SpotifyProvider


pytestmark = pytest.mark.asyncio


class TestSpotifySourceProviderVCR:
    """VCR tests for SpotifyProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> SpotifyProvider:
        """Create a Spotify provider instance.

        Uses environment variables for credentials if available,
        otherwise falls back to None (will fail if no cassette exists).
        """
        return SpotifyProvider(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
        )

    @pytest.mark.vcr
    async def test_get_track(self, provider: SpotifyProvider) -> None:
        """Test getting a track from Spotify."""
        from spotdl.providers.sources.base import SourceProviderError
        from spotipy.oauth2 import SpotifyOauthError

        try:
            song = await provider.get_track(
                "https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV"
            )

            assert song.name == "Harder, Better, Faster, Stronger"
            assert song.artist == "Daft Punk"
            assert "Daft Punk" in song.artists
            assert song.platform == Platform.SPOTIFY
            assert song.platform_id == "0DiWol3AO6WpXZgp0goxAV"
            assert song.album_name == "Discovery"
            assert song.duration > 0
        except (SourceProviderError, SpotifyOauthError) as e:
            pytest.skip(f"Spotify credentials not available: {e}")

    @pytest.mark.vcr
    async def test_get_album(self, provider: SpotifyProvider) -> None:
        """Test getting an album from Spotify."""
        from spotdl.providers.sources.base import SourceProviderError
        from spotipy.oauth2 import SpotifyOauthError

        try:
            song_list = await provider.get_album(
                "https://open.spotify.com/album/2noRn2Aes5aoNVsU6iWThc"
            )

            assert song_list.name == "Discovery"
            assert len(song_list.songs) > 0
            assert song_list.songs[0].platform == Platform.SPOTIFY
            assert song_list.songs[0].album_name == "Discovery"
        except (SourceProviderError, SpotifyOauthError) as e:
            pytest.skip(f"Spotify credentials not available: {e}")

    @pytest.mark.vcr
    async def test_search(self, provider: SpotifyProvider) -> None:
        """Test searching for tracks on Spotify."""
        from spotdl.providers.sources.base import SourceProviderError
        from spotipy.oauth2 import SpotifyOauthError

        try:
            songs = await provider.search("Daft Punk Harder Better Faster Stronger", limit=5)

            assert len(songs) > 0
            first_song = songs[0]
            assert first_song.platform == Platform.SPOTIFY
            # The search should return relevant results
            assert any("Daft Punk" in s.artist or "Daft Punk" in s.artists for s in songs)
        except (SourceProviderError, SpotifyOauthError) as e:
            pytest.skip(f"Spotify credentials not available: {e}")

    @staticmethod
    def test_extract_id_track() -> None:
        """Test extracting track ID from URL."""
        result = SpotifyProvider._extract_id(
            "https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV"
        )
        assert result == ("track", "0DiWol3AO6WpXZgp0goxAV")

    @staticmethod
    def test_extract_id_album() -> None:
        """Test extracting album ID from URL."""
        result = SpotifyProvider._extract_id(
            "https://open.spotify.com/album/2noRn2Aes5aoNVsU6iWThc"
        )
        assert result == ("album", "2noRn2Aes5aoNVsU6iWThc")

    @staticmethod
    def test_extract_id_playlist() -> None:
        """Test extracting playlist ID from URL."""
        result = SpotifyProvider._extract_id(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )
        assert result == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")

    @staticmethod
    def test_extract_id_artist() -> None:
        """Test extracting artist ID from URL."""
        result = SpotifyProvider._extract_id(
            "https://open.spotify.com/artist/4tZwfgrHOc3mvqYlEYSvVi"
        )
        assert result == ("artist", "4tZwfgrHOc3mvqYlEYSvVi")

    @staticmethod
    def test_extract_id_with_intl() -> None:
        """Test extracting ID from URL with intl prefix."""
        result = SpotifyProvider._extract_id(
            "https://open.spotify.com/intl-de/track/0DiWol3AO6WpXZgp0goxAV"
        )
        assert result == ("track", "0DiWol3AO6WpXZgp0goxAV")

    @staticmethod
    def test_extract_id_uri() -> None:
        """Test extracting ID from Spotify URI."""
        result = SpotifyProvider._extract_id("spotify:track:0DiWol3AO6WpXZgp0goxAV")
        assert result == ("track", "0DiWol3AO6WpXZgp0goxAV")

    @staticmethod
    def test_extract_id_invalid() -> None:
        """Test extracting ID from invalid URL."""
        from spotdl.providers.sources.base import InvalidURLError

        with pytest.raises(InvalidURLError):
            SpotifyProvider._extract_id("https://example.com/track/123")

    @staticmethod
    def test_matches_url() -> None:
        """Test URL matching."""
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV"
        )
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/intl-de/album/2noRn2Aes5aoNVsU6iWThc"
        )
        assert SpotifyProvider.matches_url("spotify:track:0DiWol3AO6WpXZgp0goxAV")
        assert not SpotifyProvider.matches_url("https://example.com/track/123")

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = SpotifyProvider()
        assert provider.name == "spotify"
        assert provider.display_name == "Spotify"

    async def test_provider_init_without_credentials(self) -> None:
        """Test provider initialization without credentials."""
        # Provider can be created without credentials
        provider = SpotifyProvider()
        assert provider._client is None
        assert provider._client_id is None
        assert provider._client_secret is None
