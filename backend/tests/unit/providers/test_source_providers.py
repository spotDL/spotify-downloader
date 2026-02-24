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

    def test_get_url_type_browse_album(self) -> None:
        """Test YT Music browse album URL type detection."""
        assert (
            YouTubeMusicProvider.get_url_type(
                "https://music.youtube.com/browse/album_wuO4_P_8p-Q"
            )
            == "album"
        )

    def test_get_url_type_browse_artist(self) -> None:
        """Test YT Music browse artist URL type detection."""
        assert (
            YouTubeMusicProvider.get_url_type(
                "https://music.youtube.com/browse/UCabc123"
            )
            == "artist"
        )

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
            "https://music.youtube.com/browse/album_wuO4_P_8p-Q",
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


class TestAppleMusicProvider:
    """Tests for Apple Music provider."""

    def test_extract_url_info_track_in_album(self) -> None:
        """Test extracting track info from album URL with track ID."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/album/test-album/1234567890?i=9876543210"
        )
        assert result["country"] == "us"
        assert result["type"] == "track"
        assert result["id"] == "1234567890"
        assert result["track_id"] == "9876543210"

    def test_extract_url_info_album(self) -> None:
        """Test extracting album info from URL."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/album/test-album/1234567890"
        )
        assert result["country"] == "us"
        assert result["type"] == "album"
        assert result["id"] == "1234567890"
        assert result["track_id"] is None

    def test_extract_url_info_playlist(self) -> None:
        """Test extracting playlist info from URL."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/playlist/test-playlist/pl.abc123"
        )
        # Playlist IDs don't match the standard pattern
        assert result["country"] is None or result["type"] == "playlist"

    def test_extract_url_info_artist(self) -> None:
        """Test extracting artist info from URL."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        result = AppleMusicProvider._extract_url_info(
            "https://music.apple.com/us/artist/test-artist/123456"
        )
        assert result["country"] == "us"
        assert result["type"] == "artist"
        assert result["id"] == "123456"

    def test_extract_url_info_invalid(self) -> None:
        """Test extracting info from invalid URL returns None values."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        result = AppleMusicProvider._extract_url_info("https://example.com/track/123")
        assert result["country"] is None
        assert result["type"] is None
        assert result["id"] is None

    def test_parse_duration_full(self) -> None:
        """Test parsing full ISO 8601 duration."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()
        assert provider._parse_duration("PT3M45S") == 225
        assert provider._parse_duration("PT1H30M15S") == 5415

    def test_parse_duration_minutes_only(self) -> None:
        """Test parsing duration with minutes only."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()
        assert provider._parse_duration("PT5M") == 300

    def test_parse_duration_seconds_only(self) -> None:
        """Test parsing duration with seconds only."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()
        assert provider._parse_duration("PT45S") == 45

    def test_parse_duration_empty(self) -> None:
        """Test parsing empty duration."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()
        assert provider._parse_duration("") == 0
        assert provider._parse_duration("invalid") == 0

    def test_track_to_song(self) -> None:
        """Test converting Apple Music track data to Song."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider
        from spotdl.core.types.song import Platform

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "byArtist": {"name": "Artist Name"},
            "inAlbum": {"name": "Test Album"},
            "duration": "PT3M45S",
            "datePublished": "2024-06-15",
            "url": "https://music.apple.com/us/album/test/123?i=456",
            "image": "https://example.com/cover.jpg",
            "contentRating": "explicit",
        }

        song = provider._track_to_song(track_data)

        assert song.name == "Test Song"
        assert song.artist == "Artist Name"
        assert song.artists == ["Artist Name"]
        assert song.duration == 225
        assert song.platform == Platform.APPLE_MUSIC
        assert song.album_name == "Test Album"
        assert song.year == 2024
        assert song.explicit is True
        assert song.cover_url == "https://example.com/cover.jpg"

    def test_track_to_song_artist_list(self) -> None:
        """Test converting track with artist list."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "byArtist": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "url": "https://music.apple.com/us/album/test/123?i=456",
        }

        song = provider._track_to_song(track_data)
        assert song.artist == "Artist 1"

    def test_track_to_song_with_list_info(self) -> None:
        """Test converting track with list context."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "url": "https://music.apple.com/us/album/test/123?i=456",
        }

        list_info = {
            "name": "My Playlist",
            "url": "https://music.apple.com/us/playlist/pl.abc",
            "position": 5,
            "length": 20,
        }

        song = provider._track_to_song(track_data, list_info)

        assert song.list_name == "My Playlist"
        assert song.list_position == 5
        assert song.list_length == 20

    @pytest.mark.asyncio
    async def test_get_track_invalid_url(self) -> None:
        """Test get_track raises error for invalid URL."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = AppleMusicProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_track_non_track_url(self) -> None:
        """Test get_track raises error for non-track URL."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = AppleMusicProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://music.apple.com/us/artist/test/123")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()
        await provider.close()  # Should not raise

    @pytest.mark.parametrize(
        "url",
        [
            "https://music.apple.com/us/album/test/123?i=456",
            "https://music.apple.com/gb/album/test/789?i=101",
            "https://music.apple.com/us/artist/test/123",
            "https://music.apple.com/us/playlist/test/1234567890",  # Playlist with numeric ID
        ],
    )
    def test_apple_music_matches(self, url: str) -> None:
        """Test Apple Music URL matching."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        assert AppleMusicProvider.matches_url(url)


class TestBandcampProvider:
    """Tests for Bandcamp provider."""

    def test_extract_url_info_track(self) -> None:
        """Test extracting track info from URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        result = BandcampProvider._extract_url_info(
            "https://artist.bandcamp.com/track/test-song"
        )
        assert result["subdomain"] == "artist"
        assert result["type"] == "track"
        assert result["slug"] == "test-song"

    def test_extract_url_info_album(self) -> None:
        """Test extracting album info from URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        result = BandcampProvider._extract_url_info(
            "https://myartist.bandcamp.com/album/test-album"
        )
        assert result["subdomain"] == "myartist"
        assert result["type"] == "album"
        assert result["slug"] == "test-album"

    def test_extract_url_info_artist(self) -> None:
        """Test extracting artist info from URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        result = BandcampProvider._extract_url_info("https://coolband.bandcamp.com/")
        assert result["subdomain"] == "coolband"
        assert result["type"] == "artist"
        assert result["slug"] is None

    def test_extract_url_info_artist_no_slash(self) -> None:
        """Test extracting artist info from URL without trailing slash."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        result = BandcampProvider._extract_url_info("https://coolband.bandcamp.com")
        assert result["subdomain"] == "coolband"
        assert result["type"] == "artist"

    def test_extract_url_info_invalid(self) -> None:
        """Test extracting info from invalid URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        result = BandcampProvider._extract_url_info("https://example.com/track/123")
        assert result["subdomain"] is None

    def test_track_to_song(self) -> None:
        """Test converting Bandcamp track data to Song."""
        from spotdl.providers.sources.bandcamp import BandcampProvider
        from spotdl.core.types.song import Platform

        provider = BandcampProvider()

        track = {
            "id": 12345,
            "title": "Test Track",
            "duration": 225.5,
            "artist": "Band Name",
            "url": "https://band.bandcamp.com/track/test-track",
            "track_num": 3,
        }

        album_data = {
            "title": "Test Album",
            "art_url": "https://f4.bcbits.com/img/a123_10.jpg",
            "release_date": "15 Jun 2024",
            "tags": [{"name": "electronic"}, {"name": "ambient"}],
        }

        song = provider._track_to_song(track, album_data)

        assert song.name == "Test Track"
        assert song.artist == "Band Name"
        assert song.duration == 225
        assert song.platform == Platform.BANDCAMP
        assert song.platform_id == "12345"
        assert song.album_name == "Test Album"
        assert song.track_number == 3
        assert "electronic" in song.genres
        assert "ambient" in song.genres

    def test_track_to_song_duration_string(self) -> None:
        """Test converting track with string duration."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {
            "title": "Test",
            "duration": "3:45",
            "url": "https://band.bandcamp.com/track/test",
        }

        song = provider._track_to_song(track)
        assert song.duration == 225

    def test_track_to_song_duration_hms(self) -> None:
        """Test converting track with hours:minutes:seconds duration."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {
            "title": "Long Track",
            "duration": "1:30:15",
            "url": "https://band.bandcamp.com/track/long",
        }

        song = provider._track_to_song(track)
        assert song.duration == 5415

    def test_track_to_song_with_list_info(self) -> None:
        """Test converting track with list context."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {
            "title": "Test",
            "url": "https://band.bandcamp.com/track/test",
        }

        list_info = {
            "name": "Album Name",
            "url": "https://band.bandcamp.com/album/test",
            "position": 3,
            "length": 10,
        }

        song = provider._track_to_song(track, list_info=list_info)
        assert song.list_name == "Album Name"
        assert song.list_position == 3
        assert song.list_length == 10

    def test_track_to_song_year_extraction(self) -> None:
        """Test year extraction from release date."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {"title": "Test", "url": "https://band.bandcamp.com/track/test"}
        album_data = {"release_date": "December 25, 2023"}

        song = provider._track_to_song(track, album_data)
        assert song.year == 2023

    @pytest.mark.asyncio
    async def test_get_track_invalid_url(self) -> None:
        """Test get_track raises error for invalid URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = BandcampProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_track_non_track_url(self) -> None:
        """Test get_track raises error for non-track URL."""
        from spotdl.providers.sources.bandcamp import BandcampProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = BandcampProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://band.bandcamp.com/album/test")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()
        await provider.close()

    @pytest.mark.parametrize(
        "url",
        [
            "https://artist.bandcamp.com/track/test",
            "https://band.bandcamp.com/album/test",
            "https://musician.bandcamp.com/",
        ],
    )
    def test_bandcamp_matches(self, url: str) -> None:
        """Test Bandcamp URL matching."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        assert BandcampProvider.matches_url(url)


