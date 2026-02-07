"""Tests for YouTube Music source provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spotdl_core.providers.sources.ytmusic import (
    YTMUSIC_URL_PATTERNS,
    YouTubeMusicProvider,
)
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl_core.types import Platform, Song, SongList


class TestYouTubeMusicProvider:
    """Test YouTubeMusicProvider class."""

    @pytest.fixture
    def provider(self) -> YouTubeMusicProvider:
        """Create a YouTube Music provider."""
        return YouTubeMusicProvider()

    @pytest.fixture
    def mock_song_data(self) -> dict:
        """Create mock song data."""
        return {
            "videoId": "abc123",
            "title": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "album": {"name": "Test Album"},
            "duration": "3:45",
            "duration_seconds": 225,
            "thumbnails": [
                {"url": "https://example.com/thumb.jpg", "width": 640, "height": 640}
            ],
            "year": "2023",
            "isExplicit": True,
        }

    @pytest.fixture
    def mock_album_data(self) -> dict:
        """Create mock album data."""
        return {
            "title": "Test Album",
            "tracks": [
                {
                    "videoId": "track1",
                    "title": "Track 1",
                    "artists": [{"name": "Test Artist"}],
                    "duration": "3:30",
                },
                {
                    "videoId": "track2",
                    "title": "Track 2",
                    "artists": [{"name": "Test Artist"}],
                    "duration": "4:00",
                },
            ],
        }

    @pytest.fixture
    def mock_playlist_data(self) -> dict:
        """Create mock playlist data."""
        return {
            "title": "Test Playlist",
            "tracks": [
                {
                    "videoId": "track1",
                    "title": "Track 1",
                    "artists": [{"name": "Artist 1"}],
                    "duration": "3:30",
                },
            ],
        }

    @pytest.fixture
    def mock_artist_data(self) -> dict:
        """Create mock artist data."""
        return {
            "name": "Test Artist",
            "songs": {
                "results": [
                    {
                        "videoId": "song1",
                        "title": "Song 1",
                        "artists": [{"name": "Test Artist"}],
                        "duration": "3:30",
                    }
                ]
            },
            "albums": {
                "results": [
                    {
                        "browseId": "album1",
                        "title": "Album 1",
                    }
                ]
            },
        }

    def test_provider_init(self, provider: YouTubeMusicProvider):
        """Test provider initialization."""
        assert provider.name == "youtube_music"
        assert provider.display_name == "YouTube Music"
        assert len(provider.url_patterns) == 4

    def test_provider_init_with_auth(self):
        """Test provider initialization with auth file."""
        provider = YouTubeMusicProvider(auth_file="auth.json")
        assert provider._auth_file == "auth.json"

    def test_url_patterns(self):
        """Test URL patterns are defined."""
        assert len(YTMUSIC_URL_PATTERNS) == 4
        assert YTMUSIC_URL_PATTERNS[0].search("https://music.youtube.com/watch?v=abc123")
        assert YTMUSIC_URL_PATTERNS[1].search("https://music.youtube.com/playlist?list=PLabc")
        assert YTMUSIC_URL_PATTERNS[2].search("https://music.youtube.com/channel/UCabc123")
        assert YTMUSIC_URL_PATTERNS[3].search("https://music.youtube.com/browse/MPREb_abc")

    def test_extract_video_id(self, provider: YouTubeMusicProvider):
        """Test extracting video ID."""
        video_id = provider._extract_video_id("https://music.youtube.com/watch?v=abc123")
        assert video_id == "abc123"

    def test_extract_video_id_with_list(self, provider: YouTubeMusicProvider):
        """Test extracting video ID with playlist parameter."""
        video_id = provider._extract_video_id(
            "https://music.youtube.com/watch?v=abc123&list=PLxyz"
        )
        assert video_id == "abc123"

    def test_extract_video_id_no_match(self, provider: YouTubeMusicProvider):
        """Test extracting video ID with no match."""
        video_id = provider._extract_video_id("https://music.youtube.com/channel/UCabc")
        assert video_id is None

    def test_extract_playlist_id(self, provider: YouTubeMusicProvider):
        """Test extracting playlist ID."""
        playlist_id = provider._extract_playlist_id(
            "https://music.youtube.com/playlist?list=PLabc123"
        )
        assert playlist_id == "PLabc123"

    def test_extract_playlist_id_no_match(self, provider: YouTubeMusicProvider):
        """Test extracting playlist ID with no match."""
        playlist_id = provider._extract_playlist_id("https://music.youtube.com/watch?v=abc")
        assert playlist_id is None

    def test_extract_channel_id(self, provider: YouTubeMusicProvider):
        """Test extracting channel ID."""
        channel_id = provider._extract_channel_id("https://music.youtube.com/channel/UCabc123")
        assert channel_id == "UCabc123"

    def test_extract_channel_id_browse(self, provider: YouTubeMusicProvider):
        """Test extracting browse ID."""
        browse_id = provider._extract_channel_id("https://music.youtube.com/browse/MPREb_abc")
        assert browse_id == "MPREb_abc"

    def test_extract_channel_id_no_match(self, provider: YouTubeMusicProvider):
        """Test extracting channel ID with no match."""
        channel_id = provider._extract_channel_id("https://music.youtube.com/watch?v=abc")
        assert channel_id is None

    def test_song_to_song_minimal(self, provider: YouTubeMusicProvider, mock_song_data: dict):
        """Test converting song data to Song."""
        song = provider._song_to_song(mock_song_data)
        assert isinstance(song, Song)
        assert song.name == "Test Song"
        assert song.artists == ["Test Artist"]
        assert song.duration == 225
        assert song.platform == Platform.YOUTUBE_MUSIC
        assert song.platform_id == "abc123"
        assert song.url == "https://music.youtube.com/watch?v=abc123"

    def test_song_to_song_parse_duration_mm_ss(self, provider: YouTubeMusicProvider):
        """Test parsing duration in mm:ss format."""
        data = {
            "videoId": "test",
            "title": "Test",
            "artists": [{"name": "Artist"}],
            "duration": "3:45",
        }
        song = provider._song_to_song(data)
        assert song.duration == 225  # 3*60 + 45

    def test_song_to_song_parse_duration_hh_mm_ss(self, provider: YouTubeMusicProvider):
        """Test parsing duration in hh:mm:ss format."""
        data = {
            "videoId": "test",
            "title": "Test",
            "artists": [{"name": "Artist"}],
            "duration": "1:30:45",
        }
        song = provider._song_to_song(data)
        assert song.duration == 5445  # 1*3600 + 30*60 + 45

    def test_song_to_song_with_list_info(
        self, provider: YouTubeMusicProvider, mock_song_data: dict
    ):
        """Test converting song data with list info."""
        list_info = {
            "name": "Test Playlist",
            "url": "https://music.youtube.com/playlist?list=test",
            "position": 3,
            "length": 10,
        }
        song = provider._song_to_song(mock_song_data, list_info=list_info)
        assert song.list_name == "Test Playlist"
        assert song.list_position == 3

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_track(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider, mock_song_data: dict
    ):
        """Test getting a track."""
        mock_client = MagicMock()
        mock_song_response = {
            "videoDetails": {
                "videoId": "abc123",
                "title": "Test Song",
                "author": "Test Artist",
                "lengthSeconds": "225",
                "thumbnail": {
                    "thumbnails": [
                        {"url": "https://example.com/thumb.jpg", "width": 640, "height": 640}
                    ]
                },
            },
            "microformat": {
                "microformatDataRenderer": {
                    "artistNames": "Test Artist",
                }
            },
        }
        mock_client.get_song.return_value = mock_song_response
        provider._client = mock_client

        song = await provider.get_track("https://music.youtube.com/watch?v=abc123")

        assert isinstance(song, Song)
        assert song.platform_id == "abc123"
        mock_client.get_song.assert_called_once_with("abc123")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_track_invalid_url(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://music.youtube.com/playlist?list=abc")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_track_not_found(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting track that doesn't exist."""
        mock_client = MagicMock()
        mock_client.get_song.return_value = None
        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://music.youtube.com/watch?v=invalid")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_track_exception(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting track with exception."""
        mock_client = MagicMock()
        mock_client.get_song.side_effect = Exception("API error")
        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://music.youtube.com/watch?v=abc123")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_album(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider, mock_album_data: dict
    ):
        """Test getting an album."""
        mock_client = MagicMock()
        mock_client.get_album.return_value = mock_album_data
        provider._client = mock_client

        song_list = await provider.get_album("https://music.youtube.com/browse/MPREb_abc")

        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Album"
        assert len(song_list.songs) == 2
        mock_client.get_album.assert_called_once_with("MPREb_abc")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_album_invalid_url(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://music.youtube.com/watch?v=abc")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_album_not_found(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting album that doesn't exist."""
        mock_client = MagicMock()
        mock_client.get_album.return_value = None
        provider._client = mock_client

        with pytest.raises(SourceProviderError):
            await provider.get_album("https://music.youtube.com/browse/invalid")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_playlist(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider, mock_playlist_data: dict
    ):
        """Test getting a playlist."""
        mock_client = MagicMock()
        mock_client.get_playlist.return_value = mock_playlist_data
        provider._client = mock_client

        song_list = await provider.get_playlist(
            "https://music.youtube.com/playlist?list=PLabc123"
        )

        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Playlist"
        assert len(song_list.songs) == 1
        mock_client.get_playlist.assert_called_once()

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_playlist_invalid_url(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider
    ):
        """Test getting playlist with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_playlist("https://music.youtube.com/watch?v=abc")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_playlist_skips_tracks_without_video_id(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider, mock_playlist_data: dict
    ):
        """Test getting playlist skips tracks without video ID."""
        mock_playlist_data["tracks"].append(
            {"title": "Invalid Track", "artists": [{"name": "Artist"}]}
        )
        mock_client = MagicMock()
        mock_client.get_playlist.return_value = mock_playlist_data
        provider._client = mock_client

        song_list = await provider.get_playlist(
            "https://music.youtube.com/playlist?list=PLabc123"
        )
        assert len(song_list.songs) == 1  # Invalid track skipped

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_artist(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider, mock_artist_data: dict
    ):
        """Test getting artist tracks."""
        mock_client = MagicMock()
        mock_client.get_artist.return_value = mock_artist_data
        provider._client = mock_client

        # Mock get_album
        mock_album = SongList(
            name="Album 1",
            url="https://music.youtube.com/browse/album1",
            platform=Platform.YOUTUBE_MUSIC,
            urls=("https://music.youtube.com/watch?v=album_track1",),
            songs=(
                Song(
                    name="Album Track 1",
                    artists=["Test Artist"],
                    artist="Test Artist",
                    duration=200,
                    platform=Platform.YOUTUBE_MUSIC,
                    platform_id="album_track1",
                    url="https://music.youtube.com/watch?v=album_track1",
                ),
            ),
        )

        with patch.object(provider, "get_album", return_value=mock_album):
            song_list = await provider.get_artist("https://music.youtube.com/channel/UCabc123")

            assert isinstance(song_list, SongList)
            assert song_list.name == "Test Artist"
            assert len(song_list.songs) >= 1

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_get_artist_invalid_url(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider
    ):
        """Test getting artist with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_artist("https://music.youtube.com/watch?v=abc")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_search(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test searching for tracks."""
        mock_client = MagicMock()
        mock_results = [
            {
                "videoId": "result1",
                "title": "Result 1",
                "artists": [{"name": "Artist 1"}],
                "duration": "3:30",
            }
        ]
        mock_client.search.return_value = mock_results
        provider._client = mock_client

        results = await provider.search("test query")

        assert len(results) == 1
        assert isinstance(results[0], Song)
        assert results[0].name == "Result 1"
        mock_client.search.assert_called_once()

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_search_with_limit(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test searching with limit."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        provider._client = mock_client

        await provider.search("test query", limit=5)

        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["limit"] == 5

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_search_skips_results_without_video_id(
        self, mock_ytmusic_class, provider: YouTubeMusicProvider
    ):
        """Test search skips results without video ID."""
        mock_client = MagicMock()
        mock_results = [
            {"videoId": "valid", "title": "Valid", "artists": [{"name": "Artist"}]},
            {"title": "Invalid", "artists": [{"name": "Artist"}]},
        ]
        mock_client.search.return_value = mock_results
        provider._client = mock_client

        results = await provider.search("test query")
        assert len(results) == 1

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    async def test_search_exception(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test search with exception returns empty list."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API error")
        provider._client = mock_client

        results = await provider.search("test query")
        assert results == []

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    def test_get_client_without_auth(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting client without auth file."""
        client = provider._get_client()
        assert client is not None
        mock_ytmusic_class.assert_called_once_with()

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    def test_get_client_with_auth(self, mock_ytmusic_class):
        """Test getting client with auth file."""
        provider = YouTubeMusicProvider(auth_file="auth.json")
        client = provider._get_client()
        assert client is not None
        mock_ytmusic_class.assert_called_once_with("auth.json")

    @patch("spotdl_core.providers.sources.ytmusic.YTMusic")
    def test_get_client_cached(self, mock_ytmusic_class, provider: YouTubeMusicProvider):
        """Test getting cached client."""
        client1 = provider._get_client()
        client2 = provider._get_client()
        assert client1 is client2
        assert mock_ytmusic_class.call_count == 1
