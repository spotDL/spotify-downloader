"""Tests for base source provider."""

from __future__ import annotations

import re

import pytest

from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl_core.types import Song, SongList


class TestSourceProviderError:
    """Test SourceProviderError exception."""

    def test_source_provider_error(self):
        """Test creating SourceProviderError."""
        error = SourceProviderError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestInvalidURLError:
    """Test InvalidURLError exception."""

    def test_invalid_url_error(self):
        """Test creating InvalidURLError."""
        error = InvalidURLError("Invalid URL")
        assert str(error) == "Invalid URL"
        assert isinstance(error, SourceProviderError)


class TestTrackNotFoundError:
    """Test TrackNotFoundError exception."""

    def test_track_not_found_error(self):
        """Test creating TrackNotFoundError."""
        error = TrackNotFoundError("Track not found")
        assert str(error) == "Track not found"
        assert isinstance(error, SourceProviderError)


class ConcreteProvider(SourceProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"
    url_patterns = [
        re.compile(r"https://test\.com/(track|album|playlist|artist)/(\w+)"),
        re.compile(r"test:(track|album):(\w+)"),
    ]

    async def get_track(self, url: str) -> Song:
        """Get track."""
        return Song(
            name="Test Track",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform="test",
            platform_id="test123",
            url=url,
        )

    async def get_album(self, url: str) -> SongList:
        """Get album."""
        song = await self.get_track(url)
        return SongList(
            name="Test Album",
            url=url,
            platform="test",
            urls=(url,),
            songs=(song,),
        )

    async def get_playlist(self, url: str) -> SongList:
        """Get playlist."""
        song = await self.get_track(url)
        return SongList(
            name="Test Playlist",
            url=url,
            platform="test",
            urls=(url,),
            songs=(song,),
        )

    async def get_artist(self, url: str) -> SongList:
        """Get artist."""
        song = await self.get_track(url)
        return SongList(
            name="Test Artist",
            url=url,
            platform="test",
            urls=(url,),
            songs=(song,),
        )

    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """Search."""
        return [
            Song(
                name=f"Result {i}",
                artists=["Test Artist"],
                artist="Test Artist",
                duration=180,
                platform="test",
                platform_id=f"test{i}",
                url=f"https://test.com/track/test{i}",
            )
            for i in range(min(limit, 3))
        ]


class TestSourceProvider:
    """Test SourceProvider base class."""

    @pytest.fixture
    def provider(self) -> ConcreteProvider:
        """Create a concrete provider for testing."""
        return ConcreteProvider()

    def test_provider_name(self, provider: ConcreteProvider):
        """Test provider name."""
        assert provider.name == "test"
        assert provider.display_name == "Test Provider"

    def test_matches_url_valid(self, provider: ConcreteProvider):
        """Test matches_url with valid URL."""
        assert provider.matches_url("https://test.com/track/abc123")
        assert provider.matches_url("https://test.com/album/xyz789")
        assert provider.matches_url("test:track:abc")
        assert provider.matches_url("test:album:xyz")

    def test_matches_url_invalid(self, provider: ConcreteProvider):
        """Test matches_url with invalid URL."""
        assert not provider.matches_url("https://other.com/track/abc")
        assert not provider.matches_url("invalid")
        assert not provider.matches_url("")

    def test_extract_id_track(self, provider: ConcreteProvider):
        """Test extract_id for track URL."""
        track_id = provider.extract_id("https://test.com/track/abc123")
        # extract_id returns the first captured group which is the type in our pattern
        assert track_id == "track"

    def test_extract_id_album(self, provider: ConcreteProvider):
        """Test extract_id for album URL."""
        album_id = provider.extract_id("https://test.com/album/xyz789")
        # extract_id returns the first captured group which is the type in our pattern
        assert album_id == "album"

    def test_extract_id_uri(self, provider: ConcreteProvider):
        """Test extract_id for URI format."""
        track_id = provider.extract_id("test:track:abc")
        # extract_id returns the first captured group which is the type in our pattern
        assert track_id == "track"

    def test_extract_id_no_match(self, provider: ConcreteProvider):
        """Test extract_id with no match."""
        assert provider.extract_id("https://other.com/track/abc") is None
        assert provider.extract_id("invalid") is None

    def test_get_url_type_track(self, provider: ConcreteProvider):
        """Test get_url_type for track URL."""
        assert provider.get_url_type("https://test.com/track/abc") == "track"
        assert provider.get_url_type("https://test.com/song/abc") == "track"

    def test_get_url_type_album(self, provider: ConcreteProvider):
        """Test get_url_type for album URL."""
        assert provider.get_url_type("https://test.com/album/abc") == "album"

    def test_get_url_type_playlist(self, provider: ConcreteProvider):
        """Test get_url_type for playlist URL."""
        assert provider.get_url_type("https://test.com/playlist/abc") == "playlist"

    def test_get_url_type_artist(self, provider: ConcreteProvider):
        """Test get_url_type for artist URL."""
        assert provider.get_url_type("https://test.com/artist/abc") == "artist"

    def test_get_url_type_unknown(self, provider: ConcreteProvider):
        """Test get_url_type with unknown URL."""
        assert provider.get_url_type("https://test.com/unknown/abc") is None

    def test_get_url_type_case_insensitive(self, provider: ConcreteProvider):
        """Test get_url_type is case insensitive."""
        assert provider.get_url_type("https://test.com/TRACK/abc") == "track"
        assert provider.get_url_type("https://test.com/Album/abc") == "album"

    async def test_get_track(self, provider: ConcreteProvider):
        """Test get_track."""
        song = await provider.get_track("https://test.com/track/abc123")
        assert isinstance(song, Song)
        assert song.name == "Test Track"
        assert song.url == "https://test.com/track/abc123"

    async def test_get_album(self, provider: ConcreteProvider):
        """Test get_album."""
        song_list = await provider.get_album("https://test.com/album/abc123")
        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Album"
        assert len(song_list.songs) == 1

    async def test_get_playlist(self, provider: ConcreteProvider):
        """Test get_playlist."""
        song_list = await provider.get_playlist("https://test.com/playlist/abc123")
        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Playlist"
        assert len(song_list.songs) == 1

    async def test_get_artist(self, provider: ConcreteProvider):
        """Test get_artist."""
        song_list = await provider.get_artist("https://test.com/artist/abc123")
        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Artist"
        assert len(song_list.songs) == 1

    async def test_search(self, provider: ConcreteProvider):
        """Test search."""
        results = await provider.search("test query")
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, Song) for r in results)

    async def test_search_with_limit(self, provider: ConcreteProvider):
        """Test search with limit."""
        results = await provider.search("test query", limit=2)
        assert len(results) == 2

    async def test_get_songs_from_url_track(self, provider: ConcreteProvider):
        """Test get_songs_from_url with track URL."""
        songs = await provider.get_songs_from_url("https://test.com/track/abc")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)

    async def test_get_songs_from_url_album(self, provider: ConcreteProvider):
        """Test get_songs_from_url with album URL."""
        songs = await provider.get_songs_from_url("https://test.com/album/abc")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)

    async def test_get_songs_from_url_playlist(self, provider: ConcreteProvider):
        """Test get_songs_from_url with playlist URL."""
        songs = await provider.get_songs_from_url("https://test.com/playlist/abc")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)

    async def test_get_songs_from_url_artist(self, provider: ConcreteProvider):
        """Test get_songs_from_url with artist URL."""
        songs = await provider.get_songs_from_url("https://test.com/artist/abc")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)

    async def test_get_songs_from_url_unknown(self, provider: ConcreteProvider):
        """Test get_songs_from_url with unknown URL type defaults to track."""
        songs = await provider.get_songs_from_url("https://test.com/unknown/abc")
        assert len(songs) == 1
        assert isinstance(songs[0], Song)


class TestSourceProviderAbstractMethods:
    """Test that abstract methods must be implemented."""

    def test_cannot_instantiate_base_provider(self):
        """Test that SourceProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SourceProvider()

    def test_concrete_provider_requires_all_methods(self):
        """Test that concrete provider must implement all abstract methods."""

        class IncompleteProvider(SourceProvider):
            """Incomplete provider missing methods."""

            name = "incomplete"
            display_name = "Incomplete"
            url_patterns = []

        with pytest.raises(TypeError):
            IncompleteProvider()