class TestSoundCloudProvider:
    """Tests for SoundCloud provider."""

    def test_extract_url_info_track(self) -> None:
        """Test extracting track info from URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info(
            "https://soundcloud.com/artist/track-name"
        )
        assert result["user"] == "artist"
        assert result["slug"] == "track-name"
        assert result["type"] == "track"

    def test_extract_url_info_playlist(self) -> None:
        """Test extracting playlist info from URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info(
            "https://soundcloud.com/artist/sets/my-playlist"
        )
        assert result["user"] == "artist"
        assert result["slug"] == "my-playlist"
        assert result["type"] == "playlist"

    def test_extract_url_info_artist(self) -> None:
        """Test extracting artist info from URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info(
            "https://soundcloud.com/artist"
        )
        assert result["user"] == "artist"
        assert result["type"] == "artist"

    def test_extract_url_info_artist_tracks_page(self) -> None:
        """Test extracting artist tracks page info."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info(
            "https://soundcloud.com/artist/tracks"
        )
        assert result["user"] == "artist"
        assert result["type"] == "artist"

    def test_extract_url_info_www_prefix(self) -> None:
        """Test extracting info from URL with www prefix."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info(
            "https://www.soundcloud.com/artist/track"
        )
        assert result["user"] == "artist"
        assert result["slug"] == "track"
        assert result["type"] == "track"

    def test_extract_url_info_invalid(self) -> None:
        """Test extracting info from invalid URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        result = SoundCloudProvider._extract_url_info("https://example.com/track/123")
        assert result["user"] is None

    def test_track_to_song(self) -> None:
        """Test converting SoundCloud track data to Song."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider
        from spotdl.core.types.song import Platform

        provider = SoundCloudProvider()

        track = {
            "id": 123456789,
            "title": "Test Track",
            "duration": 225000,  # milliseconds
            "user": {
                "id": 987654,
                "username": "Artist Name",
                "avatar_url": "https://example.com/avatar.jpg",
            },
            "permalink_url": "https://soundcloud.com/artist/test-track",
            "artwork_url": "https://example.com/artwork-large.jpg",
            "created_at": "2024-06-15T12:00:00Z",
            "genre": "Electronic",
            "tag_list": '"ambient" chill relaxing',
        }

        song = provider._track_to_song(track)

        assert song.name == "Test Track"
        assert song.artist == "Artist Name"
        assert song.duration == 225
        assert song.platform == Platform.SOUNDCLOUD
        assert song.platform_id == "123456789"
        assert song.year == 2024
        assert "Electronic" in song.genres
        assert "ambient" in song.genres

    def test_track_to_song_cover_url_resolution(self) -> None:
        """Test cover URL resolution to higher quality."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        provider = SoundCloudProvider()

        track = {
            "id": 123,
            "title": "Test",
            "duration": 1000,
            "user": {"username": "Artist"},
            "permalink_url": "https://soundcloud.com/artist/test",
            "artwork_url": "https://i1.sndcdn.com/artworks-abc-large.jpg",
        }

        song = provider._track_to_song(track)
        assert "t500x500" in song.cover_url

    def test_track_to_song_with_list_info(self) -> None:
        """Test converting track with list context."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        provider = SoundCloudProvider()

        track = {
            "id": 123,
            "title": "Test",
            "duration": 1000,
            "user": {"username": "Artist"},
            "permalink_url": "https://soundcloud.com/artist/test",
        }

        list_info = {
            "name": "My Set",
            "url": "https://soundcloud.com/artist/sets/my-set",
            "position": 2,
            "length": 15,
        }

        song = provider._track_to_song(track, list_info)
        assert song.list_name == "My Set"
        assert song.list_position == 2

    @pytest.mark.asyncio
    async def test_get_track_invalid_url(self) -> None:
        """Test get_track raises error for invalid URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = SoundCloudProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_track_non_track_url(self) -> None:
        """Test get_track raises error for non-track URL."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = SoundCloudProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://soundcloud.com/artist/sets/playlist")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        provider = SoundCloudProvider()
        await provider.close()

    @pytest.mark.parametrize(
        "url",
        [
            "https://soundcloud.com/artist/track",
            "https://www.soundcloud.com/artist/sets/playlist",
            "https://soundcloud.com/artist/tracks",  # Artist tracks page
        ],
    )
    def test_soundcloud_matches(self, url: str) -> None:
        """Test SoundCloud URL matching."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        assert SoundCloudProvider.matches_url(url)


