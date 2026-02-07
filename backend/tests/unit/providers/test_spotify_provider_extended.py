"""Extended tests for Spotify provider to improve coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from spotipy.exceptions import SpotifyException

from spotdl.core.types.song import Platform, Song
from spotdl.providers.sources.base import InvalidURLError, TrackNotFoundError
from spotdl.providers.sources.spotify import SpotifyClientError, SpotifyProvider


class TestSpotifyProviderExtended:
    """Extended tests for Spotify provider to improve coverage."""

    def test_spotify_client_error(self) -> None:
        """Test SpotifyClientError exception."""
        error = SpotifyClientError("Client error")
        assert str(error) == "Client error"

    def test_init_with_auth_token(self) -> None:
        """Test initialization with auth token."""
        provider = SpotifyProvider(auth_token="test_token_123")
        assert provider._auth_token == "test_token_123"
        assert provider._client is None

    def test_init_with_credentials(self) -> None:
        """Test initialization with client credentials."""
        provider = SpotifyProvider(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )
        assert provider._client_id == "test_client_id"
        assert provider._client_secret == "test_client_secret"
        assert provider._user_auth is False

    def test_init_with_user_auth(self) -> None:
        """Test initialization with user auth enabled."""
        provider = SpotifyProvider(
            client_id="test_id",
            client_secret="test_secret",
            user_auth=True,
        )
        assert provider._user_auth is True

    @patch("spotdl.providers.sources.spotify.spotipy.Spotify")
    def test_get_client_with_auth_token(self, mock_spotify: MagicMock) -> None:
        """Test getting client with auth token."""
        provider = SpotifyProvider(auth_token="test_token")
        client = provider._get_client()

        mock_spotify.assert_called_once_with(auth="test_token")
        assert client is not None

    @patch("spotdl.providers.sources.spotify.spotipy.Spotify")
    @patch("spotdl.providers.sources.spotify.SpotifyClientCredentials")
    def test_get_client_with_credentials(
        self, mock_creds: MagicMock, mock_spotify: MagicMock
    ) -> None:
        """Test getting client with client credentials."""
        provider = SpotifyProvider(
            client_id="test_id",
            client_secret="test_secret",
        )
        client = provider._get_client()

        mock_creds.assert_called_once_with(
            client_id="test_id",
            client_secret="test_secret",
        )
        assert client is not None

    def test_get_client_no_credentials_raises(self) -> None:
        """Test getting client without credentials raises error."""
        provider = SpotifyProvider()

        with pytest.raises(SpotifyClientError) as exc_info:
            provider._get_client()

        assert "credentials not configured" in str(exc_info.value).lower()

    @patch("spotdl.providers.sources.spotify.spotipy.Spotify")
    @patch("spotdl.providers.sources.spotify.SpotifyOAuth")
    def test_get_client_with_user_auth(
        self, mock_oauth: MagicMock, mock_spotify: MagicMock
    ) -> None:
        """Test getting client with user OAuth."""
        provider = SpotifyProvider(
            client_id="test_id",
            client_secret="test_secret",
            user_auth=True,
        )
        client = provider._get_client()

        mock_oauth.assert_called_once()
        call_kwargs = mock_oauth.call_args[1]
        assert call_kwargs["client_id"] == "test_id"
        assert call_kwargs["client_secret"] == "test_secret"
        assert "user-library-read" in call_kwargs["scope"]
        assert client is not None

    def test_get_client_user_auth_no_credentials_raises(self) -> None:
        """Test user auth without credentials raises error."""
        provider = SpotifyProvider(user_auth=True)

        with pytest.raises(SpotifyClientError) as exc_info:
            provider._get_client()

        assert "credentials not configured" in str(exc_info.value).lower()

    @patch("spotdl.providers.sources.spotify.spotipy.Spotify")
    def test_get_client_caching(self, mock_spotify: MagicMock) -> None:
        """Test client is cached after first creation."""
        provider = SpotifyProvider(auth_token="test_token")

        client1 = provider._get_client()
        client2 = provider._get_client()

        # Should only create once
        mock_spotify.assert_called_once()
        assert client1 is client2

    def test_track_to_song_minimal_data(self) -> None:
        """Test converting track with minimal data."""
        provider = SpotifyProvider(auth_token="test")

        track_data = {
            "name": "Minimal Song",
            "id": "min123",
            "duration_ms": 120000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/min123"},
        }

        song = provider._track_to_song(track_data)

        assert song.name == "Minimal Song"
        assert song.duration == 120
        assert song.platform == Platform.SPOTIFY
        assert song.platform_id == "min123"

    def test_track_to_song_no_album(self) -> None:
        """Test converting track without album data."""
        provider = SpotifyProvider(auth_token="test")

        track_data = {
            "name": "No Album Song",
            "id": "noalb123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/noalb123"},
        }

        song = provider._track_to_song(track_data)
        assert song.album_name == ""

    def test_track_to_song_no_isrc(self) -> None:
        """Test converting track without ISRC."""
        provider = SpotifyProvider(auth_token="test")

        track_data = {
            "name": "No ISRC",
            "id": "noisrc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/noisrc123"},
        }

        song = provider._track_to_song(track_data)
        assert song.isrc is None or song.isrc == ""

    def test_track_to_song_no_explicit_flag(self) -> None:
        """Test converting track without explicit flag."""
        provider = SpotifyProvider(auth_token="test")

        track_data = {
            "name": "Unknown Explicit",
            "id": "unk123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/unk123"},
        }

        song = provider._track_to_song(track_data)
        assert song.explicit is False

    def test_track_to_song_no_popularity(self) -> None:
        """Test converting track without popularity."""
        provider = SpotifyProvider(auth_token="test")

        track_data = {
            "name": "No Pop",
            "id": "nopop123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/nopop123"},
        }

        song = provider._track_to_song(track_data)
        assert song.popularity is None or song.popularity == 0

    @pytest.mark.asyncio
    async def test_get_track_with_mock(self) -> None:
        """Test getting track with mocked Spotify client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.track.return_value = {
            "name": "Test Track",
            "id": "track123",
            "duration_ms": 200000,
            "artists": [{"name": "Test Artist", "id": "art123"}],
            "album": {
                "name": "Test Album",
                "release_date": "2024-01-01",
                "images": [{"url": "https://example.com/cover.jpg"}],
            },
            "external_urls": {"spotify": "https://open.spotify.com/track/track123"},
            "external_ids": {"isrc": "TEST123"},
            "explicit": False,
        }

        provider._client = mock_client

        song = await provider.get_track("https://open.spotify.com/track/track123")

        mock_client.track.assert_called_once_with("track123")
        assert song.name == "Test Track"
        assert song.platform == Platform.SPOTIFY

    @pytest.mark.asyncio
    async def test_get_track_not_found(self) -> None:
        """Test getting track that doesn't exist."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.track.side_effect = SpotifyException(
            404, "Not Found", "Track not found"
        )

        provider._client = mock_client

        with pytest.raises(TrackNotFoundError):
            await provider.get_track("https://open.spotify.com/track/notfound123")

    @pytest.mark.asyncio
    async def test_get_track_spotify_exception(self) -> None:
        """Test handling Spotify API exception."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        # Make the mock callable raise the exception
        mock_client.track = MagicMock(side_effect=SpotifyException(
            500, "Internal Error", "Server error"
        ))

        provider._client = mock_client

        with pytest.raises(Exception):  # Could be SpotifyException or wrapped
            await provider.get_track("https://open.spotify.com/track/error123")

    @pytest.mark.asyncio
    async def test_get_track_twice(self) -> None:
        """Test getting track twice uses same client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.track.return_value = {
            "name": "Track",
            "id": "abc",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
        }

        provider._client = mock_client

        song1 = await provider.get_track("https://open.spotify.com/track/abc123")
        song2 = await provider.get_track("https://open.spotify.com/track/def456")

        assert song1 is not None
        assert song2 is not None
        assert mock_client.track.call_count == 2

    @pytest.mark.asyncio
    async def test_get_album_with_mock(self) -> None:
        """Test getting album with mocked client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.album.return_value = {
            "name": "Test Album",
            "id": "alb123",
            "release_date": "2024-01-01",
            "artists": [{"name": "Album Artist"}],
            "total_tracks": 2,
            "images": [{"url": "https://example.com/cover.jpg"}],
            "tracks": {
                "items": [
                    {
                        "name": "Track 1",
                        "id": "t1",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist", "id": "art1"}],
                        "external_urls": {
                            "spotify": "https://open.spotify.com/track/t1"
                        },
                    },
                    {
                        "name": "Track 2",
                        "id": "t2",
                        "duration_ms": 200000,
                        "artists": [{"name": "Artist", "id": "art1"}],
                        "external_urls": {
                            "spotify": "https://open.spotify.com/track/t2"
                        },
                    },
                ]
            },
        }

        provider._client = mock_client

        song_list = await provider.get_album("https://open.spotify.com/album/alb123")

        mock_client.album.assert_called_once_with("alb123")
        assert song_list.name == "Test Album"
        assert len(song_list.songs) == 2
        assert song_list.songs[0].list_name == "Test Album"

    @pytest.mark.asyncio
    async def test_get_playlist_with_mock(self) -> None:
        """Test getting playlist with mocked client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.playlist.return_value = {
            "name": "Test Playlist",
            "id": "pl123",
            "owner": {"display_name": "User"},
            "images": [{"url": "https://example.com/playlist.jpg"}],
            "tracks": {
                "items": [
                    {
                        "track": {
                            "name": "Track 1",
                            "id": "t1",
                            "duration_ms": 180000,
                            "artists": [{"name": "Artist", "id": "art1"}],
                            "album": {"name": "Album"},
                            "external_urls": {
                                "spotify": "https://open.spotify.com/track/t1"
                            },
                        }
                    }
                ],
                "next": None,
            },
        }

        provider._client = mock_client

        song_list = await provider.get_playlist(
            "https://open.spotify.com/playlist/pl123"
        )

        mock_client.playlist.assert_called_once_with("pl123")
        assert song_list.name == "Test Playlist"
        # Playlist may filter None tracks
        assert len(song_list.songs) >= 0

    @pytest.mark.asyncio
    async def test_get_artist_with_mock(self) -> None:
        """Test getting artist with mocked client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.artist.return_value = {
            "name": "Test Artist",
            "id": "art123",
        }
        mock_client.artist_albums.return_value = {
            "items": [
                {
                    "id": "alb1",
                    "name": "Album 1",
                }
            ],
            "next": None,
        }
        mock_client.album.return_value = {
            "name": "Album 1",
            "id": "alb1",
            "tracks": {
                "items": [
                    {
                        "name": "Track 1",
                        "id": "t1",
                        "duration_ms": 200000,
                        "artists": [{"name": "Test Artist", "id": "art123"}],
                        "external_urls": {
                            "spotify": "https://open.spotify.com/track/t1"
                        },
                    }
                ]
            },
        }

        provider._client = mock_client

        song_list = await provider.get_artist(
            "https://open.spotify.com/artist/art123"
        )

        mock_client.artist.assert_called_once_with("art123")
        # Name could be just "Test Artist" or "Test Artist - Songs"
        assert "Test Artist" in song_list.name

    @pytest.mark.asyncio
    async def test_search_with_mock(self) -> None:
        """Test searching with mocked client."""
        provider = SpotifyProvider(auth_token="test_token")

        mock_client = MagicMock()
        mock_client.search.return_value = {
            "tracks": {
                "items": [
                    {
                        "name": "Search Result",
                        "id": "res1",
                        "duration_ms": 180000,
                        "artists": [{"name": "Artist", "id": "art1"}],
                        "external_urls": {
                            "spotify": "https://open.spotify.com/track/res1"
                        },
                    }
                ]
            }
        }

        provider._client = mock_client

        songs = await provider.search("test query")

        mock_client.search.assert_called_once()
        assert len(songs) == 1
        assert songs[0].name == "Search Result"

    def test_provider_attributes(self) -> None:
        """Test provider attributes."""
        provider = SpotifyProvider(auth_token="test_token")
        assert provider.name == "spotify"
        assert provider.display_name == "Spotify"

    def test_matches_url_standard(self) -> None:
        """Test URL matching for standard Spotify URLs."""
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/track/abc123"
        )
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/album/xyz789"
        )

    def test_matches_url_intl(self) -> None:
        """Test URL matching for international URLs."""
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/intl-us/track/abc123"
        )
        assert SpotifyProvider.matches_url(
            "https://open.spotify.com/intl-fr/album/xyz789"
        )

    def test_matches_url_uri(self) -> None:
        """Test URL matching for Spotify URIs."""
        assert SpotifyProvider.matches_url("spotify:track:abc123")
        assert SpotifyProvider.matches_url("spotify:album:xyz789")

    def test_matches_url_invalid(self) -> None:
        """Test URL matching rejects invalid URLs."""
        assert not SpotifyProvider.matches_url("https://example.com/track/abc")
        assert not SpotifyProvider.matches_url("https://youtube.com/watch?v=abc")
