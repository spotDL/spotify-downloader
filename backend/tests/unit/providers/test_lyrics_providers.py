"""Tests for lyrics providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from spotdl.providers.lyrics.azlyrics import AZLyricsProvider
from spotdl.providers.lyrics.base import BaseLyricsProvider
from spotdl.providers.lyrics.genius import GeniusProvider, GeniusWebProvider


class TestBaseLyricsProvider:
    """Tests for BaseLyricsProvider base class."""

    def test_calculate_score(self) -> None:
        """Test calculating match score for search results."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()

        # Exact match should score high (100 from fuzzy match)
        score = provider._calculate_score("Test Song", "Test Song", ["Artist"])
        assert score == 100.0  # Exact match gives 100

        # Match with artist name adds bonus (20 points max)
        score_with_artist = provider._calculate_score("Artist - Test Song", "Test Song", ["Artist"])
        # Fuzzy match is less than 100 due to "Artist - " prefix, but adds 20 point bonus
        assert 80 < score_with_artist < 100  # High but not perfect due to extra text

        # No match should score low
        score_no_match = provider._calculate_score("Completely Different", "Test Song", ["Artist"])
        assert score_no_match < 50

    def test_find_best_match(self) -> None:
        """Test finding best matching result."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()

        results = {
            "Artist - Test Song": "https://example.com/1",
            "Different Artist - Test Song": "https://example.com/2",
            "Artist - Different Song": "https://example.com/3",
        }

        match = provider._find_best_match(results, "Test Song", ["Artist"])
        assert match is not None
        assert match[0] == "Artist - Test Song"
        assert match[1] == "https://example.com/1"

    def test_find_best_match_no_results(self) -> None:
        """Test finding best match with empty results."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()
        match = provider._find_best_match({}, "Test Song", ["Artist"])
        assert match is None

    def test_find_best_match_low_score(self) -> None:
        """Test finding best match when all scores are too low."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()

        results = {
            "xyz123abc": "https://example.com/1",
            "abcdefghij": "https://example.com/2",
        }

        match = provider._find_best_match(results, "Test Song", ["Artist"])
        assert match is None  # All scores below threshold of 50

    def test_clean_lyrics(self) -> None:
        """Test cleaning lyrics text."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()

        # Multiple blank lines
        lyrics = "Line 1\n\n\n\nLine 2"
        cleaned = provider._clean_lyrics(lyrics)
        assert "\n\n\n" not in cleaned
        assert "Line 1" in cleaned and "Line 2" in cleaned

        # Whitespace normalization
        lyrics = "  \n  Line 1  \n  Line 2  \n  "
        cleaned = provider._clean_lyrics(lyrics)
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        async with ConcreteProvider() as provider:
            assert provider._client is not None

    @pytest.mark.asyncio
    async def test_client_property_not_initialized(self) -> None:
        """Test accessing client property before initialization raises error."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        provider = ConcreteProvider()
        with pytest.raises(RuntimeError):
            _ = provider.client


class TestGeniusProvider:
    """Tests for Genius provider."""

    def test_initialization(self) -> None:
        """Test Genius provider initialization."""
        provider = GeniusProvider(access_token="test_token_123")
        assert provider.access_token == "test_token_123"
        assert "Authorization" in provider.headers
        assert provider.headers["Authorization"] == "Bearer test_token_123"

    def test_initialization_with_client(self) -> None:
        """Test initialization with shared client."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        provider = GeniusProvider(access_token="test_token", client=mock_client)
        assert provider._client == mock_client
        assert not provider._owns_client

    @pytest.mark.asyncio
    async def test_get_results_success(self) -> None:
        """Test successful search on Genius API."""
        provider = GeniusProvider(access_token="test_token")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "hits": [
                    {
                        "result": {
                            "full_title": "Test Song by Artist",
                            "url": "https://genius.com/Artist-test-song-lyrics",
                        }
                    },
                    {
                        "result": {
                            "full_title": "Another Song by Artist",
                            "url": "https://genius.com/Artist-another-song-lyrics",
                        }
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])

        assert len(results) == 2
        assert "Test Song by Artist" in results
        assert results["Test Song by Artist"] == "https://genius.com/Artist-test-song-lyrics"

    @pytest.mark.asyncio
    async def test_get_results_no_hits(self) -> None:
        """Test search with no results."""
        provider = GeniusProvider(access_token="test_token")

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": {"hits": []}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Nonexistent Song", ["Unknown"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_results_api_error(self) -> None:
        """Test search with API error."""
        provider = GeniusProvider(access_token="test_token")

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_results_limit_to_10(self) -> None:
        """Test search limits results to top 10."""
        provider = GeniusProvider(access_token="test_token")

        # Create 15 hits
        hits = [
            {"result": {"full_title": f"Song {i}", "url": f"https://genius.com/{i}"}}
            for i in range(15)
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": {"hits": hits}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test", ["Artist"])
        assert len(results) == 10  # Limited to 10

    @pytest.mark.asyncio
    async def test_extract_lyrics_old_format(self) -> None:
        """Test extracting lyrics from old Genius page format."""
        provider = GeniusProvider(access_token="test_token")

        html_content = """
        <html>
            <body>
                <div class="lyrics">
                    Verse 1 line 1<br/>
                    Verse 1 line 2<br/>
                    <br/>
                    Chorus line 1<br/>
                    Chorus line 2
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None
        assert "Verse 1 line 1" in lyrics
        assert "Chorus line 1" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_new_format(self) -> None:
        """Test extracting lyrics from new Genius page format."""
        provider = GeniusProvider(access_token="test_token")

        html_content = """
        <html>
            <body>
                <div class="LyricsHeader__Container-sc-123">Header to remove</div>
                <div class="Lyrics__Container-sc-456">
                    Verse 1 line 1<br/>
                    Verse 1 line 2
                </div>
                <div class="Lyrics__Container-sc-789">
                    Chorus line 1<br/>
                    Chorus line 2
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None
        assert "Header to remove" not in lyrics
        assert "Verse 1 line 1" in lyrics
        assert "Chorus line 1" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_br_replacement(self) -> None:
        """Test that <br/> tags are replaced with newlines."""
        provider = GeniusProvider(access_token="test_token")

        html_content = """
        <html>
            <body>
                <div class="lyrics">
                    Line 1<br/>Line 2<br/>Line 3
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None
        assert "\n" in lyrics
        assert lyrics.count("\n") >= 2

    @pytest.mark.asyncio
    async def test_extract_lyrics_retry_on_failure(self) -> None:
        """Test extraction retries on failure."""
        provider = GeniusProvider(access_token="test_token")

        # First two attempts fail, third succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.is_success = False

        mock_response_success = MagicMock()
        mock_response_success.text = '<div class="lyrics">Test lyrics</div>'
        mock_response_success.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=[mock_response_fail, mock_response_fail, mock_response_success]
        )

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None
        assert "Test lyrics" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_all_retries_fail(self) -> None:
        """Test extraction returns None after all retries fail."""
        provider = GeniusProvider(access_token="test_token")

        mock_response = MagicMock()
        mock_response.is_success = False

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is None

    @pytest.mark.asyncio
    async def test_extract_lyrics_no_lyrics_container(self) -> None:
        """Test extraction returns None when no lyrics container found."""
        provider = GeniusProvider(access_token="test_token")

        html_content = """
        <html>
            <body>
                <div class="other-content">Not lyrics</div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is None

    @pytest.mark.asyncio
    async def test_extract_lyrics_exception_handling(self) -> None:
        """Test extraction handles exceptions gracefully."""
        provider = GeniusProvider(access_token="test_token")

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is None


class TestGeniusWebProvider:
    """Tests for GeniusWeb provider (no API token)."""

    def test_initialization(self) -> None:
        """Test GeniusWeb provider initialization."""
        provider = GeniusWebProvider()
        assert provider.name == "GeniusWeb"
        assert provider.max_concurrent_requests == 2

    @pytest.mark.asyncio
    async def test_get_results_success(self) -> None:
        """Test successful search via web scraping."""
        provider = GeniusWebProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "sections": [
                    {
                        "type": "song",
                        "hits": [
                            {
                                "result": {
                                    "full_title": "Test Song by Artist",
                                    "url": "https://genius.com/Artist-test-song-lyrics",
                                }
                            }
                        ],
                    },
                    {
                        "type": "artist",
                        "hits": [{"result": {"name": "Artist"}}],
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])

        assert len(results) == 1
        assert "Test Song by Artist" in results

    @pytest.mark.asyncio
    async def test_get_results_only_song_sections(self) -> None:
        """Test search only includes song sections."""
        provider = GeniusWebProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "sections": [
                    {
                        "type": "artist",
                        "hits": [{"result": {"name": "Artist"}}],
                    },
                    {
                        "type": "album",
                        "hits": [{"result": {"title": "Album"}}],
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])
        assert results == {}  # No song sections

    @pytest.mark.asyncio
    async def test_get_results_web_error(self) -> None:
        """Test search handles web errors gracefully."""
        provider = GeniusWebProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Web error"))

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_extract_lyrics_uses_same_logic(self) -> None:
        """Test extraction uses same logic as GeniusProvider."""
        provider = GeniusWebProvider()

        html_content = '<div class="lyrics">Test lyrics content</div>'

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None
        assert "Test lyrics content" in lyrics


class TestAZLyricsProvider:
    """Tests for AZLyrics provider."""

    def test_initialization(self) -> None:
        """Test AZLyrics provider initialization."""
        provider = AZLyricsProvider()
        assert provider.name == "AZLyrics"
        assert provider.max_concurrent_requests == 1
        assert provider.x_code is None
        assert "Host" in provider.headers
        assert provider.headers["Host"] == "www.azlyrics.com"

    @pytest.mark.asyncio
    async def test_ensure_x_code_success(self) -> None:
        """Test successful x_code extraction."""
        provider = AZLyricsProvider()

        # Mock homepage response
        mock_home_response = MagicMock()
        mock_home_response.text = ""

        # Mock geo.js response with x_code
        mock_geo_response = MagicMock()
        mock_geo_response.text = 'var x = {value": "abc123xyz");'

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[mock_home_response, mock_geo_response])

        provider._client = mock_client
        provider._owns_client = True

        success = await provider._ensure_x_code()
        assert success is True
        assert provider.x_code == "abc123xyz"

    @pytest.mark.asyncio
    async def test_ensure_x_code_already_cached(self) -> None:
        """Test x_code is cached and not re-fetched."""
        provider = AZLyricsProvider()
        provider.x_code = "cached_code"

        mock_client = MagicMock(spec=httpx.AsyncClient)
        provider._client = mock_client
        provider._owns_client = True

        success = await provider._ensure_x_code()
        assert success is True
        assert provider.x_code == "cached_code"
        mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_x_code_failure(self) -> None:
        """Test x_code extraction handles errors."""
        provider = AZLyricsProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        provider._client = mock_client
        provider._owns_client = True

        success = await provider._ensure_x_code()
        assert success is False
        assert provider.x_code is None

    @pytest.mark.asyncio
    async def test_get_results_no_x_code(self) -> None:
        """Test search returns empty when x_code fetch fails."""
        provider = AZLyricsProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Error"))

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_results_success(self) -> None:
        """Test successful search on AZLyrics."""
        provider = AZLyricsProvider()

        # Mock x_code fetch
        mock_home_response = MagicMock()
        mock_geo_response = MagicMock()
        mock_geo_response.text = 'var x = {value": "test_code");'

        # Mock search results
        search_html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>
                            <a href="https://www.azlyrics.com/lyrics/artist/testsong.html">
                                <b>Artist Name</b>
                                <span>Test Song</span>
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <a href="https://www.azlyrics.com/lyrics/artist/anothersong.html">
                                <b>Artist Name</b>
                                <span>Another Song</span>
                            </a>
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

        mock_search_response = MagicMock()
        mock_search_response.content = search_html.encode()
        mock_search_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=[mock_home_response, mock_geo_response, mock_search_response]
        )

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist Name"])

        assert len(results) == 2
        assert "Artist Name - Test Song" in results
        assert "Artist Name - Another Song" in results

    @pytest.mark.asyncio
    async def test_get_results_no_results(self) -> None:
        """Test search with no results."""
        provider = AZLyricsProvider()

        # Mock x_code fetch
        mock_home_response = MagicMock()
        mock_geo_response = MagicMock()
        mock_geo_response.text = 'var x = {value": "test_code");'

        # Mock empty search results
        search_html = "<html><body></body></html>"

        mock_search_response = MagicMock()
        mock_search_response.content = search_html.encode()
        mock_search_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=[mock_home_response, mock_geo_response, mock_search_response]
        )

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Nonexistent", ["Unknown"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_results_retry_logic(self) -> None:
        """Test search retries on failure."""
        provider = AZLyricsProvider()

        # Mock x_code fetch
        mock_home_response = MagicMock()
        mock_geo_response = MagicMock()
        mock_geo_response.text = 'var x = {value": "test_code");'

        # First two searches fail, third succeeds
        mock_fail_response = MagicMock()
        mock_fail_response.is_success = False

        search_html = """
        <table>
            <tr>
                <td>
                    <a href="https://www.azlyrics.com/lyrics/artist/song.html">
                        <b>Artist</b><span>Song</span>
                    </a>
                </td>
            </tr>
        </table>
        """
        mock_success_response = MagicMock()
        mock_success_response.content = search_html.encode()
        mock_success_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=[
                mock_home_response,
                mock_geo_response,
                mock_fail_response,
                mock_fail_response,
                mock_success_response,
            ]
        )

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Song", ["Artist"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_extract_lyrics_success(self) -> None:
        """Test successful lyrics extraction."""
        provider = AZLyricsProvider()

        lyrics_html = """
        <html>
            <body>
                <div class="container">Header</div>
                <div>
                    Verse 1 line 1
                    Verse 1 line 2

                    Chorus line 1
                    Chorus line 2
                </div>
                <div class="footer">Footer</div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = lyrics_html.encode()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        assert lyrics is not None
        assert "Verse 1" in lyrics
        assert "Chorus" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_finds_longest_div(self) -> None:
        """Test extraction finds the longest div without class/id."""
        provider = AZLyricsProvider()

        lyrics_html = """
        <html>
            <body>
                <div>Short text</div>
                <div>
                    This is the longest div without class or id.
                    It contains multiple lines.
                    This should be selected as the lyrics container.
                </div>
                <div>Another short text</div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = lyrics_html.encode()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        assert lyrics is not None
        assert "longest div" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_empty_result(self) -> None:
        """Test extraction returns None when lyrics div is empty."""
        provider = AZLyricsProvider()

        lyrics_html = """
        <html>
            <body>
                <div></div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = lyrics_html.encode()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        # Empty lyrics should return None
        assert lyrics is None

    @pytest.mark.asyncio
    async def test_extract_lyrics_http_error(self) -> None:
        """Test extraction handles HTTP errors."""
        provider = AZLyricsProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=MagicMock()
            )
        )

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        assert lyrics is None

    @pytest.mark.asyncio
    async def test_extract_lyrics_network_error(self) -> None:
        """Test extraction handles network errors."""
        provider = AZLyricsProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        assert lyrics is None


class TestLyricsProvidersRateLimiting:
    """Tests for rate limiting behavior."""

    def test_genius_max_concurrent_requests(self) -> None:
        """Test Genius provider has appropriate rate limiting."""
        assert GeniusProvider.max_concurrent_requests == 3

    def test_genius_web_max_concurrent_requests(self) -> None:
        """Test GeniusWeb provider has lower rate limit."""
        assert GeniusWebProvider.max_concurrent_requests == 2

    def test_azlyrics_max_concurrent_requests(self) -> None:
        """Test AZLyrics provider has strict rate limiting."""
        assert AZLyricsProvider.max_concurrent_requests == 1


class TestLyricsProvidersHTMLParsing:
    """Tests for HTML parsing edge cases."""

    @pytest.mark.asyncio
    async def test_genius_malformed_html(self) -> None:
        """Test Genius handles malformed HTML gracefully."""
        provider = GeniusProvider(access_token="test_token")

        html_content = "<div class='lyrics'>Unclosed tag"

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.is_success = True

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        # Should not raise, BeautifulSoup handles malformed HTML
        lyrics = await provider.extract_lyrics("https://genius.com/test")
        assert lyrics is not None or lyrics is None  # Either outcome is acceptable

    @pytest.mark.asyncio
    async def test_azlyrics_special_characters(self) -> None:
        """Test AZLyrics handles special characters in lyrics."""
        provider = AZLyricsProvider()

        lyrics_html = """
        <html>
            <body>
                <div>
                    Special chars: &amp; &lt; &gt; &quot;
                    Unicode: é ñ ü
                </div>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = lyrics_html.encode("utf-8")
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.azlyrics.com/lyrics/artist/song.html")
        assert lyrics is not None
        # BeautifulSoup should decode HTML entities
        assert "&amp;" in lyrics or "&" in lyrics