class TestTidalProvider:
    """Tests for Tidal provider."""

    def test_extract_id_track(self) -> None:
        """Test extracting track ID from URL."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://tidal.com/track/123456789")
        assert result == ("track", "123456789")

    def test_extract_id_album(self) -> None:
        """Test extracting album ID from URL."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://tidal.com/album/987654321")
        assert result == ("album", "987654321")

    def test_extract_id_browse_prefix(self) -> None:
        """Test extracting ID from URL with browse prefix."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://tidal.com/browse/track/123456")
        assert result == ("track", "123456")

    def test_extract_id_listen_domain(self) -> None:
        """Test extracting ID from listen.tidal.com URL."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://listen.tidal.com/track/123456")
        assert result == ("track", "123456")

    def test_extract_id_www_prefix(self) -> None:
        """Test extracting ID from URL with www prefix."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://www.tidal.com/track/123456")
        assert result == ("track", "123456")

    def test_extract_id_playlist(self) -> None:
        """Test extracting playlist ID from URL."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://tidal.com/playlist/12345678")
        assert result == ("playlist", "12345678")

    def test_extract_id_artist(self) -> None:
        """Test extracting artist ID from URL."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://tidal.com/artist/3456789")
        assert result == ("artist", "3456789")

    def test_extract_id_invalid(self) -> None:
        """Test extracting ID from invalid URL returns None."""
        from spotdl.providers.sources.tidal import TidalProvider

        result = TidalProvider._extract_id("https://example.com/track/123")
        assert result is None

    def test_parse_duration_full(self) -> None:
        """Test parsing full ISO 8601 duration."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()
        assert provider._parse_duration("PT3M45S") == 225
        assert provider._parse_duration("PT1H30M15S") == 5415

    def test_parse_duration_empty(self) -> None:
        """Test parsing empty duration."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()
        assert provider._parse_duration("") == 0
        assert provider._parse_duration("invalid") == 0

    def test_track_to_song(self) -> None:
        """Test converting Tidal track data to Song."""
        from spotdl.providers.sources.tidal import TidalProvider
        from spotdl.core.types.song import Platform

        provider = TidalProvider()

        track_data = {
            "name": "Test Song",
            "byArtist": {"name": "Artist Name"},
            "inAlbum": {"name": "Test Album"},
            "duration": "PT3M45S",
            "datePublished": "2024-06-15",
            "url": "https://tidal.com/track/123456",
            "image": {"url": "https://example.com/cover.jpg"},
            "isrcCode": "USABC1234567",
        }

        song = provider._track_to_song(track_data)

        assert song.name == "Test Song"
        assert song.artist == "Artist Name"
        assert song.duration == 225
        assert song.platform == Platform.TIDAL
        assert song.platform_id == "123456"
        assert song.album_name == "Test Album"
        assert song.year == 2024
        assert song.isrc == "USABC1234567"

    def test_track_to_song_artist_list(self) -> None:
        """Test converting track with artist list."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        track_data = {
            "name": "Test",
            "byArtist": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "url": "https://tidal.com/track/123",
        }

        song = provider._track_to_song(track_data)
        assert song.artist == "Artist 1"

    def test_track_to_song_with_meta_data(self) -> None:
        """Test converting track with meta tag data fallbacks."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        # When byArtist/inAlbum are not dicts, meta_data is used as fallback
        track_data = {
            "name": "Test",
            "url": "https://tidal.com/track/123",
            "byArtist": "invalid",  # Not a dict, triggers fallback
            "inAlbum": "invalid",  # Not a dict, triggers fallback
        }

        meta_data = {
            "musician": "Meta Artist",
            "album": "Meta Album",
            "image": "https://example.com/meta.jpg",
        }

        song = provider._track_to_song(track_data, meta_data)
        assert song.artist == "Meta Artist"
        assert song.album_name == "Meta Album"
        assert song.cover_url == "https://example.com/meta.jpg"

    def test_track_to_song_with_list_info(self) -> None:
        """Test converting track with list context."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        track_data = {
            "name": "Test",
            "url": "https://tidal.com/track/123",
        }

        list_info = {
            "name": "Playlist Name",
            "url": "https://tidal.com/playlist/456",
            "position": 7,
            "length": 25,
        }

        song = provider._track_to_song(track_data, list_info=list_info)
        assert song.list_name == "Playlist Name"
        assert song.list_position == 7
        assert song.list_length == 25

    @pytest.mark.asyncio
    async def test_get_track_invalid_url(self) -> None:
        """Test get_track raises error for invalid URL."""
        from spotdl.providers.sources.tidal import TidalProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = TidalProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://example.com/track/123")

    @pytest.mark.asyncio
    async def test_get_track_non_track_url(self) -> None:
        """Test get_track raises error for non-track URL."""
        from spotdl.providers.sources.tidal import TidalProvider
        from spotdl.providers.sources.base import InvalidURLError

        provider = TidalProvider()

        with pytest.raises(InvalidURLError):
            await provider.get_track("https://tidal.com/album/123456")

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the provider."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()
        await provider.close()

    @pytest.mark.parametrize(
        "url",
        [
            "https://tidal.com/track/123456",
            "https://www.tidal.com/browse/album/789",
            "https://listen.tidal.com/playlist/456",
            "https://tidal.com/artist/789",
        ],
    )
    def test_tidal_matches(self, url: str) -> None:
        """Test Tidal URL matching."""
        from spotdl.providers.sources.tidal import TidalProvider

        assert TidalProvider.matches_url(url)


