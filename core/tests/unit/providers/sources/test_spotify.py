"""Tests for Spotify source provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import spotipy

from spotdl_core.providers.sources.spotify import (
    SPOTIFY_URL_PATTERNS,
    SpotifyClientError,
    SpotifyProvider,
)
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProviderError,
    TrackNotFoundError,
)
from spotdl_core.types import Platform, Song, SongList


class TestSpotifyClientError:
    """Test SpotifyClientError exception."""

    def test_spotify_client_error(self):
        """Test creating SpotifyClientError."""
        error = SpotifyClientError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, SourceProviderError)


class TestSpotifyProvider:
    """Test SpotifyProvider class."""

    @pytest.fixture
    def provider(self) -> SpotifyProvider:
        """Create a Spotify provider."""
        return SpotifyProvider(client_id="test_id", client_secret="test_secret")

    @pytest.fixture
    def mock_track_data(self) -> dict:
        """Create mock track data."""
        return {
            "id": "track123",
            "name": "Test Track",
            "duration_ms": 180000,
            "explicit": False,
            "popularity": 75,
            "artists": [{"id": "artist123", "name": "Test Artist"}],
            "album": {
                "id": "album123",
                "name": "Test Album",
                "album_type": "album",
                "total_tracks": 12,
                "release_date": "2023-01-15",
                "images": [{"url": "https://example.com/cover.jpg", "width": 640, "height": 640}],
                "artists": [{"name": "Album Artist"}],
                "label": "Test Label",
                "copyrights": [{"text": "2023 Test Records"}],
                "genres": [],
            },
            "disc_number": 1,
            "track_number": 3,
            "external_urls": {"spotify": "https://open.spotify.com/track/track123"},
            "external_ids": {"isrc": "USRC12345678"},
        }

    @pytest.fixture
    def mock_artist_data(self) -> dict:
        """Create mock artist data."""
        return {
            "id": "artist123",
            "name": "Test Artist",
            "genres": ["pop", "rock"],
            "external_urls": {"spotify": "https://open.spotify.com/artist/artist123"},
        }

    @pytest.fixture
    def mock_album_data(self) -> dict:
        """Create mock album data."""
        return {
            "id": "album123",
            "name": "Test Album",
            "album_type": "album",
            "total_tracks": 2,
            "release_date": "2023-01-15",
            "images": [{"url": "https://example.com/cover.jpg", "width": 640, "height": 640}],
            "artists": [{"id": "artist123", "name": "Album Artist"}],
            "label": "Test Label",
            "copyrights": [{"text": "2023 Test Records"}],
            "genres": ["pop"],
            "external_urls": {"spotify": "https://open.spotify.com/album/album123"},
            "tracks": {
                "items": [
                    {
                        "id": "track1",
                        "name": "Track 1",
                        "duration_ms": 180000,
                        "explicit": False,
                        "artists": [{"id": "artist123", "name": "Test Artist"}],
                        "disc_number": 1,
                        "track_number": 1,
                        "external_urls": {"spotify": "https://open.spotify.com/track/track1"},
                        "external_ids": {"isrc": "USRC11111111"},
                    },
                    {
                        "id": "track2",
                        "name": "Track 2",
                        "duration_ms": 200000,
                        "explicit": True,
                        "artists": [{"id": "artist123", "name": "Test Artist"}],
                        "disc_number": 1,
                        "track_number": 2,
                        "external_urls": {"spotify": "https://open.spotify.com/track/track2"},
                        "external_ids": {"isrc": "USRC22222222"},
                    },
                ],
                "next": None,
            },
        }

    @pytest.fixture
    def mock_playlist_data(self) -> dict:
        """Create mock playlist data."""
        return {
            "id": "playlist123",
            "name": "Test Playlist",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist123"},
            "tracks": {
                "items": [
                    {
                        "track": {
                            "id": "track1",
                            "name": "Track 1",
                            "duration_ms": 180000,
                            "explicit": False,
                            "type": "track",
                            "is_local": False,
                            "artists": [{"id": "artist123", "name": "Test Artist"}],
                            "album": {
                                "id": "album123",
                                "name": "Album 1",
                                "images": [{"url": "https://example.com/cover1.jpg", "width": 640, "height": 640}],
                            },
                            "external_urls": {"spotify": "https://open.spotify.com/track/track1"},
                            "external_ids": {"isrc": "USRC11111111"},
                        }
                    },
                ],
                "next": None,
            },
        }

    def test_provider_init(self, provider: SpotifyProvider):
        """Test provider initialization."""
        assert provider.name == "spotify"
        assert provider.display_name == "Spotify"
        assert len(provider.url_patterns) == 2

    def test_provider_init_with_auth_token(self):
        """Test provider initialization with auth token."""
        provider = SpotifyProvider(auth_token="test_token")
        assert provider._auth_token == "test_token"

    def test_provider_init_with_user_auth(self):
        """Test provider initialization with user auth."""
        provider = SpotifyProvider(
            client_id="test_id", client_secret="test_secret", user_auth=True
        )
        assert provider._user_auth is True

    def test_url_patterns(self):
        """Test URL patterns are defined."""
        assert len(SPOTIFY_URL_PATTERNS) == 2
        # Test standard URL pattern
        assert SPOTIFY_URL_PATTERNS[0].search("https://open.spotify.com/track/abc123")
        assert SPOTIFY_URL_PATTERNS[0].search("https://open.spotify.com/intl-de/track/abc123")
        # Test URI pattern
        assert SPOTIFY_URL_PATTERNS[1].search("spotify:track:abc123")

    def test_extract_id_track(self, provider: SpotifyProvider):
        """Test extracting track ID."""
        resource_type, resource_id = provider._extract_id(
            "https://open.spotify.com/track/abc123"
        )
        assert resource_type == "track"
        assert resource_id == "abc123"

    def test_extract_id_album(self, provider: SpotifyProvider):
        """Test extracting album ID."""
        resource_type, resource_id = provider._extract_id(
            "https://open.spotify.com/album/xyz789"
        )
        assert resource_type == "album"
        assert resource_id == "xyz789"

    def test_extract_id_playlist(self, provider: SpotifyProvider):
        """Test extracting playlist ID."""
        resource_type, resource_id = provider._extract_id("spotify:playlist:abc123")
        assert resource_type == "playlist"
        assert resource_id == "abc123"

    def test_extract_id_invalid_url(self, provider: SpotifyProvider):
        """Test extracting ID from invalid URL."""
        with pytest.raises(InvalidURLError):
            provider._extract_id("https://invalid.com/track/abc")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    def test_get_client_with_credentials(self, mock_spotify, provider: SpotifyProvider):
        """Test getting client with client credentials."""
        client = provider._get_client()
        assert client is not None
        assert provider._client is not None

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    def test_get_client_cached(self, mock_spotify, provider: SpotifyProvider):
        """Test getting cached client."""
        client1 = provider._get_client()
        client2 = provider._get_client()
        assert client1 is client2

    def test_track_to_song_minimal(self, provider: SpotifyProvider, mock_track_data: dict):
        """Test converting minimal track data to song."""
        song = provider._track_to_song(mock_track_data)
        assert isinstance(song, Song)
        assert song.name == "Test Track"
        assert song.artists == ["Test Artist"]
        assert song.artist == "Test Artist"
        assert song.duration == 180
        assert song.platform == Platform.SPOTIFY
        assert song.platform_id == "track123"
        assert song.album_name == "Test Album"
        assert song.isrc == "USRC12345678"

    def test_track_to_song_with_artist_data(
        self, provider: SpotifyProvider, mock_track_data: dict, mock_artist_data: dict
    ):
        """Test converting track data with artist data."""
        song = provider._track_to_song(mock_track_data, artist_data=mock_artist_data)
        assert "pop" in song.genres or "rock" in song.genres

    def test_track_to_song_with_list_info(self, provider: SpotifyProvider, mock_track_data: dict):
        """Test converting track data with list info."""
        list_info = {
            "name": "Test Playlist",
            "url": "https://open.spotify.com/playlist/test",
            "position": 5,
            "length": 20,
        }
        song = provider._track_to_song(mock_track_data, list_info=list_info)
        assert song.list_name == "Test Playlist"
        assert song.list_url == "https://open.spotify.com/playlist/test"
        assert song.list_position == 5
        assert song.list_length == 20

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_track(
        self, mock_spotify_class, provider: SpotifyProvider, mock_track_data: dict, mock_artist_data: dict
    ):
        """Test getting a track."""
        mock_client = MagicMock()
        mock_client.track.return_value = mock_track_data
        mock_client.artist.return_value = mock_artist_data
        mock_client.album.return_value = mock_track_data["album"]
        provider._client = mock_client

        song = await provider.get_track("https://open.spotify.com/track/track123")

        assert isinstance(song, Song)
        assert song.name == "Test Track"
        assert song.platform_id == "track123"
        mock_client.track.assert_called_once_with("track123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_track_invalid_url(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting track with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_track("https://open.spotify.com/album/abc123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_track_not_found(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting track that doesn't exist."""
        mock_client = MagicMock()
        mock_client.track.return_value = None
        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://open.spotify.com/track/invalid")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_track_invalid_track(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting track with invalid data."""
        mock_client = MagicMock()
        mock_client.track.return_value = {"id": "test", "name": "", "duration_ms": 0}
        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://open.spotify.com/track/test")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_track_spotify_exception(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting track with Spotify API exception."""
        mock_client = MagicMock()
        mock_client.track.side_effect = spotipy.SpotifyException(404, -1, "Not found")
        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://open.spotify.com/track/track123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_album(
        self, mock_spotify_class, provider: SpotifyProvider, mock_album_data: dict
    ):
        """Test getting an album."""
        mock_client = MagicMock()
        mock_client.album.return_value = mock_album_data
        provider._client = mock_client

        song_list = await provider.get_album("https://open.spotify.com/album/album123")

        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Album"
        assert len(song_list.songs) == 2
        assert song_list.songs[0].name == "Track 1"
        assert song_list.songs[1].name == "Track 2"
        mock_client.album.assert_called_once_with("album123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_album_invalid_url(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting album with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_album("https://open.spotify.com/track/abc123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_album_not_found(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting album that doesn't exist."""
        mock_client = MagicMock()
        mock_client.album.return_value = None
        provider._client = mock_client

        with pytest.raises(SourceProviderError):
            await provider.get_album("https://open.spotify.com/album/invalid")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_album_with_pagination(
        self, mock_spotify_class, provider: SpotifyProvider, mock_album_data: dict
    ):
        """Test getting album with pagination."""
        mock_client = MagicMock()
        # First page
        first_page = mock_album_data.copy()
        first_page["tracks"]["next"] = "next_url"
        # Second page
        second_page = {
            "items": [
                {
                    "id": "track3",
                    "name": "Track 3",
                    "duration_ms": 190000,
                    "explicit": False,
                    "artists": [{"id": "artist123", "name": "Test Artist"}],
                    "disc_number": 1,
                    "track_number": 3,
                    "external_urls": {"spotify": "https://open.spotify.com/track/track3"},
                    "external_ids": {"isrc": "USRC33333333"},
                }
            ],
            "next": None,
        }

        mock_client.album.return_value = first_page
        mock_client.next.return_value = second_page
        provider._client = mock_client

        song_list = await provider.get_album("https://open.spotify.com/album/album123")
        assert len(song_list.songs) == 3

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_album_skips_local_tracks(
        self, mock_spotify_class, provider: SpotifyProvider, mock_album_data: dict
    ):
        """Test getting album skips local tracks."""
        mock_album_data["tracks"]["items"].append(
            {
                "id": None,
                "is_local": True,
                "name": "Local Track",
            }
        )
        mock_client = MagicMock()
        mock_client.album.return_value = mock_album_data
        provider._client = mock_client

        song_list = await provider.get_album("https://open.spotify.com/album/album123")
        assert len(song_list.songs) == 2  # Local track should be skipped

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_playlist(
        self, mock_spotify_class, provider: SpotifyProvider, mock_playlist_data: dict
    ):
        """Test getting a playlist."""
        mock_client = MagicMock()
        mock_client.playlist.return_value = mock_playlist_data
        provider._client = mock_client

        song_list = await provider.get_playlist("https://open.spotify.com/playlist/playlist123")

        assert isinstance(song_list, SongList)
        assert song_list.name == "Test Playlist"
        assert len(song_list.songs) == 1
        mock_client.playlist.assert_called_once_with("playlist123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_playlist_invalid_url(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting playlist with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_playlist("https://open.spotify.com/track/abc123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_playlist_skips_local_tracks(
        self, mock_spotify_class, provider: SpotifyProvider, mock_playlist_data: dict
    ):
        """Test getting playlist skips local and invalid tracks."""
        mock_playlist_data["tracks"]["items"].extend([
            {"track": {"is_local": True}},
            {"track": None},
            {"track": {"type": "episode", "is_local": False}},
        ])
        mock_client = MagicMock()
        mock_client.playlist.return_value = mock_playlist_data
        provider._client = mock_client

        song_list = await provider.get_playlist("https://open.spotify.com/playlist/playlist123")
        assert len(song_list.songs) == 1

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_artist(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting artist tracks."""
        mock_client = MagicMock()
        mock_artist = {
            "id": "artist123",
            "name": "Test Artist",
            "external_urls": {"spotify": "https://open.spotify.com/artist/artist123"},
        }
        mock_albums = {
            "items": [
                {
                    "id": "album1",
                    "name": "Album 1",
                    "external_urls": {"spotify": "https://open.spotify.com/album/album1"},
                }
            ],
            "next": None,
        }

        mock_client.artist.return_value = mock_artist
        mock_client.artist_albums.return_value = mock_albums
        provider._client = mock_client

        # Mock get_album to return a song list
        async def mock_get_album(url):
            return SongList(
                name="Album 1",
                url=url,
                platform=Platform.SPOTIFY,
                urls=("https://open.spotify.com/track/track1",),
                songs=(
                    Song(
                        name="Track 1",
                        artists=["Test Artist"],
                        artist="Test Artist",
                        duration=180,
                        platform=Platform.SPOTIFY,
                        platform_id="track1",
                        url="https://open.spotify.com/track/track1",
                    ),
                ),
            )

        with patch.object(provider, "get_album", side_effect=mock_get_album):
            song_list = await provider.get_artist("https://open.spotify.com/artist/artist123")

            assert isinstance(song_list, SongList)
            assert song_list.name == "Test Artist"
            assert len(song_list.songs) >= 1

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_get_artist_invalid_url(self, mock_spotify_class, provider: SpotifyProvider):
        """Test getting artist with invalid URL."""
        with pytest.raises(InvalidURLError):
            await provider.get_artist("https://open.spotify.com/track/abc123")

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_search(self, mock_spotify_class, provider: SpotifyProvider):
        """Test searching for tracks."""
        mock_client = MagicMock()
        mock_results = {
            "tracks": {
                "items": [
                    {
                        "id": "track1",
                        "name": "Result 1",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist 1"}],
                        "album": {
                            "name": "Album 1",
                            "images": [],
                        },
                        "external_urls": {"spotify": "https://open.spotify.com/track/track1"},
                        "external_ids": {},
                    }
                ]
            }
        }
        mock_client.search.return_value = mock_results
        provider._client = mock_client

        results = await provider.search("test query")

        assert len(results) == 1
        assert isinstance(results[0], Song)
        assert results[0].name == "Result 1"
        mock_client.search.assert_called_once()

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_search_with_limit(self, mock_spotify_class, provider: SpotifyProvider):
        """Test searching with limit."""
        mock_client = MagicMock()
        mock_results = {"tracks": {"items": []}}
        mock_client.search.return_value = mock_results
        provider._client = mock_client

        await provider.search("test query", limit=5)

        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["limit"] == 5

    @patch("spotdl_core.providers.sources.spotify.spotipy.Spotify")
    async def test_search_exception(self, mock_spotify_class, provider: SpotifyProvider):
        """Test search with exception returns empty list."""
        mock_client = MagicMock()
        mock_client.search.side_effect = spotipy.SpotifyException(500, -1, "Server error")
        provider._client = mock_client

        results = await provider.search("test query")
        assert results == []
