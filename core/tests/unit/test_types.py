"""Unit tests for core types."""

from __future__ import annotations

import json

import pytest

from spotdl_core.types import (
    Platform,
    Result,
    Song,
    SongError,
    SongList,
    TargetPlatform,
)
from spotdl_core.providers.metadata.base import MetadataResult


class TestPlatform:
    """Test Platform enum."""

    def test_platform_values(self):
        """Test all platform values are defined."""
        assert Platform.SPOTIFY == "spotify"
        assert Platform.APPLE_MUSIC == "apple_music"
        assert Platform.DEEZER == "deezer"
        assert Platform.TIDAL == "tidal"
        assert Platform.YOUTUBE_MUSIC == "youtube_music"
        assert Platform.SOUNDCLOUD == "soundcloud"
        assert Platform.BANDCAMP == "bandcamp"

    def test_platform_from_string(self):
        """Test creating platform from string."""
        assert Platform("spotify") == Platform.SPOTIFY
        assert Platform("apple_music") == Platform.APPLE_MUSIC

    def test_platform_invalid(self):
        """Test invalid platform raises error."""
        with pytest.raises(ValueError):
            Platform("invalid")


class TestTargetPlatform:
    """Test TargetPlatform enum."""

    def test_target_platform_values(self):
        """Test all target platform values are defined."""
        assert TargetPlatform.YOUTUBE == "youtube"
        assert TargetPlatform.YOUTUBE_MUSIC == "youtube_music"
        assert TargetPlatform.SOUNDCLOUD == "soundcloud"
        assert TargetPlatform.BANDCAMP == "bandcamp"
        assert TargetPlatform.PIPED == "piped"

    def test_target_platform_from_string(self):
        """Test creating target platform from string."""
        assert TargetPlatform("youtube") == TargetPlatform.YOUTUBE
        assert TargetPlatform("youtube_music") == TargetPlatform.YOUTUBE_MUSIC

    def test_target_platform_invalid(self):
        """Test invalid target platform raises error."""
        with pytest.raises(ValueError):
            TargetPlatform("invalid")


class TestSongError:
    """Test SongError exception."""

    def test_song_error_creation(self):
        """Test creating SongError."""
        error = SongError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_song_error_inheritance(self):
        """Test SongError inherits from Exception."""
        error = SongError("Test")
        assert isinstance(error, Exception)