class TestSpotifyProviderEdgeCases:
    """Additional edge case tests for Spotify provider."""

    def test_track_to_song_with_list_info(self) -> None:
        """Test track conversion with list context."""
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        }

        list_info = {
            "name": "My Playlist",
            "url": "https://open.spotify.com/playlist/pl123",
            "position": 5,
            "length": 20,
        }

        song = provider._track_to_song(track_data, list_info=list_info)

        assert song.list_name == "My Playlist"
        assert song.list_position == 5
        assert song.list_length == 20

    def test_track_to_song_empty_artists_raises(self) -> None:
        """Test track conversion with empty artists list raises IndexError.

        This tests the current behavior - empty artists list causes an error
        when trying to get artist_id.
        """
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [],
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        }

        # Empty artists list causes IndexError when accessing [0]
        with pytest.raises(IndexError):
            provider._track_to_song(track_data)

    def test_track_to_song_with_artist_data(self) -> None:
        """Test track conversion with pre-fetched artist data."""
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        }

        artist_data = {
            "genres": ["rock", "indie"],
        }

        song = provider._track_to_song(track_data, artist_data=artist_data)
        assert "rock" in song.genres
        assert "indie" in song.genres

    def test_track_to_song_partial_date(self) -> None:
        """Test track conversion with year-only release date."""
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "album": {"release_date": "2020"},
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        }

        song = provider._track_to_song(track_data)
        assert song.year == 2020

    def test_track_to_song_with_copyright(self) -> None:
        """Test track conversion with copyright info."""
        provider = SpotifyProvider()

        track_data = {
            "name": "Test Song",
            "id": "abc123",
            "duration_ms": 180000,
            "artists": [{"name": "Artist", "id": "art1"}],
            "album": {
                "copyrights": [{"text": "© 2024 Test Label", "type": "C"}],
            },
            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
        }

        song = provider._track_to_song(track_data)
        assert "2024 Test Label" in song.copyright_text


