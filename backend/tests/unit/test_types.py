"""Tests for core types."""

import json
import pytest

from spotdl.core.types.song import Platform, Song, SongList
from spotdl.core.types.result import Result, TargetPlatform


class TestPlatformEnum:
    """Tests for Platform enum."""

    def test_platform_values(self):
        """Test platform enum values."""
        assert Platform.SPOTIFY.value == "spotify"
        assert Platform.DEEZER.value == "deezer"
        assert Platform.APPLE_MUSIC.value == "apple_music"
        assert Platform.TIDAL.value == "tidal"
        assert Platform.YOUTUBE_MUSIC.value == "youtube_music"
        assert Platform.SOUNDCLOUD.value == "soundcloud"
        assert Platform.BANDCAMP.value == "bandcamp"


class TestTargetPlatformEnum:
    """Tests for TargetPlatform enum."""

    def test_target_platform_values(self):
        """Test target platform enum values."""
        assert TargetPlatform.YOUTUBE.value == "youtube"
        assert TargetPlatform.YOUTUBE_MUSIC.value == "youtube_music"
        assert TargetPlatform.SOUNDCLOUD.value == "soundcloud"
        assert TargetPlatform.BANDCAMP.value == "bandcamp"
        assert TargetPlatform.PIPED.value == "piped"
        assert TargetPlatform.SLIDER_KZ.value == "slider.kz"


class TestSong:
    """Tests for Song class."""

    def test_song_creation(self):
        """Test creating a song."""
        song = Song(
            name="Test Song",
            artists=["Artist One", "Artist Two"],
            artist="Artist One",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        assert song.name == "Test Song"
        assert song.artists == ["Artist One", "Artist Two"]
        assert song.artist == "Artist One"
        assert song.duration == 180
        assert song.platform == Platform.SPOTIFY
        assert song.song_id == "spotify:abc123"

    def test_song_display_name(self):
        """Test song display name property."""
        song = Song(
            name="Song Title",
            artists=["Main Artist"],
            artist="Main Artist",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="xyz",
            url="https://open.spotify.com/track/xyz",
        )

        assert song.display_name == "Main Artist - Song Title"

    def test_song_from_dict(self):
        """Test creating song from dictionary."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 100,
            "platform": "spotify",
            "platform_id": "123",
            "url": "https://example.com",
        }

        song = Song.from_dict(data)
        assert song.name == "Test"
        assert song.platform == Platform.SPOTIFY

    def test_song_from_json(self):
        """Test creating song from JSON string."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 100,
            "platform": "spotify",
            "platform_id": "123",
            "url": "https://example.com",
        }

        song = Song.from_json(json.dumps(data))
        assert song.name == "Test"

    def test_song_to_json(self):
        """Test serializing song to JSON."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=100,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )

        json_str = song.to_json()
        data = json.loads(json_str)

        assert data["name"] == "Test"
        assert data["platform"] == "spotify"

    def test_song_json_property(self):
        """Test song json property."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=100,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com",
        )

        data = song.json
        assert data["name"] == "Test"
        assert data["platform"] == "spotify"
        assert isinstance(data["artists"], list)


class TestResult:
    """Tests for Result class."""

    def test_result_creation(self):
        """Test creating a result."""
        result = Result(
            name="Test Result",
            artists=["Test Author"],
            artist="Test Author",
            duration=185,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id="abc",
            url="https://music.youtube.com/watch?v=abc",
            verified=True,
        )

        assert result.name == "Test Result"
        assert result.platform == TargetPlatform.YOUTUBE_MUSIC
        assert result.verified is True
        assert result.duration == 185

    def test_result_from_dict(self):
        """Test creating result from dictionary."""
        data = {
            "name": "Test",
            "artists": ["Artist1", "Artist2"],
            "artist": "Artist1",
            "duration": 200,
            "platform": "youtube",
            "platform_id": "xyz",
            "url": "https://youtube.com/watch?v=xyz",
            "verified": False,
        }

        result = Result.from_dict(data)
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.artists == ("Artist1", "Artist2")

    def test_result_from_dict_legacy_fields(self):
        """Test creating result from dictionary with legacy field names."""
        data = {
            "source": "youtube",
            "url": "https://youtube.com/watch?v=xyz",
            "verified": False,
            "name": "Test",
            "duration": 200,
            "author": "Author",
            "result_id": "xyz",
        }

        result = Result.from_dict(data)
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.artist == "Author"
        assert result.platform_id == "xyz"

    def test_result_from_json(self):
        """Test creating result from JSON."""
        data = {
            "name": "Test",
            "artists": ["Author"],
            "artist": "Author",
            "duration": 150,
            "platform": "soundcloud",
            "platform_id": "test",
            "url": "https://soundcloud.com/test",
        }

        result = Result.from_json(json.dumps(data))
        assert result.platform == TargetPlatform.SOUNDCLOUD

    def test_result_to_json(self):
        """Test serializing result to JSON."""
        result = Result(
            name="Song",
            artists=["Artist"],
            artist="Artist",
            duration=300,
            platform=TargetPlatform.BANDCAMP,
            platform_id="song123",
            url="https://artist.bandcamp.com/track/song",
            verified=True,
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["platform"] == "bandcamp"
        assert data["artists"] == ["Artist"]

    def test_result_json_property(self):
        """Test result json property."""
        result = Result(
            name="Video",
            artists=["Channel"],
            artist="Channel",
            duration=250,
            platform=TargetPlatform.PIPED,
            platform_id="abc",
            url="https://piped.video/watch?v=abc",
            verified=False,
        )

        data = result.json
        assert data["platform"] == "piped"
        assert data["verified"] is False

    def test_result_optional_fields(self):
        """Test result optional fields."""
        result = Result(
            name="Song",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc",
            url="https://youtube.com/watch?v=abc",
            album_name="Album",
            cover_url="https://example.com/cover.jpg",
            views=1000000,
            explicit=True,
            year=2024,
        )

        assert result.album_name == "Album"
        assert result.cover_url == "https://example.com/cover.jpg"
        assert result.views == 1000000
        assert result.explicit is True
        assert result.year == 2024

    def test_result_artists_list_converted_to_tuple(self):
        """Test that artists list is converted to tuple."""
        result = Result(
            name="Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=200,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc",
            url="https://youtube.com/watch?v=abc",
        )

        assert isinstance(result.artists, tuple)
        assert result.artists == ("Artist1", "Artist2")


class TestSongList:
    """Tests for SongList class."""

    def test_song_list_length(self):
        """Test song list length property."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=100,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com/1",
        )

        song_list = SongList(
            name="Test Playlist",
            url="https://example.com/playlist",
            platform=Platform.SPOTIFY,
            urls=("https://example.com/1", "https://example.com/2"),
            songs=(song,),
        )

        # Should return max of urls or songs
        assert song_list.length == 2

    def test_song_list_json(self):
        """Test song list JSON serialization."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=100,
            platform=Platform.SPOTIFY,
            platform_id="123",
            url="https://example.com/1",
        )

        song_list = SongList(
            name="My Playlist",
            url="https://example.com/playlist",
            platform=Platform.SPOTIFY,
            urls=("https://example.com/1",),
            songs=(song,),
        )

        data = song_list.json
        assert data["name"] == "My Playlist"
        assert data["platform"] == "spotify"
        assert len(data["songs"]) == 1
