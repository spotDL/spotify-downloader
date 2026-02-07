"""Unit tests for Bandcamp target provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from spotdl_core.providers.targets.base import SearchError
from spotdl_core.providers.targets.bandcamp import (
    BANDCAMP_URL_PATTERN,
    BandcampProvider,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class TestBandcampProvider:
    """Test BandcampProvider class."""

    @pytest.fixture
    def provider(self) -> BandcampProvider:
        """Create a Bandcamp provider instance."""
        return BandcampProvider()

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

    def test_initialization(self, provider: BandcampProvider):
        """Test provider initialization."""
        assert provider.name == "bandcamp"
        assert provider.display_name == "Bandcamp"
        assert provider._timeout == 30.0
        assert provider._client is None

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        provider = BandcampProvider(timeout=60.0)
        assert provider._timeout == 60.0

    @pytest.mark.asyncio
    async def test_get_client(self, provider: BandcampProvider):
        """Test HTTP client creation."""
        client = await provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Second call should return same client
        client2 = await provider._get_client()
        assert client2 is client

    @pytest.mark.asyncio
    async def test_get_client_recreates_if_closed(self, provider: BandcampProvider):
        """Test that client is recreated if closed."""
        client1 = await provider._get_client()
        await client1.aclose()

        client2 = await provider._get_client()
        assert client2 is not client1
        assert not client2.is_closed

    @pytest.mark.asyncio
    async def test_close(self, provider: BandcampProvider):
        """Test closing the provider."""
        client = await provider._get_client()
        assert not client.is_closed

        await provider.close()
        assert client.is_closed
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, provider: BandcampProvider):
        """Test closing without creating client."""
        await provider.close()  # Should not raise

    def test_parse_search_result_full_data(self, provider: BandcampProvider):
        """Test parsing search result with full data."""
        html = """
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/track/test-track">
                <img src="https://example.com/image_10.jpg" />
            </a>
            <div class="heading">Test Track</div>
            <div class="subhead">album by Test Artist from Test Album</div>
        </li>
        """
        soup = BeautifulSoup(html, "lxml")
        elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(elem)

        assert result is not None
        assert result.name == "Test Track"
        assert result.artist == "Test Artist"
        assert result.artists == ("Test Artist",)
        assert result.album_name == "Test Album"
        assert result.platform == TargetPlatform.BANDCAMP
        assert result.url == "https://artist.bandcamp.com/track/test-track"
        assert result.duration == 0  # Duration not available in search

    def test_parse_search_result_artist_no_album(self, provider: BandcampProvider):
        """Test parsing search result with artist but no album."""
        html = """
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/track/test-track"></a>
            <div class="heading">Test Track</div>
            <div class="subhead">album by Test Artist</div>
        </li>
        """
        soup = BeautifulSoup(html, "lxml")
        elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(elem)

        assert result is not None
        assert result.artist == "Test Artist"
        assert result.album_name == ""

    def test_parse_search_result_no_link(self, provider: BandcampProvider):
        """Test parsing search result without link."""
        html = """
        <li class="searchresult">
            <div class="heading">Test Track</div>
        </li>
        """
        soup = BeautifulSoup(html, "lxml")
        elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(elem)
        assert result is None

    def test_parse_search_result_not_track(self, provider: BandcampProvider):
        """Test parsing search result that's not a track."""
        html = """
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/album/test-album"></a>
            <div class="heading">Test Album</div>
        </li>
        """
        soup = BeautifulSoup(html, "lxml")
        elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(elem)
        assert result is None  # Should filter out albums

    def test_parse_search_result_image_resolution_upgrade(
        self, provider: BandcampProvider
    ):
        """Test that image resolution is upgraded."""
        html = """
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/track/test">
                <img src="https://example.com/image_9.jpg" />
            </a>
            <div class="heading">Test</div>
            <div class="subhead">by Artist</div>
        </li>
        """
        soup = BeautifulSoup(html, "lxml")
        elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(elem)

        assert result is not None
        assert result.cover_url == "https://example.com/image_10.jpg"

    def test_parse_search_result_exception_handling(self, provider: BandcampProvider):
        """Test that exceptions in parsing return None."""
        # Create malformed HTML that will cause parsing errors
        soup = BeautifulSoup("<li></li>", "lxml")
        elem = soup.find("li")

        result = provider._parse_search_result(elem)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_success(
        self, provider: BandcampProvider, sample_song: Song
    ):
        """Test successful search."""
        html = """
        <html>
            <body>
                <ul>
                    <li class="searchresult">
                        <a class="artcont" href="https://artist.bandcamp.com/track/test">
                            <img src="https://example.com/image_10.jpg" />
                        </a>
                        <div class="heading">Test Track</div>
                        <div class="subhead">by Test Artist</div>
                    </li>
                </ul>
            </body>
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
            assert results[0].platform == TargetPlatform.BANDCAMP

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, provider: BandcampProvider, sample_song: Song
    ):
        """Test that search respects limit parameter."""
        # Create HTML with 10 results
        results_html = "".join(
            [
                f"""
            <li class="searchresult">
                <a class="artcont" href="https://artist.bandcamp.com/track/test{i}"></a>
                <div class="heading">Track {i}</div>
                <div class="subhead">by Artist</div>
            </li>
            """
                for i in range(10)
            ]
        )
        html = f"<html><body><ul>{results_html}</ul></body></html>"

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
        self, provider: BandcampProvider, sample_song: Song
    ):
        """Test search with HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="Bandcamp search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_search_generic_error(
        self, provider: BandcampProvider, sample_song: Song
    ):
        """Test search with generic error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Generic error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(SearchError, match="Bandcamp search failed"):
                await provider.search(sample_song)

    @pytest.mark.asyncio
    async def test_get_track_info_success(self, provider: BandcampProvider):
        """Test getting track info successfully."""
        html = """
        <html>
            <script>
                var TralbumData = {
                    "artist": "Test Artist",
                    "current": {"title": "Test Album"},
                    "art_id": 12345,
                    "trackinfo": [{
                        "id": 67890,
                        "title": "Test Track",
                        "duration": 180
                    }]
                };
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
                "https://artist.bandcamp.com/track/test"
            )

            assert result is not None
            assert result.name == "Test Track"
            assert result.artist == "Test Artist"
            assert result.album_name == "Test Album"
            assert result.duration == 180
            assert result.platform_id == "67890"
            assert "a12345_10.jpg" in result.cover_url

    @pytest.mark.asyncio
    async def test_get_track_info_no_art_id(self, provider: BandcampProvider):
        """Test getting track info without art_id."""
        html = """
        <html>
            <script>
                var TralbumData = {
                    "artist": "Test Artist",
                    "trackinfo": [{
                        "id": 67890,
                        "title": "Test Track",
                        "duration": 180
                    }]
                };
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
                "https://artist.bandcamp.com/track/test"
            )

            assert result is not None
            assert result.cover_url is None

    @pytest.mark.asyncio
    async def test_get_track_info_not_found(self, provider: BandcampProvider):
        """Test getting track info when not found."""
        html = "<html><body>No track data</body></html>"

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_track_info(
                "https://artist.bandcamp.com/track/test"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_track_info_error(self, provider: BandcampProvider):
        """Test getting track info with error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Error")

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.get_track_info(
                "https://artist.bandcamp.com/track/test"
            )
            assert result is None

    def test_extract_url_info_track(self):
        """Test extracting info from track URL."""
        url = "https://testartist.bandcamp.com/track/test-track"
        info = BandcampProvider.extract_url_info(url)

        assert info is not None
        assert info["subdomain"] == "testartist"
        assert info["type"] == "track"
        assert info["slug"] == "test-track"

    def test_extract_url_info_album(self):
        """Test extracting info from album URL."""
        url = "https://testartist.bandcamp.com/album/test-album"
        info = BandcampProvider.extract_url_info(url)

        assert info is not None
        assert info["subdomain"] == "testartist"
        assert info["type"] == "album"
        assert info["slug"] == "test-album"

    def test_extract_url_info_no_protocol(self):
        """Test extracting info from URL without protocol."""
        url = "testartist.bandcamp.com/track/test-track"
        info = BandcampProvider.extract_url_info(url)

        assert info is not None
        assert info["subdomain"] == "testartist"

    def test_extract_url_info_with_query_params(self):
        """Test extracting info from URL with query params."""
        url = "https://testartist.bandcamp.com/track/test-track?from=search"
        info = BandcampProvider.extract_url_info(url)

        assert info is not None
        assert info["slug"] == "test-track"

    def test_extract_url_info_invalid_url(self):
        """Test extracting info from invalid URL."""
        url = "https://www.example.com/track"
        info = BandcampProvider.extract_url_info(url)
        assert info is None

    def test_extract_url_info_empty_string(self):
        """Test extracting info from empty string."""
        info = BandcampProvider.extract_url_info("")
        assert info is None

    def test_bandcamp_url_pattern(self):
        """Test Bandcamp URL regex pattern."""
        valid_urls = [
            (
                "https://testartist.bandcamp.com/track/test-track",
                "testartist",
                "track",
                "test-track",
            ),
            (
                "http://artist.bandcamp.com/album/test-album",
                "artist",
                "album",
                "test-album",
            ),
            (
                "artist.bandcamp.com/track/song",
                "artist",
                "track",
                "song",
            ),
        ]

        for url, expected_subdomain, expected_type, expected_slug in valid_urls:
            match = BANDCAMP_URL_PATTERN.search(url)
            assert match is not None, f"Failed to match: {url}"
            assert match.group(1) == expected_subdomain
            assert match.group(2) == expected_type
            assert match.group(3) == expected_slug

    def test_bandcamp_url_pattern_invalid(self):
        """Test Bandcamp URL pattern with invalid URLs."""
        invalid_urls = [
            "https://bandcamp.com",  # No subdomain
            "https://artist.bandcamp.com",  # No type/slug
            "https://soundcloud.com/artist/track",
            "not a url",
            "",
        ]

        for url in invalid_urls:
            match = BANDCAMP_URL_PATTERN.search(url)
            assert match is None, f"Should not match: {url}"