class TestSong:
    """Test Song dataclass."""

    @pytest.fixture
    def minimal_song(self) -> Song:
        """Create a minimal valid song."""
        return Song(
            name="Test Song",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://open.spotify.com/track/test123",
        )

    @pytest.fixture
    def full_song(self) -> Song:
        """Create a song with all fields populated."""
        return Song(
            name="Full Song",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=240,
            platform=Platform.SPOTIFY,
            platform_id="full123",
            url="https://open.spotify.com/track/full123",
            album_name="Test Album",
            album_artist="Album Artist",
            album_id="album123",
            album_type="album",
            genres=["pop", "rock"],
            disc_number=1,
            disc_count=2,
            track_number=3,
            tracks_count=12,
            year=2023,
            date="2023-01-15",
            song_id="custom-id",
            isrc="USRC12345678",
            explicit=True,
            publisher="Test Publisher",
            cover_url="https://example.com/cover.jpg",
            copyright_text="2023 Test Records",
            lyrics="Test lyrics",
            popularity=85,
            download_url="https://example.com/audio.mp3",
            list_name="Test Playlist",
            list_url="https://open.spotify.com/playlist/test",
            list_position=5,
            list_length=20,
            artist_id="artist123",
        )

    def test_minimal_song_creation(self, minimal_song: Song):
        """Test creating song with minimal required fields."""
        assert minimal_song.name == "Test Song"
        assert minimal_song.artists == ["Test Artist"]
        assert minimal_song.artist == "Test Artist"
        assert minimal_song.duration == 180
        assert minimal_song.platform == Platform.SPOTIFY
        assert minimal_song.platform_id == "test123"
        assert minimal_song.url == "https://open.spotify.com/track/test123"

    def test_full_song_creation(self, full_song: Song):
        """Test creating song with all fields."""
        assert full_song.name == "Full Song"
        assert full_song.album_name == "Test Album"
        assert full_song.genres == ["pop", "rock"]
        assert full_song.year == 2023
        assert full_song.explicit is True
        assert full_song.isrc == "USRC12345678"

    def test_song_post_init_song_id(self):
        """Test __post_init__ generates song_id if not provided."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        assert song.song_id == "spotify:test123"

    def test_song_post_init_song_id_custom(self):
        """Test __post_init__ preserves custom song_id."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
            song_id="custom-id",
        )
        assert song.song_id == "custom-id"

    def test_song_post_init_artist_from_artists(self):
        """Test __post_init__ sets artist from artists if empty."""
        song = Song(
            name="Test",
            artists=["First Artist", "Second Artist"],
            artist="",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )
        assert song.artist == "First Artist"

    def test_song_display_name(self, minimal_song: Song):
        """Test display_name property."""
        assert minimal_song.display_name == "Test Artist - Test Song"

    def test_song_json_property(self, minimal_song: Song):
        """Test json property returns dict with string platform."""
        data = minimal_song.json
        assert isinstance(data, dict)
        assert data["platform"] == "spotify"
        assert data["name"] == "Test Song"
        assert data["artists"] == ["Test Artist"]

    def test_song_to_json(self, minimal_song: Song):
        """Test to_json serialization."""
        json_str = minimal_song.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["platform"] == "spotify"
        assert data["name"] == "Test Song"

    def test_song_from_dict(self):
        """Test from_dict creates Song from dictionary."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "spotify",
            "platform_id": "test123",
            "url": "https://test.com",
        }
        song = Song.from_dict(data)
        assert song.name == "Test"
        assert song.platform == Platform.SPOTIFY
        assert isinstance(song.platform, Platform)

    def test_song_from_dict_with_enum(self):
        """Test from_dict handles Platform enum."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": Platform.SPOTIFY,
            "platform_id": "test123",
            "url": "https://test.com",
        }
        song = Song.from_dict(data)
        assert song.platform == Platform.SPOTIFY

    def test_song_from_json(self):
        """Test from_json creates Song from JSON string."""
        json_str = json.dumps({
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "spotify",
            "platform_id": "test123",
            "url": "https://test.com",
        })
        song = Song.from_json(json_str)
        assert song.name == "Test"
        assert song.platform == Platform.SPOTIFY

    def test_song_roundtrip_json(self, full_song: Song):
        """Test song can be serialized and deserialized."""
        json_str = full_song.to_json()
        restored = Song.from_json(json_str)
        assert restored.name == full_song.name
        assert restored.artists == full_song.artists
        assert restored.platform == full_song.platform
        assert restored.genres == full_song.genres
        assert restored.explicit == full_song.explicit

    def test_song_default_values(self, minimal_song: Song):
        """Test default values are set correctly."""
        assert minimal_song.album_name == ""
        assert minimal_song.album_artist == ""
        assert minimal_song.album_id is None
        assert minimal_song.album_type is None
        assert minimal_song.genres == []
        assert minimal_song.disc_number == 1
        assert minimal_song.disc_count == 1
        assert minimal_song.track_number == 1
        assert minimal_song.tracks_count == 1
        assert minimal_song.year == 0
        assert minimal_song.date == ""
        assert minimal_song.explicit is False
        assert minimal_song.publisher == ""
        assert minimal_song.cover_url is None
        assert minimal_song.lyrics is None
        assert minimal_song.popularity is None


