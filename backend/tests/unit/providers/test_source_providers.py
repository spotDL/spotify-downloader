"""Tests for source providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.types.song import Platform, Song
from spotdl.providers.sources.base import InvalidURLError, TrackNotFoundError
from spotdl.providers.sources.deezer import DeezerProvider
from spotdl.providers.sources.spotify import SpotifyProvider
from spotdl.providers.sources.ytmusic import YouTubeMusicProvider


class TestSpotifyProvider:
    """Tests for Spotify provider."""

    def test_extract_id_track(self) -> None:
        """Test extracting track ID from Spotify URL."""
        result = SpotifyProvider._extract_id("https://open.spotify.com/track/abc123")
        assert result == ("track", "abc123")

    def test_extract_id_album(self) -> None:
        """Test extracting album ID from Spotify URL."""
        result = SpotifyProvider._extract_id("https://open.spotify.com/album/xyz789")
        assert result == ("album", "xyz789")

    def test_extract_id_playlist(self) -> None:
        """Test extracting playlist ID from Spotify URL."""
        result = SpotifyProvider._extract_id("https://open.spotify.com/playlist/list123")
        assert result == ("playlist", "list123")

    def test_extract_id_artist(self) -> None:
        """Test extracting artist ID from Spotify URL."""
        result = SpotifyProvider._extract_id("https://open.spotify.com/artist/art456")
        assert result == ("artist", "art456")

    def test_extract_id_intl_url(self) -> None:
        """Test extracting ID from international URL."""
        result = SpotifyProvider._extract_id("https://open.spotify.com/intl-us/track/abc123")
        assert result == ("track", "abc123")

    def test_extract_id_uri(self) -> None:
        """Test extracting ID from Spotify URI."""
        result = SpotifyProvider._extract_id("spotify:track:abc123")
        assert result == ("track", "abc123")

    def test_extract_id_invalid(self) -> None:
        """Test extracting ID from invalid URL raises error."""
        with pytest.raises(InvalidURLError):
            SpotifyProvider._extract_id("https://example.com/track/123")

    def test_track_to_song(self) -> None:
        """Test converting Spotify track data to Song."""
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist 1", "id": "art1"}, {"name": "Artist 2", "id": "art2"}],
            "album": {
                "name": "Test Album",
                "id": "alb123",
                "album_type": "album",
                "release_date": "2024-01-15",
                "total_tracks": 10,
                "artists": [{"name": "Artist 1"}],
                "images": [{"url": "https://example.com/cover.jpg", "width": 640, "height": 640}],
            },
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
            "external_ids": {"isrc": "USABC1234567"},
            "explicit": True,
            "disc_number": 1,
            "track_number": 5,
            "popularity": 75,
        }

        song = provider._track_to_song(track_data)

        assert song.name == "Test Song"
        assert song.artist == "Artist 1"
        assert song.artists == ["Artist 1", "Artist 2"]
        assert song.duration == 180
        assert song.platform == Platform.SPOTIFY
        assert song.platform_id == "abc123"
        assert song.album_name == "Test Album"
        assert song.isrc == "USABC1234567"
        assert song.explicit is True
        assert song.year == 2024

    @pytest.mark.asyncio
    async def test_get_track_invalid_type(self) -> None:
        """Test get_track raises error for non-track URL."""
        provider = SpotifyProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://open.spotify.com/album/abc123")


class TestYouTubeMusicProvider:
    """Tests for YouTube Music provider."""

    def test_extract_video_id(self) -> None:
        """Test extracting video ID from URL."""
        result = YouTubeMusicProvider._extract_video_id(
            "https://music.youtube.com/watch?v=abc123xyz"
        )
        assert result == "abc123xyz"

    def test_extract_video_id_with_params(self) -> None:
        """Test extracting video ID from URL with extra params."""
        result = YouTubeMusicProvider._extract_video_id(
            "https://music.youtube.com/watch?v=abc123xyz&list=PLxyz"
        )
        assert result == "abc123xyz"

    def test_extract_video_id_no_match(self) -> None:
        """Test extracting video ID from URL without v= param returns None."""
        result = YouTubeMusicProvider._extract_video_id("https://music.youtube.com/playlist?list=abc")
        assert result is None

    def test_extract_playlist_id(self) -> None:
        """Test extracting playlist ID from URL."""
        result = YouTubeMusicProvider._extract_playlist_id(
            "https://music.youtube.com/playlist?list=PLabc123"
        )
        assert result == "PLabc123"

    def test_extract_channel_id(self) -> None:
        """Test extracting channel ID from URL."""
        result = YouTubeMusicProvider._extract_channel_id(
            "https://music.youtube.com/channel/UCabc123"
        )
        assert result == "UCabc123"

    def test_song_to_song(self) -> None:
        """Test converting YouTube Music song data to Song."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123xyz",
            "title": "Test Song",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "album": {"name": "Test Album"},
            "duration": "3:45",
            "thumbnails": [
                {"url": "https://example.com/thumb.jpg", "width": 226, "height": 226}
            ],
            "isExplicit": True,
            "year": "2024",
        }

        song = provider._song_to_song(song_data)

        assert song.name == "Test Song"
        assert song.artist == "Artist 1"
        assert song.artists == ["Artist 1", "Artist 2"]
        assert song.duration == 225  # 3*60 + 45
        assert song.platform == Platform.YOUTUBE_MUSIC
        assert song.platform_id == "abc123xyz"
        assert song.album_name == "Test Album"
        assert song.explicit is True
        assert song.year == 2024

    def test_song_to_song_duration_seconds(self) -> None:
        """Test converting song data with duration_seconds field."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "xyz789",
            "title": "Another Song",
            "duration_seconds": 200,
        }

        song = provider._song_to_song(song_data)
        assert song.duration == 200

    @pytest.mark.asyncio
    async def test_get_track_invalid_url(self) -> None:
        """Test get_track raises error for URL without video ID."""
        provider = YouTubeMusicProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://music.youtube.com/playlist?list=abc")


class TestDeezerProvider:
    """Tests for Deezer provider."""

    def test_extract_id_track(self) -> None:
        """Test extracting track ID from Deezer URL."""
        result = DeezerProvider._extract_id("https://www.deezer.com/track/123456789")
        assert result == ("track", "123456789")

    def test_extract_id_album(self) -> None:
        """Test extracting album ID from Deezer URL."""
        result = DeezerProvider._extract_id("https://deezer.com/album/987654321")
        assert result == ("album", "987654321")

    def test_extract_id_with_locale(self) -> None:
        """Test extracting ID from URL with locale."""
        result = DeezerProvider._extract_id("https://www.deezer.com/en/track/123456789")
        assert result == ("track", "123456789")

    def test_extract_id_invalid(self) -> None:
        """Test extracting ID from invalid URL returns None."""
        result = DeezerProvider._extract_id("https://example.com/track/123")
        assert result is None

    def test_track_to_song(self) -> None:
        """Test converting Deezer track data to Song."""
        provider = DeezerProvider()

        track_data = {
            "id": 123456789,
            "title": "Test Song",
            "duration": 200,
            "artist": {"id": 1, "name": "Main Artist"},
            "contributors": [{"name": "Main Artist"}, {"name": "Featured Artist"}],
            "album": {
                "id": 987654,
                "title": "Test Album",
                "cover_xl": "https://example.com/cover.jpg",
                "release_date": "2024-06-15",
                "record_type": "album",
            },
            "link": "https://www.deezer.com/track/123456789",
            "isrc": "USABC1234567",
            "explicit_lyrics": True,
            "disk_number": 1,
            "track_position": 3,
        }

        song = provider._track_to_song(track_data)

        assert song.name == "Test Song"
        assert song.artist == "Main Artist"
        assert song.artists == ["Main Artist", "Featured Artist"]
        assert song.duration == 200
        assert song.platform == Platform.DEEZER
        assert song.platform_id == "123456789"
        assert song.album_name == "Test Album"
        assert song.isrc == "USABC1234567"
        assert song.explicit is True
        assert song.year == 2024

    @pytest.mark.asyncio
    async def test_get_track_invalid_type(self) -> None:
        """Test get_track raises error for non-track URL."""
        provider = DeezerProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://www.deezer.com/album/123456")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        provider = DeezerProvider()
        # Should not raise even if no client was created
        await provider.close()


class TestProviderURLPatterns:
    """Tests for provider URL pattern matching."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://open.spotify.com/track/abc123",
            "https://open.spotify.com/intl-us/track/abc123",
            "spotify:track:abc123",
        ],
    )
    def test_spotify_matches(self, url: str) -> None:
        """Test Spotify URL matching."""
        assert SpotifyProvider.matches_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://music.youtube.com/watch?v=abc123",
            "https://music.youtube.com/playlist?list=PLabc",
            "https://music.youtube.com/channel/UCabc",
        ],
    )
    def test_ytmusic_matches(self, url: str) -> None:
        """Test YouTube Music URL matching."""
        assert YouTubeMusicProvider.matches_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.deezer.com/track/123456",
            "https://deezer.com/album/789012",
            "https://www.deezer.com/en/playlist/345678",
        ],
    )
    def test_deezer_matches(self, url: str) -> None:
        """Test Deezer URL matching."""
        assert DeezerProvider.matches_url(url)
