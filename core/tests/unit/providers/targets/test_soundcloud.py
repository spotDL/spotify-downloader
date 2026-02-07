"""Unit tests for SoundCloud target provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from spotdl_core.providers.targets.base import SearchError
from spotdl_core.providers.targets.soundcloud import (
    SOUNDCLOUD_URL_PATTERN,
    SoundCloudProvider,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestSoundCloudProvider:
    """Test SoundCloudProvider class."""

    @pytest.fixture
    def provider(self) -> SoundCloudProvider:
        """Create a SoundCloud provider instance."""
        return SoundCloudProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing."""
        return Song(
            name="Test Track",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    @pytest.fixture
    def mock_track_data(self) -> dict:
        """Create mock SoundCloud track data."""
        return {
            "id": 12345678,
            "title": "Test Track",
            "kind": "track",
            "user": {
                "username": "Test Artist",
                "avatar_url": "https://example.com/avatar.jpg",
            },
            "duration": 180000,  # milliseconds
            "artwork_url": "https://example.com/artwork-large.jpg",
            "permalink_url": "https://soundcloud.com/testartist/test-track",
            "playback_count": 10000,
        }

    def test_initialization(self, provider: SoundCloudProvider):
        """Test provider initialization."""
        assert provider.name == "soundcloud"
        assert provider.display_name == "SoundCloud"
        assert provider._timeout == 30.0
        assert provider._client is None

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        provider = SoundCloudProvider(timeout=60.0)
        assert provider._timeout == 60.0

    @pytest.mark.asyncio
    async def test_get_client(self, provider: SoundCloudProvider):
        """Test HTTP client creation."""
        client = await provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Second call should return same client
        client2 = await provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_get_client_recreates_if_closed(self, provider: SoundCloudProvider):
        """Test that client is recreated if closed."""
        client1 = await provider._get_client()
        await client1.aclose()

        client2 = await provider._get_client()
        assert client2 is not client1
        assert not client2.is_closed

    @pytest.mark.asyncio
    async def test_close(self, provider: SoundCloudProvider):
        """Test closing the provider."""
        client = await provider._get_client()
        assert not client.is_closed

        await provider.close()
        assert client.is_closed
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, provider: SoundCloudProvider):
        """Test closing without creating client."""
        await provider.close()  # Should not raise

    def test_extract_hydration_data_success(self, provider: SoundCloudProvider):
        """Test extracting hydration data from SoundCloud page."""
        html = """
        <html>
            <script>
                window.__sc_hydration = [
                    {"hydratable": "playlist", "data": {"id": 1}},
                    {"hydratable": "sound", "data": {"id": 2}}
                ];
            </script>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")
        hydration_data = provider._extract_hydration_data(soup)

        assert len(hydration_data) == 2
        assert hydration_data[0]["hydratable"] == "playlist"
        assert hydration_data[1]["hydratable"] == "sound"

    def test_extract_hydration_data_not_found(self, provider: SoundCloudProvider):
        """Test extracting hydration data when not found."""
        html = "<html><body>No hydration data</body></html>"
        soup = BeautifulSoup(html, "lxml")
        hydration_data = provider._extract_hydration_data(soup)

        assert hydration_data == []

    def test_extract_hydration_data_invalid_json(self, provider: SoundCloudProvider):
        """Test extracting hydration data with invalid JSON."""
        html = """
        <html>
            <script>
                window.__sc_hydration = [invalid json];
            </script>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")
        hydration_data = provider._extract_hydration_data(soup)

        assert hydration_data == []

    def test_track_to_result_full_data(
        self, provider: SoundCloudProvider, mock_track_data: dict
    ):
        """Test converting SoundCloud track to Result with full data."""
        result = provider._track_to_result(mock_track_data)

        assert isinstance(result, Result)
        assert result.name == "Test Track"
        assert result.artist == "Test Artist"
        assert result.artists == ("Test Artist",)
        assert result.duration == 180
        assert result.platform == TargetPlatform.SOUNDCLOUD
        assert result.platform_id == "12345678"
        assert result.url == "https://soundcloud.com/testartist/test-track"
        assert result.views == 10000
        assert "t500x500" in result.cover_url

    def test_track_to_result_minimal_data(self, provider: SoundCloudProvider):
        """Test converting track with minimal data."""
        track = {
            "id": 123,
            "title": "Test",
        }
        result = provider._track_to_result(track)

        assert result.name == "Test"
        assert result.artist == "Unknown"
        assert result.duration == 0
        assert result.platform_id == "123"

    def test_track_to_result_no_artwork_uses_avatar(
        self, provider: SoundCloudProvider
    ):
        """Test that avatar is used when no artwork."""
        track = {
            "id": 123,
            "title": "Test",
            "user": {"username": "Artist", "avatar_url": "https://example.com/avatar.jpg"},
        }
        result = provider._track_to_result(track)
        assert result.cover_url == "https://example.com/avatar.jpg"

    def test_track_to_result_duration_milliseconds(self, provider: SoundCloudProvider):
        """Test duration conversion from milliseconds."""
        track = {
            "id": 123,
            "title": "Test",
            "duration": 3500,  # 3.5 seconds in ms
        }
        result = provider._track_to_result(track)
        assert result.duration == 3

    def test_track_to_result_duration_zero(self, provider: SoundCloudProvider):
        """Test duration when zero or missing."""
        track = {
            "id": 123,
            "title": "Test",
            "duration": 0,
        }
        result = provider._track_to_result(track)
        assert result.duration == 0

    def test_track_to_result_artwork_url_replacement(
        self, provider: SoundCloudProvider
    ):
        """Test that -large. is replaced with -t500x500. in artwork URL."""
        track = {
            "id": 123,
            "title": "Test",
            "artwork_url": "https://example.com/image-large.jpg",
        }
        result = provider._track_to_result(track)
        assert result.cover_url == "https://example.com/image-t500x500.jpg"

    @pytest.mark.asyncio
    async def test_search_success(
        self,
        provider: SoundCloudProvider,
        sample_song: Song,
        mock_track_data: dict,
    ):
        """Test successful search."""
        import json

        track_json = json.dumps(mock_track_data)
        html = f"""
        <html>
            <script>
                window.__sc_hydration = [
                    {{"hydratable": "search", "data": {{
                        "collection": [{track_json}]
                    }}}}
                ];
            </script>
        </html>
        """

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=10)

            assert len(results) == 1
            assert results[0].name == "Test Track"
            assert results[0].platform == TargetPlatform.SOUNDCLOUD

    @pytest.mark.asyncio
    async def test_search_filters_non_tracks(
        self, provider: SoundCloudProvider, sample_song: Song
    ):
        """Test that non-track results are filtered out."""
        html = """
        <html>
            <script>
                window.__sc_hydration = [
                    {"hydratable": "search", "data": {
                        "collection": [
                            {"kind": "playlist", "id": 1},
                            {"kind": "track", "id": 2, "title": "Track"},
                            {"kind": "user", "id": 3}
                        ]
                    }}
                ];
            </script>
        </html>
        """

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song)

            assert len(results) == 1
            assert results[0].platform_id == "2"

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, provider: SoundCloudProvider, sample_song: Song
    ):
        """Test that search respects limit parameter."""
        import json

        tracks = [
            {"kind": "track", "id": i, "title": f"Track {i}"} for i in range(20)
        ]

        tracks_json = json.dumps(tracks)
        html = f"""
        <html>
            <script>
                window.__sc_hydration = [
                    {{"hydratable": "search", "data": {{"collection": {tracks_json}}}}}
                ];
            </script>
        </html>
        """

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            results = await provider.search(sample_song, limit=5)

            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_http_error(
        self, provider: SoundCloudProvider, sample_song: Song
    ):
        """Test search with HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="SoundCloud search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_search_generic_error(
        self, provider: SoundCloudProvider, sample_song: Song
    ):
        """Test search with generic error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Generic error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="SoundCloud search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_get_track_info_success(
        self, provider: SoundCloudProvider, mock_track_data: dict
    ):
        """Test getting track info successfully."""
        import json

        track_json = json.dumps(mock_track_data)
        html = f"""
        <html>
            <script>
                window.__sc_hydration = [
                    {{"hydratable": "sound", "data": {track_json}}}
                ];
            </script>
        </html>
        """

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_track_info(
                "https://soundcloud.com/artist/track"
            )

            assert result is not None
            assert result.name == "Test Track"
            assert result.platform_id == "12345678"

    @pytest.mark.asyncio
    async def test_get_track_info_not_found(self, provider: SoundCloudProvider):
        """Test getting track info when not found."""
        html = "<html><body>No track data</body></html>"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_track_info(
                "https://soundcloud.com/artist/track"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_track_info_error(self, provider: SoundCloudProvider):
        """Test getting track info with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_track_info(
                "https://soundcloud.com/artist/track"
            )
            assert result is None

    def test_extract_track_info_success(self):
        """Test extracting track info from URL."""
        url = "https://soundcloud.com/testartist/test-track"
        info = SoundCloudProvider.extract_track_info(url)

        assert info is not None
        assert info == ("testartist", "test-track")

    def test_extract_track_info_with_query_params(self):
        """Test extracting track info from URL with query params."""
        url = "https://soundcloud.com/testartist/test-track?in=artist/sets"
        info = SoundCloudProvider.extract_track_info(url)

        assert info is not None
        assert info == ("testartist", "test-track")

    def test_extract_track_info_no_protocol(self):
        """Test extracting track info from URL without protocol."""
        url = "soundcloud.com/testartist/test-track"
        info = SoundCloudProvider.extract_track_info(url)

        assert info is not None
        assert info == ("testartist", "test-track")

    def test_extract_track_info_invalid_url(self):
        """Test extracting track info from invalid URL."""
        url = "https://www.example.com/track"
        info = SoundCloudProvider.extract_track_info(url)
        assert info is None

    def test_extract_track_info_empty_string(self):
        """Test extracting track info from empty string."""
        info = SoundCloudProvider.extract_track_info("")
        assert info is None

    def test_soundcloud_url_pattern(self):
        """Test SoundCloud URL regex pattern."""
        valid_urls = [
            ("https://soundcloud.com/artist/track", "artist", "track"),
            ("https://www.soundcloud.com/artist/track", "artist", "track"),
            ("http://soundcloud.com/artist/track", "artist", "track"),
            ("soundcloud.com/test-artist/test-track", "test-artist", "test-track"),
        ]

        for url, expected_artist, expected_track in valid_urls:
            match = SOUNDCLOUD_URL_PATTERN.search(url)
            assert match is not None, f"Failed to match: {url}"
            assert match.group(1) == expected_artist
            assert match.group(2) == expected_track

    def test_soundcloud_url_pattern_invalid(self):
        """Test SoundCloud URL pattern with invalid URLs."""
        invalid_urls = [
            "https://bandcamp.com/artist/track",
            "https://soundcloud.com/artist",  # Missing track
            "not a url",
            "",
        ]

        for url in invalid_urls:
            match = SOUNDCLOUD_URL_PATTERN.search(url)
            assert match is None, f"Should not match: {url}"
