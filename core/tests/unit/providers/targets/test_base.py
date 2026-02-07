"""Unit tests for base target provider."""

from __future__ import annotations

import pytest

from spotdl_core.providers.targets.base import (
    NoResultsError,
    SearchError,
    TargetProvider,
    TargetProviderError,
)
from spotdl_core.types import Platform, Result, Song, TargetPlatform


class ConcreteTargetProvider(TargetProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        """Mock search implementation."""
        return [
            Result(
                name=song.name,
                artists=song.artists,
                artist=song.artist,
                duration=song.duration,
                platform=TargetPlatform.YOUTUBE,
                platform_id="test123",
                url="https://example.com/test",
            )
        ]


class TestTargetProviderError:
    """Test TargetProviderError exception."""

    def test_exception_creation(self):
        """Test creating TargetProviderError."""
        error = TargetProviderError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_inheritance(self):
        """Test TargetProviderError inherits from Exception."""
        error = TargetProviderError("Test")
        assert isinstance(error, Exception)


class TestSearchError:
    """Test SearchError exception."""

    def test_exception_creation(self):
        """Test creating SearchError."""
        error = SearchError("Search failed")
        assert str(error) == "Search failed"
        assert isinstance(error, TargetProviderError)

    def test_inheritance(self):
        """Test SearchError inherits from TargetProviderError."""
        error = SearchError("Test")
        assert isinstance(error, TargetProviderError)
        assert isinstance(error, Exception)


class TestNoResultsError:
    """Test NoResultsError exception."""

    def test_exception_creation(self):
        """Test creating NoResultsError."""
        error = NoResultsError("No results")
        assert str(error) == "No results"
        assert isinstance(error, TargetProviderError)

    def test_inheritance(self):
        """Test NoResultsError inherits from TargetProviderError."""
        error = NoResultsError("Test")
        assert isinstance(error, TargetProviderError)
        assert isinstance(error, Exception)


class TestTargetProvider:
    """Test TargetProvider base class."""

    @pytest.fixture
    def provider(self) -> ConcreteTargetProvider:
        """Create a test provider instance."""
        return ConcreteTargetProvider()

    @pytest.fixture
    def sample_song(self) -> Song:
        """Create a sample song for testing."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    def test_initialization(self, provider: ConcreteTargetProvider):
        """Test provider initialization."""
        assert provider.name == "test"
        assert provider.display_name == "Test Provider"

    def test_name_attribute(self, provider: ConcreteTargetProvider):
        """Test provider name attribute."""
        assert isinstance(provider.name, str)
        assert provider.name == "test"

    def test_display_name_attribute(self, provider: ConcreteTargetProvider):
        """Test provider display_name attribute."""
        assert isinstance(provider.display_name, str)
        assert provider.display_name == "Test Provider"

    @pytest.mark.asyncio
    async def test_search_abstract(self):
        """Test that search is abstract."""
        # Test that TargetProvider cannot be instantiated without implementing search
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            TargetProvider()

    @pytest.mark.asyncio
    async def test_search_implementation(
        self, provider: ConcreteTargetProvider, sample_song: Song
    ):
        """Test search implementation."""
        results = await provider.search(sample_song)
        assert len(results) == 1
        assert results[0].name == "Test Song"
        assert results[0].artist == "Test Artist"

    @pytest.mark.asyncio
    async def test_get_best_match(
        self, provider: ConcreteTargetProvider, sample_song: Song
    ):
        """Test get_best_match method."""
        result = await provider.get_best_match(sample_song)
        assert result is not None
        assert result.name == "Test Song"
        assert result.artist == "Test Artist"

    @pytest.mark.asyncio
    async def test_get_best_match_no_results(self):
        """Test get_best_match with no results."""

        class EmptyProvider(TargetProvider):
            name = "empty"
            display_name = "Empty"

            async def search(self, song: Song, limit: int = 10) -> list[Result]:
                return []

        provider = EmptyProvider()
        song = Song(
            name="Test",
            artists=["Test"],
            artist="Test",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )
        result = await provider.get_best_match(song)
        assert result is None

    def test_build_search_query_basic(
        self, provider: ConcreteTargetProvider, sample_song: Song
    ):
        """Test basic search query building."""
        query = provider.build_search_query(sample_song)
        assert query == "Test Artist - Test Song"

    def test_build_search_query_removes_official_audio(
        self, provider: ConcreteTargetProvider
    ):
        """Test that (Official Audio) is removed from query."""
        song = Song(
            name="Test Song (Official Audio)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )
        query = provider.build_search_query(song)
        assert query == "Test Artist - Test Song"
        assert "(Official Audio)" not in query

    def test_build_search_query_removes_official_video(
        self, provider: ConcreteTargetProvider
    ):
        """Test that (Official Video) is removed from query."""
        song = Song(
            name="Test Song (Official Video)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )
        query = provider.build_search_query(song)
        assert query == "Test Artist - Test Song"
        assert "(Official Video)" not in query

    def test_build_search_query_removes_lyrics(
        self, provider: ConcreteTargetProvider
    ):
        """Test that (Lyrics) is removed from query."""
        song = Song(
            name="Test Song (Lyrics)",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )
        query = provider.build_search_query(song)
        assert query == "Test Artist - Test Song"
        assert "(Lyrics)" not in query

    def test_build_search_query_strips_whitespace(
        self, provider: ConcreteTargetProvider
    ):
        """Test that extra whitespace is stripped."""
        song = Song(
            name="  Test Song  ",
            artists=["  Test Artist  "],
            artist="  Test Artist  ",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )
        query = provider.build_search_query(song)
        assert query == "Test Artist   -   Test Song"

    @pytest.mark.asyncio
    async def test_close_default(self, provider: ConcreteTargetProvider):
        """Test default close implementation."""
        await provider.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, provider: ConcreteTargetProvider):
        """Test async context manager entry."""
        async with provider as p:
            assert p is provider

    @pytest.mark.asyncio
    async def test_context_manager_exit(self, provider: ConcreteTargetProvider):
        """Test async context manager exit."""
        closed = False

        class TrackingProvider(ConcreteTargetProvider):
            async def close(self):
                nonlocal closed
                closed = True

        async with TrackingProvider():
            pass

        assert closed

    @pytest.mark.asyncio
    async def test_context_manager_exit_with_exception(self):
        """Test async context manager exit with exception."""
        closed = False

        class TrackingProvider(ConcreteTargetProvider):
            async def close(self):
                nonlocal closed
                closed = True

        try:
            async with TrackingProvider():
                raise ValueError("Test error")
        except ValueError:
            pass

        assert closed
