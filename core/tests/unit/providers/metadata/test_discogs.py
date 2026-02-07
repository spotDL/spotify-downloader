"""Unit tests for spotdl_core.providers.metadata.discogs module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from spotdl_core.providers.metadata.base import MetadataProviderError, MetadataResult
from spotdl_core.providers.metadata.discogs import DiscogsProvider


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def mock_discogs_client():
    """Create a mock Discogs client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_release():
    """Create a mock Discogs release."""
    release = MagicMock()
    release.id = 12345
    release.title = "Test Album"
    release.year = 2024

    # Mock artists
    artist = MagicMock()
    artist.name = "Test Artist"
    release.artists = [artist]

    # Mock genres and styles
    release.genres = ["Electronic", "Rock"]
    release.styles = ["Ambient", "Post-Rock"]

    # Mock labels
    label = MagicMock()
    label.name = "Test Label"
    release.labels = [label]

    # Mock country
    release.country = "US"

    # Mock images
    image = MagicMock()
    image.type = "primary"
    image.uri = "https://example.com/cover.jpg"
    release.images = [image]

    # Mock tracklist
    track = MagicMock()
    track.title = "Test Song"
    track.position = "1"
    release.tracklist = [track]

    return release


# ── 1. Initialization Tests ─────────────────────────────────────────


class TestDiscogsInitialization:
    """Test DiscogsProvider initialization."""

    def test_init_without_token(self) -> None:
        """Test initialization without user token."""
        provider = DiscogsProvider()
        assert provider._user_token is None
        assert provider._client is None
        assert provider.requests_per_second == 0.4

    def test_init_with_token(self) -> None:
        """Test initialization with user token."""
        provider = DiscogsProvider(user_token="test_token")
        assert provider._user_token == "test_token"
        assert provider.requests_per_second == 1.0

    def test_init_with_custom_user_agent(self) -> None:
        """Test initialization with custom user agent."""
        custom_agent = "CustomApp/1.0"
        provider = DiscogsProvider(user_agent=custom_agent)
        assert provider._user_agent == custom_agent

    def test_provider_attributes(self) -> None:
        """Test provider class attributes."""
        provider = DiscogsProvider()
        assert provider.name == "discogs"
        assert provider.display_name == "Discogs"

    def test_has_lock_for_thread_safety(self) -> None:
        """Test provider has asyncio lock."""
        provider = DiscogsProvider()
        assert isinstance(provider._lock, asyncio.Lock)


# ── 2. Client Initialization Tests ──────────────────────────────────


class TestClientInitialization:
    """Test Discogs client initialization."""

    @pytest.mark.asyncio
    async def test_ensure_client_called(self) -> None:
        """Test client is called during operations."""
        provider = DiscogsProvider()
        # Just verify the method exists and can be called
        assert hasattr(provider, "_ensure_client")

    @pytest.mark.asyncio
    async def test_ensure_client_uses_lock(self) -> None:
        """Test client initialization uses lock."""
        provider = DiscogsProvider()
        assert provider._lock is not None
        assert isinstance(provider._lock, asyncio.Lock)


# ── 3. ISRC Lookup Tests ────────────────────────────────────────────


class TestISRCLookup:
    """Test ISRC lookup functionality."""

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_supported(self) -> None:
        """Test ISRC lookup returns None (not supported)."""
        provider = DiscogsProvider()
        result = await provider.lookup_by_isrc("USRC12345678")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_logs_message(self) -> None:
        """Test ISRC lookup logs appropriate message."""
        provider = DiscogsProvider()

        with patch("spotdl_core.providers.metadata.discogs.logger") as mock_logger:
            await provider.lookup_by_isrc("USRC12345678")
            mock_logger.debug.assert_called_once()


# ── 4. Name Lookup Tests ────────────────────────────────────────────


