"""Additional tests for source providers (Apple Music, SoundCloud, Tidal, Bandcamp)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from spotdl_core.providers.sources.apple_music import AppleMusicProvider
from spotdl_core.providers.sources.soundcloud import SoundCloudProvider
from spotdl_core.providers.sources.tidal import TidalProvider
from spotdl_core.providers.sources.bandcamp import BandcampProvider
from spotdl_core.providers.sources.base import InvalidURLError, SourceProviderError
from spotdl_core.types import Platform, Song


class TestAppleMusicProvider:
    """Test AppleMusicProvider class."""

    @pytest.fixture
    def provider(self) -> AppleMusicProvider:
        """Create an Apple Music provider."""
        return AppleMusicProvider()

    def test_provider_init(self, provider: AppleMusicProvider):
        """Test provider initialization."""
        assert provider.name == "apple_music"
        assert provider.display_name == "Apple Music"
        assert len(provider.url_patterns) == 2

    def test_extract_url_info_album(self, provider: AppleMusicProvider):
        """Test extracting album URL info."""
        info = provider._extract_url_info("https://music.apple.com/us/album/test/123456")
        assert info["country"] == "us"
        assert info["type"] == "album"
        assert info["id"] == "123456"

    def test_extract_url_info_track(self, provider: AppleMusicProvider):
        """Test extracting track URL info."""
        info = provider._extract_url_info("https://music.apple.com/us/album/test/123?i=456")
        assert info["country"] == "us"
        assert info["type"] == "track"
        assert info["track_id"] == "456"

    def test_extract_url_info_no_match(self, provider: AppleMusicProvider):
        """Test extracting URL info with no match."""
        info = provider._extract_url_info("https://invalid.com/album/123")
        assert info["country"] is None

    @patch("httpx.AsyncClient")
    async def test_get_track_invalid_url(self, mock_client, provider: AppleMusicProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://invalid.com/track/123")

    @patch("httpx.AsyncClient")
    async def test_get_album_invalid_url(self, mock_client, provider: AppleMusicProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://invalid.com/album/123")

    @patch("httpx.AsyncClient")
    async def test_search_exception(self, mock_client, provider: AppleMusicProvider):
        """Test search with exception."""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = httpx.HTTPError("Error")
        provider._client = mock_async_client

        results = await provider.search("test")
        assert results == []

    async def test_close(self, provider: AppleMusicProvider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()


class TestSoundCloudProvider:
    """Test SoundCloudProvider class."""

    @pytest.fixture
    def provider(self) -> SoundCloudProvider:
        """Create a SoundCloud provider."""
        return SoundCloudProvider()

    def test_provider_init(self, provider: SoundCloudProvider):
        """Test provider initialization."""
        assert provider.name == "soundcloud"
        assert provider.display_name == "SoundCloud"
        assert len(provider.url_patterns) == 2

    def test_extract_url_info_track(self, provider: SoundCloudProvider):
        """Test extracting track URL info."""
        info = provider._extract_url_info("https://soundcloud.com/artist/track-name")
        assert info["user"] == "artist"
        assert info["slug"] == "track-name"
        assert info["type"] == "track"

    def test_extract_url_info_playlist(self, provider: SoundCloudProvider):
        """Test extracting playlist URL info."""
        info = provider._extract_url_info("https://soundcloud.com/artist/sets/playlist")
        assert info["user"] == "artist"
        assert info["slug"] == "playlist"
        assert info["type"] == "playlist"

    def test_extract_url_info_artist(self, provider: SoundCloudProvider):
        """Test extracting artist URL info."""
        info = provider._extract_url_info("https://soundcloud.com/artist")
        assert info["user"] == "artist"
        assert info["slug"] is None
        assert info["type"] == "artist"

    def test_extract_url_info_no_match(self, provider: SoundCloudProvider):
        """Test extracting URL info with no match."""
        info = provider._extract_url_info("https://invalid.com")
        assert info["user"] is None

    @patch("httpx.AsyncClient")
    async def test_get_track_invalid_url(self, mock_client, provider: SoundCloudProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://invalid.com/track")

    @patch("httpx.AsyncClient")
    async def test_search_exception(self, mock_client, provider: SoundCloudProvider):
        """Test search returns empty list on exception."""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = httpx.HTTPError("Error")
        provider._client = mock_async_client

        results = await provider.search("test")
        assert results == []

    async def test_close(self, provider: SoundCloudProvider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()


class TestTidalProvider:
    """Test TidalProvider class."""

    @pytest.fixture
    def provider(self) -> TidalProvider:
        """Create a Tidal provider."""
        return TidalProvider()

    def test_provider_init(self, provider: TidalProvider):
        """Test provider initialization."""
        assert provider.name == "tidal"
        assert provider.display_name == "Tidal"
        assert len(provider.url_patterns) == 2

    def test_extract_id_track(self, provider: TidalProvider):
        """Test extracting track ID."""
        result = provider._extract_id("https://tidal.com/browse/track/123456")
        assert result == ("track", "123456")

    def test_extract_id_album(self, provider: TidalProvider):
        """Test extracting album ID."""
        result = provider._extract_id("https://listen.tidal.com/album/789")
        assert result == ("album", "789")

    def test_extract_id_no_match(self, provider: TidalProvider):
        """Test extracting ID with no match."""
        result = provider._extract_id("https://invalid.com/track/123")
        assert result is None

    @patch("httpx.AsyncClient")
    async def test_get_track_invalid_url(self, mock_client, provider: TidalProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://invalid.com/track/123")

    @patch("httpx.AsyncClient")
    async def test_get_album_invalid_url(self, mock_client, provider: TidalProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://invalid.com/album/123")

    @patch("httpx.AsyncClient")
    async def test_search_exception(self, mock_client, provider: TidalProvider):
        """Test search with exception."""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = httpx.HTTPError("Error")
        provider._client = mock_async_client

        results = await provider.search("test")
        assert results == []

    async def test_close(self, provider: TidalProvider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()


class TestBandcampProvider:
    """Test BandcampProvider class."""

    @pytest.fixture
    def provider(self) -> BandcampProvider:
        """Create a Bandcamp provider."""
        return BandcampProvider()

    def test_provider_init(self, provider: BandcampProvider):
        """Test provider initialization."""
        assert provider.name == "bandcamp"
        assert provider.display_name == "Bandcamp"
        assert len(provider.url_patterns) == 2

    def test_extract_url_info_track(self, provider: BandcampProvider):
        """Test extracting track URL info."""
        info = provider._extract_url_info("https://artist.bandcamp.com/track/song-name")
        assert info["subdomain"] == "artist"
        assert info["type"] == "track"
        assert info["slug"] == "song-name"

    def test_extract_url_info_album(self, provider: BandcampProvider):
        """Test extracting album URL info."""
        info = provider._extract_url_info("https://artist.bandcamp.com/album/album-name")
        assert info["subdomain"] == "artist"
        assert info["type"] == "album"
        assert info["slug"] == "album-name"

    def test_extract_url_info_artist(self, provider: BandcampProvider):
        """Test extracting artist URL info."""
        info = provider._extract_url_info("https://artist.bandcamp.com/")
        assert info["subdomain"] == "artist"
        assert info["type"] == "artist"

    def test_extract_url_info_no_match(self, provider: BandcampProvider):
        """Test extracting URL info with no match."""
        info = provider._extract_url_info("https://invalid.com")
        assert info["subdomain"] is None

    @patch("httpx.AsyncClient")
    async def test_get_track_invalid_url(self, mock_client, provider: BandcampProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://invalid.com/track")

    @patch("httpx.AsyncClient")
    async def test_get_album_invalid_url(self, mock_client, provider: BandcampProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://invalid.com/album")

    @patch("httpx.AsyncClient")
    async def test_search_exception(self, mock_client, provider: BandcampProvider):
        """Test search with exception."""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = httpx.HTTPError("Error")
        provider._client = mock_async_client

        results = await provider.search("test")
        assert results == []

    async def test_close(self, provider: BandcampProvider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client
        await provider.close()
        mock_client.aclose.assert_called_once()
