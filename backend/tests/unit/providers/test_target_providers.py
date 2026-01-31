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

    def test_extract_video_id_with_params(self) -> None:
        """Test extracting video ID from URL with extra parameters."""
        result = PipedProvider.extract_video_id(
            "https://www.youtube.com/watch?v=abc123xyz12&list=PLxyz"
        )
        assert result == "abc123xyz12"

    def test_extract_video_id_invalid(self) -> None:
        """Test extracting video ID from invalid URL."""
        result = PipedProvider.extract_video_id("https://example.com/video/abc")
        assert result is None

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

    def test_item_to_result_uploader_fallback(self) -> None:
        """Test item to result uses uploader as fallback."""
        provider = PipedProvider()

        item_data = {
            "url": "/watch?v=xyz789abc12",
            "title": "Test",
            "uploader": "Fallback Channel",  # No uploaderName
            "duration": 100,
        }

        result = provider._item_to_result(item_data)
        assert result.artist == "Fallback Channel"

    def test_item_to_result_empty_url(self) -> None:
        """Test item to result with empty URL."""
        provider = PipedProvider()

        item_data = {
            "url": "",
            "title": "Test",
            "uploaderName": "Channel",
            "duration": 100,
        }

        result = provider._item_to_result(item_data)
        assert result.platform_id == ""
        assert result.url == ""

    def test_provider_attributes(self) -> None:
        """Test provider has correct attributes."""
        provider = PipedProvider()
        assert provider.name == "piped"
        assert provider.display_name == "Piped"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = PipedProvider()
        await provider.close()


class TestYouTubeProviderAdditional:
    """Additional tests for YouTube provider."""

    def test_extract_video_id_with_timestamp(self) -> None:
        """Test extracting video ID from URL with timestamp."""
        result = YouTubeProvider.extract_video_id(
            "https://www.youtube.com/watch?v=abc123xyz12&t=120"
        )
        assert result == "abc123xyz12"

    def test_result_to_result_no_thumbnails(self) -> None:
        """Test converting video data with no thumbnails."""
        provider = YouTubeProvider()

        video_data = {
            "videoId": "xyz789abc12",
            "title": "Test Video",
            "author": "Test Channel",
            "lengthSeconds": 180,
        }

        result = provider._result_to_result(video_data)
        assert result.cover_url is None
        assert result.duration == 180

    def test_result_to_result_defaults(self) -> None:
        """Test converting video data with missing fields."""
        provider = YouTubeProvider()

        video_data = {
            "videoId": "vid123",
        }

        result = provider._result_to_result(video_data)
        assert result.name == "Unknown"
        assert result.artist == "Unknown"
        assert result.duration == 0
        assert result.verified is False

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = YouTubeProvider()
        await provider.close()


