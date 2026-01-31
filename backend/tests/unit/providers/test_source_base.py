"""Tests for base source provider."""

import re

import pytest

from spotdl.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)


class TestSourceProviderErrors:
    """Tests for source provider exceptions."""

    def test_source_provider_error(self) -> None:
        """Test SourceProviderError."""
        error = SourceProviderError("Test error")
        assert str(error) == "Test error"

    def test_invalid_url_error(self) -> None:
        """Test InvalidURLError inherits from SourceProviderError."""
        error = InvalidURLError("Invalid URL")
        assert isinstance(error, SourceProviderError)
        assert str(error) == "Invalid URL"

    def test_track_not_found_error(self) -> None:
        """Test TrackNotFoundError inherits from SourceProviderError."""
        error = TrackNotFoundError("Track not found")
        assert isinstance(error, SourceProviderError)
        assert str(error) == "Track not found"


class ConcreteProvider(SourceProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"
    url_patterns = [
        re.compile(r"https://test\.com/(track|album|playlist|artist)/(\w+)"),
    ]

    async def get_track(self, url: str):
        pass

    async def get_album(self, url: str):
        pass

    async def get_playlist(self, url: str):
        pass

    async def get_artist(self, url: str):
        pass

    async def search(self, query: str, limit: int = 10):
        return []


class TestSourceProviderBase:
    """Tests for SourceProvider base class."""

    def test_matches_url(self) -> None:
        """Test URL matching."""
        assert ConcreteProvider.matches_url("https://test.com/track/abc123")
        assert ConcreteProvider.matches_url("https://test.com/album/xyz789")
        assert not ConcreteProvider.matches_url("https://other.com/track/abc123")

    def test_extract_id(self) -> None:
        """Test ID extraction from URL."""
        assert ConcreteProvider.extract_id("https://test.com/track/abc123") == "track"
        assert ConcreteProvider.extract_id("https://other.com/track/123") is None

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://test.com/track/abc", "track"),
            ("https://test.com/album/xyz", "album"),
            ("https://test.com/playlist/list", "playlist"),
            ("https://test.com/artist/art", "artist"),
            ("https://test.com/song/abc", "track"),  # song normalized to track
            ("https://test.com/other/xyz", None),
        ],
    )
    def test_get_url_type(self, url: str, expected: str | None) -> None:
        """Test URL type detection."""
        assert ConcreteProvider.get_url_type(url) == expected

    def test_provider_attributes(self) -> None:
        """Test provider has required attributes."""
        provider = ConcreteProvider()
        assert provider.name == "test"
        assert provider.display_name == "Test Provider"
        assert len(provider.url_patterns) > 0