class TestSongList:
    """Test SongList dataclass."""

    @pytest.fixture
    def song1(self) -> Song:
        """Create first test song."""
        return Song(
            name="Song 1",
            artists=["Artist 1"],
            artist="Artist 1",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="song1",
            url="https://spotify.com/track/song1",
        )

    @pytest.fixture
    def song2(self) -> Song:
        """Create second test song."""
        return Song(
            name="Song 2",
            artists=["Artist 2"],
            artist="Artist 2",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="song2",
            url="https://spotify.com/track/song2",
        )

    @pytest.fixture
    def song_list(self, song1: Song, song2: Song) -> SongList:
        """Create a test song list."""
        return SongList(
            name="Test Playlist",
            url="https://spotify.com/playlist/test",
            platform=Platform.SPOTIFY,
            urls=(
                "https://spotify.com/track/song1",
                "https://spotify.com/track/song2",
            ),
            songs=(song1, song2),
        )

    def test_song_list_creation(self, song_list: SongList, song1: Song, song2: Song):
        """Test creating a song list."""
        assert song_list.name == "Test Playlist"
        assert song_list.url == "https://spotify.com/playlist/test"
        assert song_list.platform == Platform.SPOTIFY
        assert len(song_list.urls) == 2
        assert len(song_list.songs) == 2
        assert song_list.songs[0] == song1
        assert song_list.songs[1] == song2

    def test_song_list_length_property(self, song_list: SongList):
        """Test length property returns max of urls and songs."""
        assert song_list.length == 2

    def test_song_list_length_urls_only(self):
        """Test length with only URLs."""
        song_list = SongList(
            name="Test",
            url="https://test.com",
            platform=Platform.SPOTIFY,
            urls=("url1", "url2", "url3"),
            songs=(),
        )
        assert song_list.length == 3

    def test_song_list_length_songs_only(self, song1: Song):
        """Test length with only songs."""
        song_list = SongList(
            name="Test",
            url="https://test.com",
            platform=Platform.SPOTIFY,
            urls=(),
            songs=(song1,),
        )
        assert song_list.length == 1

    def test_song_list_json_property(self, song_list: SongList):
        """Test json property returns dict."""
        data = song_list.json
        assert isinstance(data, dict)
        assert data["name"] == "Test Playlist"
        assert data["platform"] == "spotify"
        assert isinstance(data["urls"], list)
        assert len(data["urls"]) == 2
        assert isinstance(data["songs"], list)
        assert len(data["songs"]) == 2

    def test_song_list_frozen(self, song_list: SongList):
        """Test song list is frozen (immutable)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            song_list.name = "New Name"

    def test_song_list_empty(self):
        """Test creating an empty song list."""
        song_list = SongList(
            name="Empty",
            url="https://test.com",
            platform=Platform.SPOTIFY,
            urls=(),
            songs=(),
        )
        assert song_list.length == 0


class TestResult:
    """Test Result dataclass."""

    @pytest.fixture
    def minimal_result(self) -> Result:
        """Create a minimal valid result."""
        return Result(
            name="Test Video",
            artists=["Test Artist"],
            artist="Test Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test123",
            url="https://youtube.com/watch?v=test123",
        )

    @pytest.fixture
    def full_result(self) -> Result:
        """Create a result with all fields populated."""
        return Result(
            name="Full Video",
            artists=("Artist 1", "Artist 2"),
            artist="Artist 1",
            duration=240,
            platform=TargetPlatform.YOUTUBE,
            platform_id="full123",
            url="https://youtube.com/watch?v=full123",
            album_name="Test Album",
            cover_url="https://example.com/cover.jpg",
            views=1000000,
            explicit=True,
            verified=True,
            year=2023,
            track_number=3,
            isrc_search=True,
            search_query="artist name - song name",
        )

    def test_minimal_result_creation(self, minimal_result: Result):
        """Test creating result with minimal required fields."""
        assert minimal_result.name == "Test Video"
        assert minimal_result.artists == ("Test Artist",)
        assert minimal_result.artist == "Test Artist"
        assert minimal_result.duration == 180
        assert minimal_result.platform == TargetPlatform.YOUTUBE
        assert minimal_result.platform_id == "test123"
        assert minimal_result.url == "https://youtube.com/watch?v=test123"

    def test_full_result_creation(self, full_result: Result):
        """Test creating result with all fields."""
        assert full_result.name == "Full Video"
        assert full_result.album_name == "Test Album"
        assert full_result.views == 1000000
        assert full_result.explicit is True
        assert full_result.verified is True
        assert full_result.year == 2023
        assert full_result.isrc_search is True

    def test_result_post_init_converts_list_to_tuple(self):
        """Test __post_init__ converts artists list to tuple."""
        result = Result(
            name="Test",
            artists=["Artist 1", "Artist 2"],
            artist="Artist 1",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="test123",
            url="https://test.com",
        )
        assert isinstance(result.artists, tuple)
        assert result.artists == ("Artist 1", "Artist 2")

    def test_result_display_name(self, minimal_result: Result):
        """Test display_name property."""
        assert minimal_result.display_name == "Test Artist - Test Video"

    def test_result_json_property(self, minimal_result: Result):
        """Test json property returns dict with string platform and list artists."""
        data = minimal_result.json
        assert isinstance(data, dict)
        assert data["platform"] == "youtube"
        assert data["name"] == "Test Video"
        assert isinstance(data["artists"], list)
        assert data["artists"] == ["Test Artist"]

    def test_result_to_json(self, minimal_result: Result):
        """Test to_json serialization."""
        json_str = minimal_result.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["platform"] == "youtube"
        assert data["name"] == "Test Video"
        assert isinstance(data["artists"], list)

    def test_result_from_dict(self):
        """Test from_dict creates Result from dictionary."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "youtube",
            "platform_id": "test123",
            "url": "https://test.com",
        }
        result = Result.from_dict(data)
        assert result.name == "Test"
        assert result.platform == TargetPlatform.YOUTUBE
        assert isinstance(result.platform, TargetPlatform)
        assert isinstance(result.artists, tuple)

    def test_result_from_dict_with_enum(self):
        """Test from_dict handles TargetPlatform enum."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": TargetPlatform.YOUTUBE,
            "platform_id": "test123",
            "url": "https://test.com",
        }
        result = Result.from_dict(data)
        assert result.platform == TargetPlatform.YOUTUBE

    def test_result_from_dict_legacy_source_field(self):
        """Test from_dict handles legacy 'source' field."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "source": "youtube",
            "platform_id": "test123",
            "url": "https://test.com",
        }
        result = Result.from_dict(data)
        assert result.platform == TargetPlatform.YOUTUBE

    def test_result_from_dict_legacy_author_field(self):
        """Test from_dict handles legacy 'author' field."""
        data = {
            "name": "Test",
            "author": "Legacy Artist",
            "duration": 180,
            "platform": "youtube",
            "platform_id": "test123",
            "url": "https://test.com",
        }
        result = Result.from_dict(data)
        assert result.artist == "Legacy Artist"
        assert result.artists == ("Legacy Artist",)

    def test_result_from_dict_legacy_result_id_field(self):
        """Test from_dict handles legacy 'result_id' field."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "youtube",
            "result_id": "legacy123",
            "url": "https://test.com",
        }
        result = Result.from_dict(data)
        assert result.platform_id == "legacy123"

    def test_result_from_dict_legacy_album_field(self):
        """Test from_dict handles legacy 'album' field."""
        data = {
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "youtube",
            "platform_id": "test123",
            "url": "https://test.com",
            "album": "Legacy Album",
        }
        result = Result.from_dict(data)
        assert result.album_name == "Legacy Album"

    def test_result_from_json(self):
        """Test from_json creates Result from JSON string."""
        json_str = json.dumps({
            "name": "Test",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 180,
            "platform": "youtube",
            "platform_id": "test123",
            "url": "https://test.com",
        })
        result = Result.from_json(json_str)
        assert result.name == "Test"
        assert result.platform == TargetPlatform.YOUTUBE

    def test_result_roundtrip_json(self, full_result: Result):
        """Test result can be serialized and deserialized."""
        json_str = full_result.to_json()
        restored = Result.from_json(json_str)
        assert restored.name == full_result.name
        assert restored.artists == full_result.artists
        assert restored.platform == full_result.platform
        assert restored.views == full_result.views
        assert restored.explicit == full_result.explicit
        assert restored.verified == full_result.verified

    def test_result_frozen(self, minimal_result: Result):
        """Test result is frozen (immutable)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            minimal_result.name = "New Name"

    def test_result_default_values(self, minimal_result: Result):
        """Test default values are set correctly."""
        assert minimal_result.album_name is None
        assert minimal_result.cover_url is None
        assert minimal_result.views is None
        assert minimal_result.explicit is False
        assert minimal_result.verified is False
        assert minimal_result.year is None
        assert minimal_result.track_number is None
        assert minimal_result.isrc_search is False
        assert minimal_result.search_query is None


