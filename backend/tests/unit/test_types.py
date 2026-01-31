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
            source=TargetPlatform.YOUTUBE_MUSIC,
            url="https://music.youtube.com/watch?v=abc",
            verified=True,
            name="Test Result",
            duration=185.0,
            author="Test Author",
            result_id="abc",
        )

        assert result.name == "Test Result"
        assert result.source == TargetPlatform.YOUTUBE_MUSIC
        assert result.verified is True
        assert result.duration == 185.0

    def test_result_from_dict(self):
        """Test creating result from dictionary."""
        data = {
            "source": "youtube",
            "url": "https://youtube.com/watch?v=xyz",
            "verified": False,
            "name": "Test",
            "duration": 200.0,
            "author": "Author",
            "result_id": "xyz",
            "artists": ["Artist1", "Artist2"],
        }

        result = Result.from_dict(data)
        assert result.source == TargetPlatform.YOUTUBE
        assert result.artists == ("Artist1", "Artist2")

    def test_result_from_json(self):
        """Test creating result from JSON."""
        data = {
            "source": "soundcloud",
            "url": "https://soundcloud.com/test",
            "verified": False,
            "name": "Test",
            "duration": 150.0,
            "author": "Author",
            "result_id": "test",
        }

        result = Result.from_json(json.dumps(data))
        assert result.source == TargetPlatform.SOUNDCLOUD

    def test_result_to_json(self):
        """Test serializing result to JSON."""
        result = Result(
            source=TargetPlatform.BANDCAMP,
            url="https://artist.bandcamp.com/track/song",
            verified=True,
            name="Song",
            duration=300.0,
            author="Artist",
            result_id="song123",
            artists=("Artist",),
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["source"] == "bandcamp"
        assert data["artists"] == ["Artist"]

    def test_result_json_property(self):
        """Test result json property."""
        result = Result(
            source=TargetPlatform.PIPED,
            url="https://piped.video/watch?v=abc",
            verified=False,
            name="Video",
            duration=250.0,
            author="Channel",
            result_id="abc",
        )

        data = result.json
        assert data["source"] == "piped"
        assert data["verified"] is False

    def test_result_is_frozen(self):
        """Test that result is immutable."""
        result = Result(
            source=TargetPlatform.YOUTUBE,
            url="https://youtube.com/watch?v=test",
            verified=True,
            name="Test",
            duration=100.0,
            author="Author",
            result_id="test",
        )

        with pytest.raises(AttributeError):
            result.name = "Changed"  # type: ignore

    def test_result_is_hashable(self):
        """Test that result can be used in sets/dicts."""
        result1 = Result(
            source=TargetPlatform.YOUTUBE,
            url="https://youtube.com/watch?v=a",
            verified=True,
            name="A",
            duration=100.0,
            author="Author",
            result_id="a",
        )
        result2 = Result(
            source=TargetPlatform.YOUTUBE,
            url="https://youtube.com/watch?v=b",
            verified=True,
            name="B",
            duration=100.0,
            author="Author",
            result_id="b",
        )

        # Should be usable in a set
        result_set = {result1, result2}
        assert len(result_set) == 2

        # Should be usable as dict key
        result_dict = {result1: 100, result2: 200}
        assert result_dict[result1] == 100


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