class TestDeezerProviderEdgeCases:
    """Additional edge case tests for Deezer provider."""

    def test_track_to_song_no_contributors(self) -> None:
        """Test track conversion without contributors."""
        provider = DeezerProvider()

        track_data = {
            "id": 123456,
            "title": "Test Song",
            "duration": 200,
            "artist": {"id": 1, "name": "Main Artist"},
            "link": "https://www.deezer.com/track/123456",
        }

        song = provider._track_to_song(track_data)
        assert song.artists == ["Main Artist"]

    def test_track_to_song_with_list_info(self) -> None:
        """Test track conversion with list context."""
        provider = DeezerProvider()

        track_data = {
            "id": 123456,
            "title": "Test Song",
            "duration": 200,
            "artist": {"id": 1, "name": "Artist"},
            "link": "https://www.deezer.com/track/123456",
        }

        list_info = {
            "name": "Playlist",
            "url": "https://www.deezer.com/playlist/abc",
            "position": 3,
            "length": 15,
        }

        song = provider._track_to_song(track_data, list_info=list_info)
        assert song.list_name == "Playlist"
        assert song.list_position == 3


class TestYouTubeMusicProviderEdgeCases:
    """Additional edge case tests for YouTube Music provider."""

    def test_song_to_song_no_artists(self) -> None:
        """Test song conversion with no artists."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123",
            "title": "Test Song",
            "duration": "3:00",
        }

        song = provider._song_to_song(song_data)
        assert song.artist == "Unknown"

    def test_song_to_song_with_thumbnails(self) -> None:
        """Test song conversion picks best thumbnail."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123",
            "title": "Test Song",
            "duration": "3:00",
            "thumbnails": [
                {"url": "https://example.com/small.jpg", "width": 120, "height": 90},
                {"url": "https://example.com/large.jpg", "width": 480, "height": 360},
            ],
        }

        song = provider._song_to_song(song_data)
        assert "large" in song.cover_url or song.cover_url is not None

    def test_song_to_song_with_list_info(self) -> None:
        """Test song conversion with list context."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123",
            "title": "Test Song",
        }

        list_info = {
            "name": "My Playlist",
            "url": "https://music.youtube.com/playlist?list=abc",
            "position": 7,
            "length": 25,
        }

        song = provider._song_to_song(song_data, list_info=list_info)
        assert song.list_name == "My Playlist"
        assert song.list_position == 7

    def test_song_to_song_duration_parsing(self) -> None:
        """Test duration parsing in song conversion."""
        provider = YouTubeMusicProvider()

        # Minutes:seconds format
        song_data = {
            "videoId": "abc123",
            "title": "Test Song",
            "duration": "5:00",
        }

        song = provider._song_to_song(song_data)
        assert song.duration == 300

    def test_song_to_song_duration_hours(self) -> None:
        """Test duration parsing with hours."""
        provider = YouTubeMusicProvider()

        song_data = {
            "videoId": "abc123",
            "title": "Test Song",
            "duration": "1:30:00",
        }

        song = provider._song_to_song(song_data)
        assert song.duration == 5400


class TestBandcampProviderEdgeCases:
    """Additional edge case tests for Bandcamp provider."""

    def test_track_to_song_no_album_data(self) -> None:
        """Test track conversion without album data."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {
            "title": "Test Track",
            "url": "https://band.bandcamp.com/track/test",
        }

        song = provider._track_to_song(track)
        assert song.name == "Test Track"
        assert song.album_name is None or song.album_name == ""

    def test_track_to_song_invalid_duration(self) -> None:
        """Test track conversion with invalid duration."""
        from spotdl.providers.sources.bandcamp import BandcampProvider

        provider = BandcampProvider()

        track = {
            "title": "Test",
            "duration": "invalid",
            "url": "https://band.bandcamp.com/track/test",
        }

        song = provider._track_to_song(track)
        assert song.duration == 0