class TestMetadataResult:
    """Test MetadataResult dataclass."""

    def test_metadata_result_minimal(self):
        """Test creating metadata result with minimal fields."""
        result = MetadataResult()
        assert result.name is None
        assert result.artists is None
        assert result.genres == []
        assert result.source == ""
        assert result.confidence == 1.0

    def test_metadata_result_full(self):
        """Test creating metadata result with all fields."""
        result = MetadataResult(
            name="Test Song",
            artists=["Artist 1", "Artist 2"],
            album_name="Test Album",
            album_artist="Album Artist",
            isrc="USRC12345678",
            upc="123456789012",
            musicbrainz_id="mb-123",
            discogs_id="discogs-456",
            genres=["rock", "pop"],
            year=2023,
            date="2023-01-15",
            track_number=3,
            disc_number=1,
            total_tracks=12,
            total_discs=2,
            album_art_url="https://example.com/art.jpg",
            label="Test Records",
            country="US",
            duration_ms=180000,
            bpm=120.5,
            key="C major",
            source="musicbrainz",
            confidence=0.95,
        )
        assert result.name == "Test Song"
        assert result.artists == ["Artist 1", "Artist 2"]
        assert result.album_name == "Test Album"
        assert result.isrc == "USRC12345678"
        assert result.genres == ["rock", "pop"]
        assert result.year == 2023
        assert result.source == "musicbrainz"
        assert result.confidence == 0.95

    def test_metadata_result_identifiers(self):
        """Test metadata result identifiers."""
        result = MetadataResult(
            isrc="USRC12345678",
            upc="123456789012",
            musicbrainz_id="mb-123",
            discogs_id="discogs-456",
        )
        assert result.isrc == "USRC12345678"
        assert result.upc == "123456789012"
        assert result.musicbrainz_id == "mb-123"
        assert result.discogs_id == "discogs-456"

    def test_metadata_result_audio_features(self):
        """Test metadata result audio features."""
        result = MetadataResult(
            duration_ms=180000,
            bpm=120.5,
            key="C major",
        )
        assert result.duration_ms == 180000
        assert result.bpm == 120.5
        assert result.key == "C major"

    def test_metadata_result_album_info(self):
        """Test metadata result album information."""
        result = MetadataResult(
            album_name="Test Album",
            album_artist="Album Artist",
            album_art_url="https://example.com/art.jpg",
            label="Test Records",
            country="US",
        )
        assert result.album_name == "Test Album"
        assert result.album_artist == "Album Artist"
        assert result.album_art_url == "https://example.com/art.jpg"
        assert result.label == "Test Records"
        assert result.country == "US"

    def test_metadata_result_track_info(self):
        """Test metadata result track information."""
        result = MetadataResult(
            track_number=3,
            disc_number=1,
            total_tracks=12,
            total_discs=2,
        )
        assert result.track_number == 3
        assert result.disc_number == 1
        assert result.total_tracks == 12
        assert result.total_discs == 2


