"""Tests for target providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.providers.targets.bandcamp import BandcampProvider
from spotdl.providers.targets.base import (
    NoResultsError,
    SearchError,
    TargetProvider,
    TargetProviderError,
)
from spotdl.providers.targets.piped import PipedProvider
from spotdl.providers.targets.soundcloud import SoundCloudProvider
from spotdl.providers.targets.youtube import YouTubeProvider
from spotdl.providers.targets.ytmusic import YouTubeMusicProvider


class TestTargetProviderErrors:
    """Tests for target provider exceptions."""

    def test_target_provider_error(self) -> None:
        """Test TargetProviderError."""
        error = TargetProviderError("Test error")
        assert str(error) == "Test error"

    def test_search_error(self) -> None:
        """Test SearchError inherits from TargetProviderError."""
        error = SearchError("Search failed")
        assert isinstance(error, TargetProviderError)
        assert str(error) == "Search failed"

    def test_no_results_error(self) -> None:
        """Test NoResultsError inherits from TargetProviderError."""
        error = NoResultsError("No results")
        assert isinstance(error, TargetProviderError)
        assert str(error) == "No results"


class ConcreteTargetProvider(TargetProvider):
    """Concrete implementation for testing."""

    name = "test"
    display_name = "Test Provider"

    async def search(self, song: Song, limit: int = 10) -> list[Result]:
        return []


class TestTargetProviderBase:
    """Tests for TargetProvider base class."""

    def test_build_search_query(self) -> None:
        """Test building search query from song."""
        provider = ConcreteTargetProvider()
        song = Song(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        query = provider.build_search_query(song)
        assert query == "Artist 1 - Test Song"

    def test_build_search_query_cleans_suffixes(self) -> None:
        """Test search query removes common suffixes."""
        provider = ConcreteTargetProvider()
        song = Song(
            name="Test Song (Official Audio)",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        query = provider.build_search_query(song)
        assert "(Official Audio)" not in query

    @pytest.mark.asyncio
    async def test_get_best_match_empty(self) -> None:
        """Test get_best_match returns None when no results."""
        provider = ConcreteTargetProvider()
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc",
            url="https://test.com",
        )

        result = await provider.get_best_match(song)
        assert result is None

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test close method."""
        provider = ConcreteTargetProvider()
        await provider.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with ConcreteTargetProvider() as provider:
            assert provider is not None


class TestYouTubeProvider:
    """Tests for YouTube provider."""

    def test_extract_video_id(self) -> None:
        """Test extracting video ID from YouTube URL."""
        result = YouTubeProvider.extract_video_id("https://www.youtube.com/watch?v=abc123xyz12")
        assert result == "abc123xyz12"

    def test_extract_video_id_short(self) -> None:
        """Test extracting video ID from short URL."""
        result = YouTubeProvider.extract_video_id("https://youtu.be/abc123xyz12")
        assert result == "abc123xyz12"

    def test_extract_video_id_invalid(self) -> None:
        """Test extracting video ID from invalid URL."""
        result = YouTubeProvider.extract_video_id("https://example.com/watch?v=abc")
        assert result is None

    def test_result_to_result(self) -> None:
        """Test converting YouTube video data to Result."""
        provider = YouTubeProvider()

        video_data = {
            "videoId": "abc123xyz12",
            "title": "Test Video",
            "author": "Test Channel",
            "lengthSeconds": 200,
            "viewCount": 1000000,
            "videoThumbnails": [
                {"url": "https://example.com/thumb.jpg", "width": 320, "height": 180},
                {"url": "https://example.com/thumb_hd.jpg", "width": 1280, "height": 720},
            ],
            "isVerified": True,
        }

        result = provider._result_to_result(video_data)

        assert result.name == "Test Video"
        assert result.artist == "Test Channel"
        assert result.duration == 200
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.platform_id == "abc123xyz12"
        assert result.url == "https://www.youtube.com/watch?v=abc123xyz12"
        assert result.views == 1000000
        assert result.verified is True
        # Should get highest res thumbnail
        assert "thumb_hd.jpg" in result.cover_url

    def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = YouTubeProvider()
        assert provider.name == "youtube"
        assert provider.display_name == "YouTube"