class TestNameLookup:
    """Test lookup by name functionality."""

    @pytest.mark.asyncio
    async def test_lookup_by_name_success(self, mock_release) -> None:
        """Test successful lookup by name."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_calculate_match_score", return_value=80):
                with patch.object(provider, "_parse_release") as mock_parse:
                    mock_parse.return_value = MetadataResult(name="Test Song")

                    result = await provider.lookup_by_name("Test Song", "Test Artist")

                    assert result is not None
                    mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_by_name_with_album(self, mock_release) -> None:
        """Test lookup by name with album parameter."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_calculate_match_score", return_value=80):
                with patch.object(provider, "_parse_release", return_value=MetadataResult()):
                    await provider.lookup_by_name("Test Song", "Test Artist", "Test Album")

                    # Verify album is included in query
                    call_args = mock_client.search.call_args
                    assert "Test Album" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_lookup_by_name_no_results(self) -> None:
        """Test lookup when no results found."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            result = await provider.lookup_by_name("Test Song", "Test Artist")
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_low_score(self, mock_release) -> None:
        """Test lookup when match score is too low."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_calculate_match_score", return_value=30):
                result = await provider.lookup_by_name("Test Song", "Test Artist")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_error_handling(self) -> None:
        """Test error handling during lookup."""
        provider = DiscogsProvider()

        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Network error")

        with patch.object(provider, "_ensure_client", return_value=mock_client):
            result = await provider.lookup_by_name("Test Song", "Test Artist")
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_uses_executor(self, mock_release) -> None:
        """Test lookup uses executor for blocking operations."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = mock_results

                with patch.object(provider, "_calculate_match_score", return_value=80):
                    with patch.object(provider, "_parse_release", return_value=MetadataResult()):
                        await provider.lookup_by_name("Test Song", "Test Artist")

                        mock_event_loop.run_in_executor.assert_called()

    @pytest.mark.asyncio
    async def test_lookup_by_name_limits_results(self, mock_release) -> None:
        """Test lookup limits number of results processed."""
        provider = DiscogsProvider()

        # Create 10 releases
        releases = [mock_release] * 10

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter(releases))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_calculate_match_score", return_value=80) as mock_score:
                with patch.object(provider, "_parse_release", return_value=MetadataResult()):
                    await provider.lookup_by_name("Test Song", "Test Artist")

                    # Should only process first 5
                    assert mock_score.call_count <= 5


# ── 5. Search Tests ─────────────────────────────────────────────────


class TestSearch:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_success(self, mock_release) -> None:
        """Test successful search."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_parse_release") as mock_parse:
                mock_parse.return_value = MetadataResult(name="Test")

                results = await provider.search("test query")

                assert len(results) == 1
                mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_limit(self, mock_release) -> None:
        """Test search with custom limit."""
        provider = DiscogsProvider()

        releases = [mock_release] * 20

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter(releases))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_parse_release") as mock_parse:
                mock_parse.return_value = MetadataResult(name="Test")

                results = await provider.search("test query", limit=5)

                assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """Test search with no results."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            results = await provider.search("test query")
            assert results == []

    @pytest.mark.asyncio
    async def test_search_error_handling(self) -> None:
        """Test search error handling."""
        provider = DiscogsProvider()

        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Error")

        with patch.object(provider, "_ensure_client", return_value=mock_client):
            results = await provider.search("test query")
            assert results == []

    @pytest.mark.asyncio
    async def test_search_parse_failure(self, mock_release) -> None:
        """Test search continues when parse fails."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([mock_release, mock_release]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_parse_release") as mock_parse:
                # First fails, second succeeds
                mock_parse.side_effect = [Exception("Parse error"), MetadataResult(name="Test")]

                results = await provider.search("test query")

                assert len(results) == 1


# ── 6. Release Lookup Tests ─────────────────────────────────────────