class TestDownloadTypes:
    """Test download-related types."""

    def test_download_settings_import(self):
        """Test DownloadSettings can be imported."""
        from spotdl_core.download.downloader import DownloadSettings

        settings = DownloadSettings()
        assert settings.audio_format == "mp3"
        assert settings.audio_quality == "best"
        assert settings.embed_metadata is True

    def test_download_settings_custom(self):
        """Test DownloadSettings with custom values."""
        from spotdl_core.download.downloader import DownloadSettings

        settings = DownloadSettings(
            audio_format="flac",
            audio_quality="320k",
            bitrate="320k",
            embed_metadata=False,
            embed_lyrics=False,
            embed_cover=False,
        )
        assert settings.audio_format == "flac"
        assert settings.audio_quality == "320k"
        assert settings.bitrate == "320k"
        assert settings.embed_metadata is False
        assert settings.embed_lyrics is False
        assert settings.embed_cover is False

    def test_download_progress_import(self):
        """Test DownloadProgress can be imported."""
        from spotdl_core.download.downloader import DownloadProgress

        progress = DownloadProgress()
        assert progress.status == ""
        assert progress.progress == 0.0

    def test_download_progress_values(self):
        """Test DownloadProgress with values."""
        from spotdl_core.download.downloader import DownloadProgress

        progress = DownloadProgress(
            status="downloading",
            progress=0.5,
            speed="1.2MB/s",
            eta="00:30",
            filename="test.mp3",
        )
        assert progress.status == "downloading"
        assert progress.progress == 0.5
        assert progress.speed == "1.2MB/s"
        assert progress.eta == "00:30"
        assert progress.filename == "test.mp3"

    def test_download_meta_import(self):
        """Test DownloadMeta can be imported."""
        from spotdl_core.download.downloader import DownloadMeta

        meta = DownloadMeta()
        assert meta.title == ""
        assert meta.artist == ""
        assert meta.artists == []

    def test_download_meta_values(self):
        """Test DownloadMeta with values."""
        from spotdl_core.download.downloader import DownloadMeta

        meta = DownloadMeta(
            title="Test Song",
            artist="Test Artist",
            artists=["Test Artist", "Featured Artist"],
            album="Test Album",
            duration=180,
            genres=["rock", "pop"],
            year=2023,
            track_number=3,
            isrc="USRC12345678",
        )
        assert meta.title == "Test Song"
        assert meta.artist == "Test Artist"
        assert meta.artists == ["Test Artist", "Featured Artist"]
        assert meta.album == "Test Album"
        assert meta.duration == 180
        assert meta.genres == ["rock", "pop"]
        assert meta.year == 2023
        assert meta.track_number == 3
        assert meta.isrc == "USRC12345678"


class TestTypeInteroperability:
    """Test interactions between different types."""

    def test_song_to_result_compatibility(self):
        """Test Song and Result have compatible field names."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="song123",
            url="https://spotify.com/track/song123",
        )

        # These fields should be compatible for comparison
        assert hasattr(song, "name")
        assert hasattr(song, "artists")
        assert hasattr(song, "artist")
        assert hasattr(song, "duration")

    def test_platform_vs_target_platform(self):
        """Test Platform and TargetPlatform are separate."""
        # Platform is for metadata sources
        assert Platform.SPOTIFY == "spotify"

        # TargetPlatform is for audio sources
        assert TargetPlatform.YOUTUBE == "youtube"

        # They should not be interchangeable
        with pytest.raises(ValueError):
            TargetPlatform("spotify")

    def test_song_list_songs_property(self):
        """Test SongList properly contains Song objects."""
        song = Song(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id="test123",
            url="https://test.com",
        )

        song_list = SongList(
            name="Test List",
            url="https://test.com",
            platform=Platform.SPOTIFY,
            urls=("https://test.com",),
            songs=(song,),
        )

        assert isinstance(song_list.songs[0], Song)
        assert song_list.songs[0].name == "Test"
