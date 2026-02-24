"""Tests for core types."""

import pytest
from datetime import datetime

from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Platform,
    SearchResult,
    Song,
    TargetPlatform,
)


class TestSong:
    """Tests for Song dataclass."""

    def test_create_song(self) -> None:
        """Test creating a song."""
        song = Song(
            name="Test Song",
            artists=["Artist1", "Artist2"],
            artist="Artist1",
            duration=200,
            platform=Platform.SPOTIFY,
            platform_id="abc123",
            url="https://open.spotify.com/track/abc123",
        )

        assert song.name == "Test Song"
        assert song.artists == ["Artist1", "Artist2"]
        assert song.duration == 200
        assert song.platform == Platform.SPOTIFY
        assert song.song_id == "spotify:abc123"

    def test_display_name(self) -> None:
        """Test display name property."""
        song = Song(
            name="My Song",
            artists=["Cool Artist"],
            artist="Cool Artist",
            duration=180,
            platform=Platform.DEEZER,
            platform_id="xyz789",
            url="https://deezer.com/track/xyz789",
        )

        assert song.display_name == "Cool Artist - My Song"

    def test_from_dict(self) -> None:
        """Test creating song from dictionary."""
        data = {
            "name": "Dict Song",
            "artists": ["Artist"],
            "artist": "Artist",
            "duration": 120,
            "platform": "spotify",
            "platform_id": "test",
            "url": "https://example.com",
        }

        song = Song.from_dict(data)
        assert song.name == "Dict Song"
        assert song.platform == Platform.SPOTIFY


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a download result."""
        result = DownloadResult(
            name="Test Result",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            verified=True,
            score=90.5,
        )

        assert result.name == "Test Result"
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.verified is True
        assert result.score == 90.5

    def test_display_name(self) -> None:
        """Test display name property."""
        result = DownloadResult(
            name="My Result",
            artists=["Cool Artist"],
            artist="Cool Artist",
            duration=180,
            platform=TargetPlatform.SOUNDCLOUD,
            platform_id="xyz",
            url="https://soundcloud.com/xyz",
        )

        assert result.display_name == "Cool Artist - My Result"

    def test_from_dict(self) -> None:
        """Test creating DownloadResult from dictionary."""
        data = {
            "name": "Dict Result",
            "artists": ["Artist1"],
            "artist": "Artist1",
            "duration": 200,
            "platform": "youtube",
            "platform_id": "dict123",
            "url": "https://youtube.com/watch?v=dict123",
            "score": 85.0,
        }

        result = DownloadResult.from_dict(data)
        assert result.name == "Dict Result"
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.score == 85.0

    def test_hash_and_equality(self) -> None:
        """Test hashability and equality."""
        result1 = DownloadResult(
            name="Same",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="same123",
            url="https://youtube.com/watch?v=same123",
        )
        result2 = DownloadResult(
            name="Same",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="same123",
            url="https://youtube.com/watch?v=same123",
        )

        assert result1 == result2
        assert hash(result1) == hash(result2)

        # Test as dict key
        d = {result1: "value"}
        assert d[result2] == "value"


class TestDownloadItem:
    """Tests for DownloadItem dataclass."""

    def test_create_item(self, sample_song: Song) -> None:
        """Test creating a download item."""
        item = DownloadItem(song=sample_song)

        assert item.song == sample_song
        assert item.result is None
        assert item.status == DownloadStatus.PENDING
        assert item.progress == 0.0

    def test_display_name(self, sample_song: Song) -> None:
        """Test display name property."""
        item = DownloadItem(song=sample_song)
        assert item.display_name == sample_song.display_name

    def test_status_display_pending(self, sample_song: Song) -> None:
        """Test status display for pending item."""
        item = DownloadItem(song=sample_song, status=DownloadStatus.PENDING)
        assert item.status_display == "Pending"

    def test_status_display_downloading_with_progress(self, sample_song: Song) -> None:
        """Test status display for downloading item with progress."""
        item = DownloadItem(
            song=sample_song,
            status=DownloadStatus.DOWNLOADING,
            progress=45.5,
        )
        assert item.status_display == "Downloading 46%"

    def test_status_display_failed_with_error(self, sample_song: Song) -> None:
        """Test status display for failed item with error."""
        item = DownloadItem(
            song=sample_song,
            status=DownloadStatus.FAILED,
            error="Network connection failed unexpectedly during download",
        )
        assert "Failed:" in item.status_display
        assert len(item.status_display) <= 40  # Error truncated


class TestEnums:
    """Tests for enum types."""

    def test_platform_values(self) -> None:
        """Test Platform enum values."""
        assert Platform.SPOTIFY == "spotify"
        assert Platform.APPLE_MUSIC == "apple_music"
        assert Platform.DEEZER == "deezer"
        assert Platform.TIDAL == "tidal"
        assert Platform.YOUTUBE_MUSIC == "youtube_music"
        assert Platform.SOUNDCLOUD == "soundcloud"
        assert Platform.BANDCAMP == "bandcamp"

    def test_target_platform_values(self) -> None:
        """Test TargetPlatform enum values."""
        assert TargetPlatform.YOUTUBE == "youtube"
        assert TargetPlatform.YOUTUBE_MUSIC == "youtube_music"
        assert TargetPlatform.SOUNDCLOUD == "soundcloud"
        assert TargetPlatform.BANDCAMP == "bandcamp"
        assert TargetPlatform.PIPED == "piped"

    def test_download_status_values(self) -> None:
        """Test DownloadStatus enum values."""
        assert DownloadStatus.PENDING == "pending"
        assert DownloadStatus.SEARCHING == "searching"
        assert DownloadStatus.DOWNLOADING == "downloading"
        assert DownloadStatus.CONVERTING == "converting"
        assert DownloadStatus.EMBEDDING == "embedding"
        assert DownloadStatus.COMPLETED == "completed"
        assert DownloadStatus.FAILED == "failed"
        assert DownloadStatus.CANCELLED == "cancelled"