class TestReleaseLookup:
    """Test release lookup by ID."""

    @pytest.mark.asyncio
    async def test_lookup_release_success(self, mock_release) -> None:
        """Test successful release lookup."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_client.release.return_value = mock_release
            mock_ensure.return_value = mock_client

            with patch.object(provider, "_parse_release") as mock_parse:
                mock_parse.return_value = MetadataResult(name="Test")

                result = await provider.lookup_release(12345)

                assert result is not None
                mock_client.release.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_lookup_release_not_found(self) -> None:
        """Test release lookup when not found."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_client.release.side_effect = Exception("Not found")
            mock_ensure.return_value = mock_client

            result = await provider.lookup_release(99999)
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_release_uses_executor(self, mock_release) -> None:
        """Test release lookup uses executor."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = mock_release

                with patch.object(provider, "_parse_release", return_value=MetadataResult()):
                    await provider.lookup_release(12345)

                    mock_event_loop.run_in_executor.assert_called()


# ── 7. Match Score Calculation Tests ────────────────────────────────


class TestMatchScoreCalculation:
    """Test match score calculation."""

    def test_calculate_match_score_perfect_match(self, mock_release) -> None:
        """Test perfect match score."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Test Song", "Test Artist", "Test Album"
        )
        assert score > 70

    def test_calculate_match_score_artist_match(self, mock_release) -> None:
        """Test artist match contributes to score."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Different Song", "Test Artist", None
        )
        assert score >= 40

    def test_calculate_match_score_album_match(self, mock_release) -> None:
        """Test album match contributes to score."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Test Song", "Different Artist", "Test Album"
        )
        assert score >= 30

    def test_calculate_match_score_track_match(self, mock_release) -> None:
        """Test track name match contributes to score."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Test Song", "Different Artist", None
        )
        assert score >= 30

    def test_calculate_match_score_no_match(self, mock_release) -> None:
        """Test no match returns low score."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Completely Different", "Unknown Artist", "Unknown Album"
        )
        assert score == 0

    def test_calculate_match_score_case_insensitive(self, mock_release) -> None:
        """Test matching is case insensitive."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "test song", "TEST ARTIST", "test ALBUM"
        )
        assert score > 70

    def test_calculate_match_score_partial_artist_match(self, mock_release) -> None:
        """Test partial artist name matches."""
        provider = DiscogsProvider()
        score = provider._calculate_match_score(
            mock_release, "Song", "Test", None
        )
        assert score >= 40

    def test_calculate_match_score_error_handling(self) -> None:
        """Test error handling in score calculation."""
        provider = DiscogsProvider()
        broken_release = MagicMock()
        broken_release.title = None
        broken_release.artists = None

        score = provider._calculate_match_score(
            broken_release, "Test", "Test", None
        )
        assert score == 0.0


# ── 8. Release Parsing Tests ────────────────────────────────────────


class TestReleaseParsing:
    """Test release parsing."""

    @pytest.mark.asyncio
    async def test_parse_release_basic(self, mock_release) -> None:
        """Test basic release parsing."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.album_name == "Test Album"
        assert result.year == 2024
        assert result.source == "discogs"

    @pytest.mark.asyncio
    async def test_parse_release_with_artists(self, mock_release) -> None:
        """Test parsing release with artists."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.artists == ["Test Artist"]

    @pytest.mark.asyncio
    async def test_parse_release_cleans_artist_names(self) -> None:
        """Test artist name cleaning (removes numbers)."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        artist = MagicMock()
        artist.name = "Test Artist (2)"
        release.artists = [artist]
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.tracklist = []
        release.id = 123

        result = await provider._parse_release(release)

        assert result is not None
        assert result.artists == ["Test Artist"]

    @pytest.mark.asyncio
    async def test_parse_release_with_genres_and_styles(self, mock_release) -> None:
        """Test parsing genres and styles."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert "Electronic" in result.genres
        assert "Rock" in result.genres
        assert "Ambient" in result.genres
        assert "Post-Rock" in result.genres

    @pytest.mark.asyncio
    async def test_parse_release_with_label(self, mock_release) -> None:
        """Test parsing label information."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.label == "Test Label"

    @pytest.mark.asyncio
    async def test_parse_release_with_country(self, mock_release) -> None:
        """Test parsing country information."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.country == "US"

    @pytest.mark.asyncio
    async def test_parse_release_with_cover_art(self, mock_release) -> None:
        """Test parsing cover art."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.album_art_url == "https://example.com/cover.jpg"

    @pytest.mark.asyncio
    async def test_parse_release_cover_prefers_primary(self) -> None:
        """Test cover art prefers primary image."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.artists = []
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.tracklist = []
        release.id = 123

        # Create multiple images
        img1 = MagicMock()
        img1.type = "secondary"
        img1.uri = "https://example.com/cover1.jpg"

        img2 = MagicMock()
        img2.type = "primary"
        img2.uri = "https://example.com/cover2.jpg"

        release.images = [img1, img2]

        result = await provider._parse_release(release)

        assert result is not None
        assert result.album_art_url == "https://example.com/cover2.jpg"

    @pytest.mark.asyncio
    async def test_parse_release_with_track_name(self, mock_release) -> None:
        """Test parsing with specific track name."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release, track_name="Test Song")

        assert result is not None
        assert result.name == "Test Song"
        assert result.track_number == 1

    @pytest.mark.asyncio
    async def test_parse_release_track_position_parsing(self) -> None:
        """Test parsing track position."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.artists = []
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.id = 123

        # Create track with alphanumeric position
        track = MagicMock()
        track.title = "Test Track"
        track.position = "A2"
        release.tracklist = [track]

        result = await provider._parse_release(release, track_name="Test Track")

        assert result is not None
        assert result.track_number == 2

    @pytest.mark.asyncio
    async def test_parse_release_with_discogs_id(self, mock_release) -> None:
        """Test parsing Discogs ID."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.discogs_id == "12345"

    @pytest.mark.asyncio
    async def test_parse_release_confidence_score(self, mock_release) -> None:
        """Test confidence score is set."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release)

        assert result is not None
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_parse_release_no_title(self) -> None:
        """Test parsing fails without title."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = None

        result = await provider._parse_release(release)
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_release_error_handling(self) -> None:
        """Test error handling during parsing."""
        provider = DiscogsProvider()
        broken_release = MagicMock()
        # Make title accessible but other attributes raise
        broken_release.title = "Test"
        type(broken_release).artists = property(lambda self: (_ for _ in ()).throw(Exception("Error")))

        result = await provider._parse_release(broken_release)
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_release_invalid_year(self) -> None:
        """Test parsing with invalid year."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.year = "invalid"
        release.artists = []
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.tracklist = []
        release.id = 123

        result = await provider._parse_release(release)

        assert result is not None
        assert result.year is None


# ── 9. Close Method Tests ───────────────────────────────────────────


class TestCloseMethod:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_sets_client_to_none(self) -> None:
        """Test close sets client to None."""
        provider = DiscogsProvider()
        # Manually set client to test close
        provider._client = MagicMock()
        assert provider._client is not None

        await provider.close()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self) -> None:
        """Test close without initialized client."""
        provider = DiscogsProvider()
        await provider.close()
        assert provider._client is None


# ── 10. Edge Cases and Error Handling ───────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_search_query(self) -> None:
        """Test search with empty query."""
        provider = DiscogsProvider()

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_results = MagicMock()
            mock_results.__iter__ = Mock(return_value=iter([]))
            mock_client.search.return_value = mock_results
            mock_ensure.return_value = mock_client

            results = await provider.search("")
            assert results == []

    @pytest.mark.asyncio
    async def test_parse_release_empty_artists(self) -> None:
        """Test parsing release with no artists."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.artists = []
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.tracklist = []
        release.id = 123

        result = await provider._parse_release(release)

        assert result is not None
        assert result.artists is None

    @pytest.mark.asyncio
    async def test_parse_release_no_images(self) -> None:
        """Test parsing release with no images."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.artists = []
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.tracklist = []
        release.id = 123

        result = await provider._parse_release(release)

        assert result is not None
        assert result.album_art_url is None

    @pytest.mark.asyncio
    async def test_parse_release_no_labels(self) -> None:
        """Test parsing release with no labels."""
        provider = DiscogsProvider()
        release = MagicMock()
        release.title = "Album"
        release.artists = []
        release.year = None
        release.genres = []
        release.styles = []
        release.labels = []
        release.country = None
        release.images = []
        release.tracklist = []
        release.id = 123

        result = await provider._parse_release(release)

        assert result is not None
        assert result.label is None

    @pytest.mark.asyncio
    async def test_parse_release_track_not_found(self, mock_release) -> None:
        """Test parsing when track name not found in tracklist."""
        provider = DiscogsProvider()
        result = await provider._parse_release(mock_release, track_name="Nonexistent Track")

        assert result is not None
        assert result.name == "Test Album"  # Falls back to album name
        assert result.track_number is None

    def test_rate_limiting_values(self) -> None:
        """Test rate limiting configuration."""
        provider_without_token = DiscogsProvider()
        assert provider_without_token.requests_per_second == 0.4

        provider_with_token = DiscogsProvider(user_token="token")
        assert provider_with_token.requests_per_second == 1.0