class TestYouTubeMusicTargetProvider:
    """Tests for YouTube Music target provider."""

    def test_extract_video_id(self) -> None:
        """Test extracting video ID from YouTube Music URL."""
        result = YouTubeMusicProvider.extract_video_id(
            "https://music.youtube.com/watch?v=abc123xyz12"
        )
        assert result == "abc123xyz12"

    def test_extract_video_id_standard_yt(self) -> None:
        """Test extracting video ID from standard YouTube URL."""
        result = YouTubeMusicProvider.extract_video_id(
            "https://www.youtube.com/watch?v=xyz789abc12"
        )
        assert result == "xyz789abc12"

    def test_result_to_result(self) -> None:
        """Test converting YouTube Music song data to Result."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123xyz12",
            "title": "Test Song",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "album": {"name": "Test Album"},
            "duration": "3:20",
            "thumbnails": [{"url": "https://example.com/cover.jpg", "width": 226, "height": 226}],
            "isExplicit": True,
        }

        result = provider._result_to_result(song_data)

        assert result.name == "Test Song"
        assert result.artist == "Artist 1"
        assert result.artists == ("Artist 1", "Artist 2")
        assert result.duration == 200  # 3*60 + 20
        assert result.platform == TargetPlatform.YOUTUBE_MUSIC
        assert result.platform_id == "abc123xyz12"
        assert result.album_name == "Test Album"
        assert result.explicit is True


class TestSoundCloudTargetProvider:
    """Tests for SoundCloud target provider."""

    def test_extract_track_info(self) -> None:
        """Test extracting track info from SoundCloud URL."""
        result = SoundCloudProvider.extract_track_info(
            "https://soundcloud.com/artist-name/track-name"
        )
        assert result == ("artist-name", "track-name")

    def test_extract_track_info_www(self) -> None:
        """Test extracting track info from www URL."""
        result = SoundCloudProvider.extract_track_info(
            "https://www.soundcloud.com/artist/song"
        )
        assert result == ("artist", "song")

    def test_extract_track_info_invalid(self) -> None:
        """Test extracting track info from invalid URL."""
        result = SoundCloudProvider.extract_track_info("https://example.com/track")
        assert result is None

    def test_track_to_result(self) -> None:
        """Test converting SoundCloud track data to Result."""
        provider = SoundCloudProvider()

        track_data = {
            "id": 123456789,
            "title": "Test Track",
            "user": {"username": "TestArtist", "avatar_url": "https://example.com/avatar.jpg"},
            "duration": 200000,  # milliseconds
            "artwork_url": "https://example.com/artwork-large.jpg",
            "permalink_url": "https://soundcloud.com/testartist/test-track",
            "playback_count": 50000,
        }

        result = provider._track_to_result(track_data)

        assert result.name == "Test Track"
        assert result.artist == "TestArtist"
        assert result.duration == 200
        assert result.platform == TargetPlatform.SOUNDCLOUD
        assert result.platform_id == "123456789"
        assert result.views == 50000


class TestBandcampTargetProvider:
    """Tests for Bandcamp target provider."""

    def test_extract_url_info(self) -> None:
        """Test extracting URL info from Bandcamp URL."""
        result = BandcampProvider.extract_url_info(
            "https://artist.bandcamp.com/track/song-name"
        )
        assert result == {"subdomain": "artist", "type": "track", "slug": "song-name"}

    def test_extract_url_info_album(self) -> None:
        """Test extracting URL info from album URL."""
        result = BandcampProvider.extract_url_info(
            "https://myband.bandcamp.com/album/album-title"
        )
        assert result == {"subdomain": "myband", "type": "album", "slug": "album-title"}

    def test_extract_url_info_invalid(self) -> None:
        """Test extracting URL info from invalid URL."""
        result = BandcampProvider.extract_url_info("https://example.com/track/abc")
        assert result is None


class TestPipedProvider:
    """Tests for Piped provider."""

    def test_extract_video_id_youtube(self) -> None:
        """Test extracting video ID from YouTube URL."""
        result = PipedProvider.extract_video_id("https://www.youtube.com/watch?v=abc123xyz12")
        assert result == "abc123xyz12"

    def test_extract_video_id_youtu_be(self) -> None:
        """Test extracting video ID from youtu.be URL."""
        result = PipedProvider.extract_video_id("https://youtu.be/xyz789abc12")
        assert result == "xyz789abc12"

    def test_item_to_result(self) -> None:
        """Test converting Piped item to Result."""
        provider = PipedProvider()

        item_data = {
            "url": "/watch?v=abc123xyz12",
            "title": "Test Video",
            "uploaderName": "Test Channel",
            "duration": 200,
            "thumbnail": "https://example.com/thumb.jpg",
            "views": 500000,
            "uploaderVerified": True,
        }

        result = provider._item_to_result(item_data)

        assert result.name == "Test Video"
        assert result.artist == "Test Channel"
        assert result.duration == 200
        assert result.platform == TargetPlatform.PIPED
        assert result.platform_id == "abc123xyz12"
        assert result.url == "https://www.youtube.com/watch?v=abc123xyz12"
        assert result.views == 500000
        assert result.verified is True

    def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = PipedProvider()
        assert provider.name == "piped"
        assert provider.display_name == "Piped"