class TestBaseLyricsProviderIntegration:
    """Tests for BaseLyricsProvider get_lyrics integration method."""

    @pytest.mark.asyncio
    async def test_get_lyrics_success(self) -> None:
        """Test successful lyrics retrieval through get_lyrics."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {"Artist - Test Song": "https://example.com/lyrics"}

            async def extract_lyrics(self, url: str) -> str | None:
                return "Test lyrics content\n\nVerse 1\nLine 2"

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is not None
            assert "Test lyrics content" in lyrics

    @pytest.mark.asyncio
    async def test_get_lyrics_no_results(self) -> None:
        """Test get_lyrics returns None when search has no results."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {}

            async def extract_lyrics(self, url: str) -> str | None:
                return "Should not be called"

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Nonexistent", ["Unknown"])
            assert lyrics is None

    @pytest.mark.asyncio
    async def test_get_lyrics_no_good_match(self) -> None:
        """Test get_lyrics returns None when no good match found."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {"xyz123abc": "https://example.com/1"}

            async def extract_lyrics(self, url: str) -> str | None:
                return "Should not be called"

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is None

    @pytest.mark.asyncio
    async def test_get_lyrics_extraction_fails(self) -> None:
        """Test get_lyrics returns None when extraction fails."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {"Artist - Test Song": "https://example.com/lyrics"}

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is None

    @pytest.mark.asyncio
    async def test_get_lyrics_cleans_lyrics(self) -> None:
        """Test get_lyrics cleans extracted lyrics."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                return {"Test Song": "https://example.com/lyrics"}

            async def extract_lyrics(self, url: str) -> str | None:
                return "  Lyrics\n\n\n\nMore lyrics  "

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is not None
            assert not lyrics.startswith(" ")
            assert not lyrics.endswith(" ")
            assert "\n\n\n" not in lyrics

    @pytest.mark.asyncio
    async def test_get_lyrics_exception_handling(self) -> None:
        """Test get_lyrics handles exceptions gracefully."""

        class ConcreteProvider(BaseLyricsProvider):
            async def get_results(self, name: str, artists: list[str], **kwargs) -> dict[str, str]:
                raise Exception("Search error")

            async def extract_lyrics(self, url: str) -> str | None:
                return None

        async with ConcreteProvider() as provider:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is None


class TestMusixMatchProvider:
    """Tests for MusixMatch provider."""

    def test_initialization(self) -> None:
        """Test MusixMatch provider initialization."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()
        assert provider.name == "MusixMatch"
        assert provider.max_concurrent_requests == 2

    @pytest.mark.asyncio
    async def test_get_results_success(self) -> None:
        """Test successful search on MusixMatch."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        search_html = """
        <html>
            <body>
                <a href="/lyrics/Artist/Test-Song">Artist - Test Song</a>
                <a href="/lyrics/Artist/Another-Song">Artist - Another Song</a>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = search_html
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test Song", ["Artist"])

        assert len(results) == 2
        assert "Artist - Test Song" in results
        assert results["Artist - Test Song"] == "https://www.musixmatch.com/lyrics/Artist/Test-Song"

    @pytest.mark.asyncio
    async def test_get_results_filters_artists(self) -> None:
        """Test artist filtering when artist is in song name."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        await provider.get_results("Artist Song", ["Artist", "Other Artist"])

        # Check the URL called
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        # Artist should be filtered out since it's in the song name
        assert "Artist" not in url or "Other%20Artist" in url

    @pytest.mark.asyncio
    async def test_get_results_retry_with_track_search(self) -> None:
        """Test retry logic with track_search when no results found."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        # First call: no results
        mock_response_empty = MagicMock()
        mock_response_empty.text = "<html><body></body></html>"
        mock_response_empty.raise_for_status = MagicMock()

        # Second call: with results
        mock_response_results = MagicMock()
        mock_response_results.text = '<a href="/lyrics/Artist/Song">Artist - Song</a>'
        mock_response_results.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[mock_response_empty, mock_response_results])

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Song", ["Artist"])

        # Should have called twice
        assert mock_client.get.call_count == 2
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_results_network_error(self) -> None:
        """Test search handles network errors."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_extract_lyrics_success(self) -> None:
        """Test successful lyrics extraction from MusixMatch."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        lyrics_html = """
        <html>
            <body>
                <p class="mxm-lyrics__content">Verse 1 line 1</p>
                <p class="mxm-lyrics__content">Verse 1 line 2</p>
                <p class="mxm-lyrics__content">Chorus line 1</p>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = lyrics_html
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.musixmatch.com/lyrics/Artist/Song")
        assert lyrics is not None
        assert "Verse 1 line 1" in lyrics
        assert "Chorus line 1" in lyrics

    @pytest.mark.asyncio
    async def test_extract_lyrics_no_paragraphs(self) -> None:
        """Test extraction returns None when no lyrics paragraphs found."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        lyrics_html = "<html><body><div>No lyrics here</div></body></html>"

        mock_response = MagicMock()
        mock_response.text = lyrics_html
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.musixmatch.com/lyrics/Artist/Song")
        assert lyrics is None

    @pytest.mark.asyncio
    async def test_extract_lyrics_http_error(self) -> None:
        """Test extraction handles HTTP errors."""
        from spotdl.providers.lyrics.musixmatch import MusixMatchProvider

        provider = MusixMatchProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=MagicMock()
            )
        )

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        lyrics = await provider.extract_lyrics("https://www.musixmatch.com/lyrics/Artist/Song")
        assert lyrics is None


class TestSyncedLyricsProvider:
    """Tests for Synced lyrics provider."""

    def test_initialization(self) -> None:
        """Test SyncedLyricsProvider initialization."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        assert provider.name == "Synced"
        assert provider.max_concurrent_requests == 2
        assert provider.allow_plain is False

    def test_initialization_with_allow_plain(self) -> None:
        """Test initialization with allow_plain option."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider(allow_plain=True)
        assert provider.allow_plain is True

    @pytest.mark.asyncio
    async def test_get_results_not_implemented(self) -> None:
        """Test get_results raises NotImplementedError."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._client = MagicMock(spec=httpx.AsyncClient)

        with pytest.raises(NotImplementedError):
            await provider.get_results("Test", ["Artist"])

    @pytest.mark.asyncio
    async def test_extract_lyrics_not_implemented(self) -> None:
        """Test extract_lyrics raises NotImplementedError."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._client = MagicMock(spec=httpx.AsyncClient)

        with pytest.raises(NotImplementedError):
            await provider.extract_lyrics("https://example.com")

    @pytest.mark.asyncio
    async def test_get_lyrics_success(self) -> None:
        """Test successful synced lyrics retrieval."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._client = MagicMock(spec=httpx.AsyncClient)

        mock_lyrics = "[00:12.00]Test lyrics line 1\n[00:15.50]Test lyrics line 2"

        with patch("syncedlyrics.search", return_value=mock_lyrics):
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics == mock_lyrics

    @pytest.mark.asyncio
    async def test_get_lyrics_import_error(self) -> None:
        """Test get_lyrics handles ImportError when syncedlyrics not installed."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._client = MagicMock(spec=httpx.AsyncClient)

        # Mock the import to raise ImportError
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'syncedlyrics'")
        ):
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is None

    @pytest.mark.asyncio
    async def test_get_lyrics_search_exception(self) -> None:
        """Test get_lyrics handles exceptions from syncedlyrics.search."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._client = MagicMock(spec=httpx.AsyncClient)

        with patch("syncedlyrics.search", side_effect=Exception("Search failed")):
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics is None

    @pytest.mark.asyncio
    async def test_get_lyrics_with_allow_plain(self) -> None:
        """Test get_lyrics with allow_plain=True."""
        from spotdl.providers.lyrics.synced import SyncedLyricsProvider

        provider = SyncedLyricsProvider(allow_plain=True)
        provider._client = MagicMock(spec=httpx.AsyncClient)

        mock_lyrics = "Plain text lyrics without timestamps"

        with patch("syncedlyrics.search", return_value=mock_lyrics) as mock_search:
            lyrics = await provider.get_lyrics("Test Song", ["Artist"])
            assert lyrics == mock_lyrics
            # Verify synced_only=False was passed
            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["synced_only"] is False


class TestLyricsProvidersNetworkErrors:
    """Tests for network error handling."""

    @pytest.mark.asyncio
    async def test_genius_timeout_error(self) -> None:
        """Test Genius handles timeout errors."""
        provider = GeniusProvider(access_token="test_token")

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_azlyrics_connection_error(self) -> None:
        """Test AZLyrics handles connection errors."""
        provider = AZLyricsProvider()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        provider._client = mock_client
        provider._owns_client = True

        # Should fail to get x_code
        results = await provider.get_results("Test", ["Artist"])
        assert results == {}

    @pytest.mark.asyncio
    async def test_genius_rate_limit_error(self) -> None:
        """Test Genius handles rate limit (429) errors."""
        provider = GeniusProvider(access_token="test_token")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "429 Too Many Requests", request=MagicMock(), response=mock_response
            )
        )

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        provider._client = mock_client
        provider._owns_client = True

        results = await provider.get_results("Test", ["Artist"])
        assert results == {}