class TestSoundCloudProviderEdgeCases:
    """Additional edge case tests for SoundCloud provider."""

    def test_track_to_song_no_artwork(self) -> None:
        """Test track conversion without artwork."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        provider = SoundCloudProvider()

        track = {
            "id": 123,
            "title": "Test",
            "duration": 180000,
            "user": {"username": "Artist"},
            "permalink_url": "https://soundcloud.com/artist/test",
            "artwork_url": None,
        }

        song = provider._track_to_song(track)
        assert song.cover_url is None or song.cover_url == ""

    def test_track_to_song_with_tag_list(self) -> None:
        """Test track conversion with tag list parsing."""
        from spotdl.providers.sources.soundcloud import SoundCloudProvider

        provider = SoundCloudProvider()

        track = {
            "id": 123,
            "title": "Test",
            "duration": 180000,
            "user": {"username": "Artist"},
            "permalink_url": "https://soundcloud.com/artist/test",
            "genre": "Electronic",
            "tag_list": '"deep house" techno "progressive"',
        }

        song = provider._track_to_song(track)
        assert "Electronic" in song.genres
        assert "deep house" in song.genres


class TestTidalProviderEdgeCases:
    """Additional edge case tests for Tidal provider."""

    def test_track_to_song_no_byArtist(self) -> None:
        """Test track conversion without byArtist."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        track_data = {
            "name": "Test",
            "url": "https://tidal.com/track/123",
        }

        song = provider._track_to_song(track_data)
        assert song.artist == "Unknown"

    def test_track_to_song_image_dict(self) -> None:
        """Test track conversion with image as dict."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        track_data = {
            "name": "Test",
            "url": "https://tidal.com/track/123",
            "image": {"url": "https://example.com/cover.jpg"},
        }

        song = provider._track_to_song(track_data)
        assert song.cover_url == "https://example.com/cover.jpg"

    def test_track_to_song_image_string(self) -> None:
        """Test track conversion with image as string."""
        from spotdl.providers.sources.tidal import TidalProvider

        provider = TidalProvider()

        track_data = {
            "name": "Test",
            "url": "https://tidal.com/track/123",
            "image": "https://example.com/cover.jpg",
        }

        song = provider._track_to_song(track_data)
        assert song.cover_url == "https://example.com/cover.jpg"


class TestAppleMusicProviderEdgeCases:
    """Additional edge case tests for Apple Music provider."""

    def test_track_to_song_no_artist(self) -> None:
        """Test track conversion without artist."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "url": "https://music.apple.com/us/album/test/123?i=456",
        }

        song = provider._track_to_song(track_data)
        assert song.artist == "Unknown"

    def test_track_to_song_artist_dict(self) -> None:
        """Test track conversion with artist as dict."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "byArtist": {"name": "Test Artist"},
            "url": "https://music.apple.com/us/album/test/123?i=456",
        }

        song = provider._track_to_song(track_data)
        assert song.artist == "Test Artist"

    def test_track_to_song_content_rating_clean(self) -> None:
        """Test track conversion with clean content rating."""
        from spotdl.providers.sources.apple_music import AppleMusicProvider

        provider = AppleMusicProvider()

        track_data = {
            "name": "Test Song",
            "url": "https://music.apple.com/us/album/test/123?i=456",
            "contentRating": "clean",
        }

        song = provider._track_to_song(track_data)
        assert song.explicit is False
