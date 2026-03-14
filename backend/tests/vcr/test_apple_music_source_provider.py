"""VCR tests for Apple Music source provider."""

import pytest

from spotdl.core.types.song import Platform
from spotdl.providers.sources.apple_music import AppleMusicProvider

pytestmark = pytest.mark.asyncio


class TestAppleMusicSourceProviderVCR:
    """VCR tests for AppleMusicProvider with recorded HTTP responses."""

    @pytest.fixture
    def provider(self) -> AppleMusicProvider:
        """Create an Apple Music provider instance."""
        return AppleMusicProvider()

    @pytest.mark.skip(reason="Apple Music uses SPA with JS rendering; no JSON-LD in server response")
    @pytest.mark.vcr
    async def test_get_track(self, provider: AppleMusicProvider) -> None:
        """Test getting a track from Apple Music."""
        song = await provider.get_track(
            "https://music.apple.com/us/album/harder-better-faster-stronger/697194953?i=697195203"
        )
        assert song.name is not None
        assert song.platform == Platform.APPLE_MUSIC
        await provider.close()

    @pytest.mark.skip(reason="Apple Music uses SPA with JS rendering; no JSON-LD in server response")
    @pytest.mark.vcr
    async def test_get_album(self, provider: AppleMusicProvider) -> None:
        """Test getting an album from Apple Music."""
        song_list = await provider.get_album(
            "https://music.apple.com/us/album/discovery/697194953"
        )
        assert song_list.name is not None
        assert len(song_list.songs) > 0
        await provider.close()

    @pytest.mark.vcr
    async def test_search(self, provider: AppleMusicProvider) -> None:
        """Test searching for tracks on Apple Music (uses iTunes API)."""
        songs = await provider.search("Daft Punk Harder Better Faster Stronger", limit=5)

        assert len(songs) > 0
        first_song = songs[0]
        assert first_song.platform == Platform.APPLE_MUSIC
        assert first_song.name is not None

        await provider.close()

    @staticmethod
    def test_extract_url_info_track() -> None:
        """Test extracting track URL info."""
        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/album/harder-better-faster-stronger/697194953?i=697195203"
        )
        assert result["country"] == "us"
        assert result["type"] == "track"  # When ?i= is present, type is "track"
        assert result["id"] == "697194953"
        assert result["track_id"] == "697195203"

    @staticmethod
    def test_extract_url_info_album() -> None:
        """Test extracting album URL info."""
        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/album/discovery/697194953"
        )
        assert result["country"] == "us"
        assert result["type"] == "album"
        assert result["id"] == "697194953"
        assert result["track_id"] is None

    @staticmethod
    def test_extract_url_info_playlist() -> None:
        """Test extracting playlist URL info."""
        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/playlist/todays-hits/1234567890"
        )
        assert result["country"] == "us"
        assert result["type"] == "playlist"
        assert result["id"] == "1234567890"

    @staticmethod
    def test_extract_url_info_artist() -> None:
        """Test extracting artist URL info."""
        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/artist/daft-punk/5468295"
        )
        assert result["country"] == "us"
        assert result["type"] == "artist"
        assert result["id"] == "5468295"

    @staticmethod
    def test_extract_url_info_different_country() -> None:
        """Test extracting URL info with different country."""
        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/gb/album/discovery/697194953"
        )
        assert result["country"] == "gb"
        assert result["type"] == "album"
        assert result["id"] == "697194953"

    @staticmethod
    def test_extract_url_info_invalid() -> None:
        """Test extracting info from invalid URL."""
        result = AppleMusicProvider._extract_url_info("https://example.com/track/123")
        assert result["country"] is None
        assert result["type"] is None

    @staticmethod
    def test_matches_url() -> None:
        """Test URL matching."""
        assert AppleMusicProvider.matches_url(
            "https://music.apple.com/us/album/discovery/697194953"
        )
        assert AppleMusicProvider.matches_url(
            "https://music.apple.com/us/album/track-name/697194953?i=697195203"
        )
        assert AppleMusicProvider.matches_url(
            "https://music.apple.com/gb/playlist/my-playlist/1234567890"
        )
        assert not AppleMusicProvider.matches_url("https://example.com/track/123")

    async def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = AppleMusicProvider()
        assert provider.name == "apple_music"
        assert provider.display_name == "Apple Music"

    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = AppleMusicProvider()
        await provider.close()