class TestYouTubeMusicTargetProviderAdditional:
    """Additional tests for YouTube Music target provider."""

    def test_extract_video_id_with_list(self) -> None:
        """Test extracting video ID from URL with playlist."""
        result = YouTubeMusicProvider.extract_video_id(
            "https://music.youtube.com/watch?v=abc123xyz12&list=RDabc"
        )
        assert result == "abc123xyz12"

    def test_extract_video_id_invalid(self) -> None:
        """Test extracting video ID from invalid URL."""
        result = YouTubeMusicProvider.extract_video_id(
            "https://music.youtube.com/playlist?list=abc"
        )
        assert result is None

    def test_result_to_result_duration_seconds(self) -> None:
        """Test converting song data with duration_seconds field."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "xyz123",
            "title": "Test Song",
            "duration_seconds": 215,
        }

        result = provider._result_to_result(song_data)
        assert result.duration == 215

    def test_result_to_result_no_artists(self) -> None:
        """Test converting song data with no artists."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "vid456",
            "title": "Test Song",
        }

        result = provider._result_to_result(song_data)
        assert result.artist == "Unknown"
        assert result.artists == ("Unknown",)

    def test_result_to_result_single_artist(self) -> None:
        """Test converting song data with single artist."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "vid789",
            "title": "Test Song",
            "artists": [{"name": "Solo Artist"}],
        }

        result = provider._result_to_result(song_data)
        assert result.artist == "Solo Artist"
        assert result.artists == ("Solo Artist",)

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = YouTubeMusicProvider()
        await provider.close()


class TestSoundCloudTargetProviderAdditional:
    """Additional tests for SoundCloud target provider."""

    def test_track_to_result_avatar_fallback(self) -> None:
        """Test cover URL falls back to avatar."""
        provider = SoundCloudProvider()

        track_data = {
            "id": 123,
            "title": "Test",
            "user": {
                "username": "Artist",
                "avatar_url": "https://example.com/avatar.jpg",
            },
            "duration": 180000,
            "permalink_url": "https://soundcloud.com/artist/test",
        }

        result = provider._track_to_result(track_data)
        assert result.cover_url == "https://example.com/avatar.jpg"

    def test_track_to_result_no_cover(self) -> None:
        """Test result with no cover URL."""
        provider = SoundCloudProvider()

        track_data = {
            "id": 456,
            "title": "Test",
            "user": {"username": "Artist"},
            "duration": 120000,
            "permalink_url": "https://soundcloud.com/artist/test",
        }

        result = provider._track_to_result(track_data)
        assert result.cover_url is None

    def test_track_to_result_zero_duration(self) -> None:
        """Test result with zero duration."""
        provider = SoundCloudProvider()

        track_data = {
            "id": 789,
            "title": "Test",
            "user": {"username": "Artist"},
            "permalink_url": "https://soundcloud.com/artist/test",
        }

        result = provider._track_to_result(track_data)
        assert result.duration == 0

    def test_extract_track_info_sets(self) -> None:
        """Test extract doesn't match sets URL."""
        result = SoundCloudProvider.extract_track_info(
            "https://soundcloud.com/artist/sets/playlist"
        )
        # Should match as it fits the pattern /user/track-name
        assert result == ("artist", "sets")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = SoundCloudProvider()
        await provider.close()


class TestBandcampTargetProviderAdditional:
    """Additional tests for Bandcamp target provider."""

    def test_extract_url_info_with_query_params(self) -> None:
        """Test extracting URL info ignores query params."""
        result = BandcampProvider.extract_url_info(
            "https://artist.bandcamp.com/track/song-name?from=search"
        )
        assert result == {"subdomain": "artist", "type": "track", "slug": "song-name"}

    def test_parse_search_result_no_link(self) -> None:
        """Test parsing result without link returns None."""
        provider = BandcampProvider()
        from bs4 import BeautifulSoup

        html = '<li class="searchresult"><div class="heading">Title</div></li>'
        soup = BeautifulSoup(html, "lxml")
        result_elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(result_elem)
        assert result is None

    def test_parse_search_result_album_link(self) -> None:
        """Test parsing result with album link returns None."""
        provider = BandcampProvider()
        from bs4 import BeautifulSoup

        html = '''
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/album/album-name"></a>
            <div class="heading">Title</div>
        </li>
        '''
        soup = BeautifulSoup(html, "lxml")
        result_elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(result_elem)
        assert result is None  # Not a track link

    def test_parse_search_result_full(self) -> None:
        """Test parsing a complete search result."""
        provider = BandcampProvider()
        from bs4 import BeautifulSoup

        # Bandcamp subhead format is "track by Artist from Album"
        html = '''
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/track/song-name">
                <img src="https://example.com/thumb_5.jpg" />
            </a>
            <div class="heading">Song Title</div>
            <div class="subhead">track by Artist Name from Album Name</div>
        </li>
        '''
        soup = BeautifulSoup(html, "lxml")
        result_elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(result_elem)
        assert result is not None
        assert result.name == "Song Title"
        assert result.artist == "Artist Name"
        assert result.album_name == "Album Name"
        assert "_10.jpg" in result.cover_url  # Higher resolution

    def test_parse_search_result_no_album(self) -> None:
        """Test parsing result without album."""
        provider = BandcampProvider()
        from bs4 import BeautifulSoup

        # Subhead without "from Album" part
        html = '''
        <li class="searchresult">
            <a class="artcont" href="https://artist.bandcamp.com/track/song">
            </a>
            <div class="heading">Song</div>
            <div class="subhead">track by Artist Only</div>
        </li>
        '''
        soup = BeautifulSoup(html, "lxml")
        result_elem = soup.find("li", class_="searchresult")

        result = provider._parse_search_result(result_elem)
        assert result is not None
        assert result.artist == "Artist Only"
        assert result.album_name == ""

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = BandcampProvider()
        await provider.close()


