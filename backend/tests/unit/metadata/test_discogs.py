"""Tests for Discogs metadata provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from spotdl.providers.metadata.discogs import DiscogsProvider


# Create mock discogs_client module for testing
@pytest.fixture(autouse=True)
def mock_discogs_client():
    """Mock the discogs_client module."""
    mock_dc = MagicMock()
    mock_dc.Client = MagicMock()

    with patch.dict(sys.modules, {"discogs_client": mock_dc}):
        yield mock_dc


class TestDiscogsProviderInit:
    """Tests for DiscogsProvider initialization."""

    def test_default_init(self) -> None:
        """Test default initialization (unauthenticated)."""
        provider = DiscogsProvider()
        assert provider.name == "discogs"
        assert provider.display_name == "Discogs"
        assert provider.requests_per_second == 0.4  # 25/min unauthenticated
        assert provider._user_token is None
        assert provider._client is None

    def test_authenticated_init(self) -> None:
        """Test initialization with user token."""
        provider = DiscogsProvider(user_token="test_token")
        assert provider._user_token == "test_token"
        assert provider.requests_per_second == 1.0  # 60/min authenticated

    def test_custom_user_agent(self) -> None:
        """Test initialization with custom user agent."""
        provider = DiscogsProvider(user_agent="custom_agent/1.0")
        assert provider._user_agent == "custom_agent/1.0"


class TestDiscogsProviderClient:
    """Tests for Discogs client initialization."""

    @pytest.fixture
    def provider(self) -> DiscogsProvider:
        """Create a provider for testing."""
        return DiscogsProvider()

    @pytest.mark.asyncio
    async def test_ensure_client_creates_client(
        self, provider: DiscogsProvider, mock_discogs_client: MagicMock
    ) -> None:
        """Test client is created on first use."""
        mock_client = MagicMock()
        mock_discogs_client.Client.return_value = mock_client

        client = await provider._ensure_client()

        assert client == mock_client
        mock_discogs_client.Client.assert_called_once_with(
            provider._user_agent,
            user_token=None,
        )

    @pytest.mark.asyncio
    async def test_ensure_client_reuses_client(
        self, provider: DiscogsProvider, mock_discogs_client: MagicMock
    ) -> None:
        """Test client is reused on subsequent calls."""
        mock_client = MagicMock()
        provider._client = mock_client

        client = await provider._ensure_client()

        assert client == mock_client

    @pytest.mark.asyncio
    async def test_ensure_client_with_token(self, mock_discogs_client: MagicMock) -> None:
        """Test client is created with token when provided."""
        provider = DiscogsProvider(user_token="my_token")
        mock_client = MagicMock()
        mock_discogs_client.Client.return_value = mock_client

        await provider._ensure_client()

        mock_discogs_client.Client.assert_called_once_with(
            provider._user_agent,
            user_token="my_token",
        )


class TestDiscogsProviderLookup:
    """Tests for DiscogsProvider lookup methods."""

    @pytest.fixture
    def provider(self) -> DiscogsProvider:
        """Create a provider for testing."""
        return DiscogsProvider()

    @pytest.fixture
    def mock_release(self) -> MagicMock:
        """Create a mock Discogs release."""
        release = MagicMock()
        release.id = 12345
        release.title = "Test Album"
        release.year = 2020

        # Mock artists
        artist = MagicMock()
        artist.name = "Test Artist (2)"  # Discogs format with disambiguation
        release.artists = [artist]

        # Mock genres and styles
        release.genres = ["Rock", "Electronic"]
        release.styles = ["Indie Rock", "Synth-pop"]

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
        track.title = "Test Track"
        track.position = "A1"
        release.tracklist = [track]

        return release

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_supported(self, provider: DiscogsProvider) -> None:
        """Test ISRC lookup returns None (not supported by Discogs)."""
        result = await provider.lookup_by_isrc("USRC17607839")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_found(
        self, provider: DiscogsProvider, mock_release: MagicMock
    ) -> None:
        """Test name lookup when release is found."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client

            # Mock search results
            mock_client.search.return_value = iter([mock_release])

            result = await provider.lookup_by_name(
                track_name="Test Track",
                artist_name="Test Artist",
                album_name="Test Album",
            )

            assert result is not None
            assert result.source == "discogs"

    @pytest.mark.asyncio
    async def test_lookup_by_name_not_found(self, provider: DiscogsProvider) -> None:
        """Test name lookup when no release found."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client

            # Mock empty search results
            mock_client.search.return_value = iter([])

            result = await provider.lookup_by_name(
                track_name="Unknown Track",
                artist_name="Unknown Artist",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_error(self, provider: DiscogsProvider) -> None:
        """Test name lookup handles errors gracefully."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client
            mock_client.search.side_effect = Exception("API Error")

            result = await provider.lookup_by_name(
                track_name="Test Track",
                artist_name="Test Artist",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_search(self, provider: DiscogsProvider, mock_release: MagicMock) -> None:
        """Test search returns results."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client

            # Mock search results with multiple releases
            mock_client.search.return_value = iter([mock_release, mock_release])

            results = await provider.search("test query", limit=5)

            assert len(results) == 2
            assert all(r.source == "discogs" for r in results)

    @pytest.mark.asyncio
    async def test_search_error(self, provider: DiscogsProvider) -> None:
        """Test search handles errors gracefully."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client
            mock_client.search.side_effect = Exception("API Error")

            results = await provider.search("test query")
            assert results == []


class TestDiscogsProviderParsing:
    """Tests for DiscogsProvider parsing methods."""

    @pytest.fixture
    def provider(self) -> DiscogsProvider:
        """Create a provider for testing."""
        return DiscogsProvider()

    @pytest.mark.asyncio
    async def test_parse_release_full(self, provider: DiscogsProvider) -> None:
        """Test parsing a complete release."""
        release = MagicMock()
        release.id = 99999
        release.title = "Great Album"
        release.year = 2022

        # Artists with Discogs disambiguation format
        artist1 = MagicMock()
        artist1.name = "Band Name (3)"
        artist2 = MagicMock()
        artist2.name = "Solo Artist"
        release.artists = [artist1, artist2]

        release.genres = ["Pop"]
        release.styles = ["Dance-pop"]

        label = MagicMock()
        label.name = "Major Label"
        release.labels = [label]

        release.country = "UK"

        # Primary image
        img = MagicMock()
        img.type = "primary"
        img.uri = "https://img.discogs.com/cover.jpg"
        release.images = [img]

        # Tracklist
        track1 = MagicMock()
        track1.title = "First Song"
        track1.position = "1"
        track2 = MagicMock()
        track2.title = "Second Song"
        track2.position = "2"
        release.tracklist = [track1, track2]

        result = await provider._parse_release(release, track_name="First Song")

        assert result is not None
        assert result.name == "First Song"
        assert result.album_name == "Great Album"
        assert result.artists == ["Band Name", "Solo Artist"]  # Cleaned
        assert result.discogs_id == "99999"
        assert result.year == 2022
        assert "Pop" in result.genres
        assert "Dance-pop" in result.genres
        assert result.label == "Major Label"
        assert result.country == "UK"
        assert result.album_art_url == "https://img.discogs.com/cover.jpg"
        assert result.track_number == 1

    @pytest.mark.asyncio
    async def test_parse_release_no_track_name(self, provider: DiscogsProvider) -> None:
        """Test parsing release without track name uses album title."""
        release = MagicMock()
        release.id = 12345
        release.title = "Album Title"
        release.year = 2021
        release.artists = []
        release.genres = None
        release.styles = None
        release.labels = None
        release.country = None
        release.images = None
        release.tracklist = []

        result = await provider._parse_release(release)

        assert result is not None
        assert result.name == "Album Title"
        assert result.album_name == "Album Title"

    @pytest.mark.asyncio
    async def test_parse_release_no_title(self, provider: DiscogsProvider) -> None:
        """Test parsing release without title returns None."""
        release = MagicMock()
        release.title = None
        release.id = 12345

        result = await provider._parse_release(release)
        assert result is None

    def test_calculate_match_score_perfect(self, provider: DiscogsProvider) -> None:
        """Test match score calculation for perfect match."""
        release = MagicMock()
        release.title = "Test Album"

        artist = MagicMock()
        artist.name = "Test Artist"
        release.artists = [artist]

        track = MagicMock()
        track.title = "Test Track"
        release.tracklist = [track]

        score = provider._calculate_match_score(
            release,
            track_name="Test Track",
            artist_name="Test Artist",
            album_name="Test Album",
        )

        assert score == 100  # 40 (artist) + 30 (album) + 30 (track)

    def test_calculate_match_score_partial(self, provider: DiscogsProvider) -> None:
        """Test match score calculation for partial match."""
        release = MagicMock()
        release.title = "Different Album"

        artist = MagicMock()
        artist.name = "Test Artist"
        release.artists = [artist]

        track = MagicMock()
        track.title = "Other Track"
        release.tracklist = [track]

        score = provider._calculate_match_score(
            release,
            track_name="Test Track",
            artist_name="Test Artist",
            album_name="Test Album",
        )

        assert score == 40  # Only artist match

    def test_calculate_match_score_no_match(self, provider: DiscogsProvider) -> None:
        """Test match score calculation for no match."""
        release = MagicMock()
        release.title = "Different Album"

        artist = MagicMock()
        artist.name = "Different Artist"
        release.artists = [artist]

        release.tracklist = []

        score = provider._calculate_match_score(
            release,
            track_name="Test Track",
            artist_name="Test Artist",
            album_name="Test Album",
        )

        assert score == 0


class TestDiscogsProviderReleaseLookup:
    """Tests for Discogs release lookup by ID."""

    @pytest.fixture
    def provider(self) -> DiscogsProvider:
        """Create a provider for testing."""
        return DiscogsProvider()

    @pytest.mark.asyncio
    async def test_lookup_release(self, provider: DiscogsProvider) -> None:
        """Test looking up a release by ID."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client

            mock_release = MagicMock()
            mock_release.id = 12345
            mock_release.title = "Found Album"
            mock_release.year = 2020
            mock_release.artists = []
            mock_release.genres = None
            mock_release.styles = None
            mock_release.labels = None
            mock_release.country = None
            mock_release.images = None
            mock_release.tracklist = []

            mock_client.release.return_value = mock_release

            result = await provider.lookup_release(12345)

            assert result is not None
            assert result.album_name == "Found Album"

    @pytest.mark.asyncio
    async def test_lookup_release_error(self, provider: DiscogsProvider) -> None:
        """Test release lookup handles errors."""
        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = MagicMock()
            mock_ensure.return_value = mock_client
            mock_client.release.side_effect = Exception("Not found")

            result = await provider.lookup_release(99999)
            assert result is None


class TestDiscogsProviderClose:
    """Tests for DiscogsProvider cleanup."""

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test close clears the client."""
        provider = DiscogsProvider()
        provider._client = MagicMock()

        await provider.close()

        assert provider._client is None