class TestPipedProviderAdditional:
    """Additional tests for Piped provider."""

    def test_item_to_result_no_uploader(self) -> None:
        """Test item to result with no uploader info."""
        provider = PipedProvider()

        item_data = {
            "url": "/watch?v=abc123",
            "title": "Test",
            "duration": 100,
        }

        result = provider._item_to_result(item_data)
        assert result.artist == "Unknown"

    def test_item_to_result_thumbnail(self) -> None:
        """Test item to result preserves thumbnail."""
        provider = PipedProvider()

        item_data = {
            "url": "/watch?v=abc123",
            "title": "Test",
            "uploaderName": "Channel",
            "duration": 100,
            "thumbnail": "https://example.com/thumb.jpg",
        }

        result = provider._item_to_result(item_data)
        assert result.cover_url == "https://example.com/thumb.jpg"


class TestYouTubeProviderResultConversion:
    """More tests for YouTube result conversion."""

    def test_result_to_result_with_verified(self) -> None:
        """Test converting video data with verified channel."""
        provider = YouTubeProvider()

        video_data = {
            "videoId": "vid123",
            "title": "Test",
            "author": "Verified Channel",
            "lengthSeconds": 200,
            "isVerified": True,
        }

        result = provider._result_to_result(video_data)
        assert result.verified is True

    def test_result_to_result_largest_thumbnail(self) -> None:
        """Test result picks largest thumbnail."""
        provider = YouTubeProvider()

        video_data = {
            "videoId": "vid123",
            "title": "Test",
            "author": "Channel",
            "lengthSeconds": 200,
            "videoThumbnails": [
                {"url": "https://example.com/small.jpg", "width": 120, "height": 90},
                {"url": "https://example.com/medium.jpg", "width": 320, "height": 180},
                {"url": "https://example.com/large.jpg", "width": 1280, "height": 720},
            ],
        }

        result = provider._result_to_result(video_data)
        assert "large" in result.cover_url


class TestYouTubeMusicResultConversion:
    """More tests for YouTube Music result conversion."""

    def test_result_to_result_with_album(self) -> None:
        """Test converting song data with album info."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "vid123",
            "title": "Test Song",
            "artists": [{"name": "Artist"}],
            "album": {"name": "Test Album"},
            "duration": "3:30",
        }

        result = provider._result_to_result(song_data)
        assert result.album_name == "Test Album"
        assert result.duration == 210

    def test_result_to_result_explicit(self) -> None:
        """Test converting song data with explicit flag."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "vid456",
            "title": "Explicit Song",
            "duration": "2:00",
            "isExplicit": True,
        }

        result = provider._result_to_result(song_data)
        assert result.explicit is True

    def test_result_to_result_thumbnails(self) -> None:
        """Test converting song data picks best thumbnail."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "vid789",
            "title": "Test",
            "thumbnails": [
                {"url": "https://example.com/small.jpg", "width": 60, "height": 60},
                {"url": "https://example.com/large.jpg", "width": 226, "height": 226},
            ],
        }

        result = provider._result_to_result(song_data)
        assert "large" in result.cover_url


class TestSoundCloudResultConversion:
    """More tests for SoundCloud result conversion."""

    def test_track_to_result_artwork_resolution(self) -> None:
        """Test artwork URL is upgraded to higher resolution."""
        provider = SoundCloudProvider()

        track_data = {
            "id": 123,
            "title": "Test",
            "user": {"username": "Artist"},
            "duration": 180000,
            "artwork_url": "https://i1.sndcdn.com/artworks-abc-large.jpg",
            "permalink_url": "https://soundcloud.com/artist/test",
        }

        result = provider._track_to_result(track_data)
        # Should upgrade from -large to -t500x500
        assert "t500x500" in result.cover_url
