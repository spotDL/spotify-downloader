"""Unit tests for download manager."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from spotdl_cli.config import Settings
from spotdl_cli.core.downloader import DownloadManager
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadStatus,
    Platform,
    Result,
    Song,
    TargetPlatform,
)

# Mock spotdl_core.download module components
from spotdl_core.download import (
    Archive,
    DownloadError,
    DownloadMeta,
    DownloadProgress,
    DownloadSettings,
    Downloader,
)


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    """Create test settings with temporary directories."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return Settings(
        output_dir=output_dir,
        audio_format="mp3",
        audio_quality="best",
        bitrate="320k",
        threads=2,
        max_concurrent=2,
        overwrite="skip",
        archive=None,
        scan_for_songs=False,
        skip_explicit=False,
        embed_metadata=True,
        embed_lyrics=True,
        embed_cover=True,
        generate_lrc=False,
        create_skip_file=False,
        respect_skip_file=False,
        add_unavailable=False,
        print_errors=False,
        save_errors=None,
        output_template="{artist} - {title}",
        max_filename_length=255,
        restrict=None,
        id3_separator="/",
        sponsor_block=False,
        sponsor_block_categories=[],
        playlist_numbering=False,
        ffmpeg_args="",
        yt_dlp_args="",
        proxy=None,
        cookies_path=Path("cookies.txt"),
    )


@pytest.fixture
def sample_song() -> Song:
    """Create a sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Test Artist", "Featured Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="test123",
        url="https://open.spotify.com/track/test123",
        album_name="Test Album",
        album_artist="Test Artist",
        cover_url="https://example.com/cover.jpg",
        genres=["Pop", "Rock"],
        year=2024,
        date="2024-01-15",
        track_number=1,
        disc_number=1,
        disc_count=1,
        tracks_count=10,
        isrc="USABC1234567",
        publisher="Test Publisher",
        song_id="test123",
        lyrics="Test lyrics\nLine 2",
        explicit=False,
        list_name=None,
        list_position=None,
        list_length=None,
    )


@pytest.fixture
def explicit_song() -> Song:
    """Create an explicit song for testing."""
    return Song(
        name="Explicit Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="explicit123",
        url="https://open.spotify.com/track/explicit123",
        album_name="Test Album",
        album_artist="Test Artist",
        cover_url="https://example.com/cover.jpg",
        genres=["Hip-Hop"],
        year=2024,
        date="2024-01-15",
        track_number=2,
        disc_number=1,
        disc_count=1,
        tracks_count=10,
        isrc="USABC1234568",
        publisher="Test Publisher",
        song_id="explicit123",
        lyrics="Explicit lyrics",
        explicit=True,
        list_name=None,
        list_position=None,
        list_length=None,
    )


@pytest.fixture
def sample_result() -> Result:
    """Create a sample download result for testing."""
    return Result(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=182,
        platform=TargetPlatform.YOUTUBE,
        platform_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        verified=True,
        album_name="Test Album",
        cover_url="https://example.com/yt-cover.jpg",
        views=1000000,
        isrc_search=False,
        search_query="Test Artist Test Song",
    )


@pytest.fixture
def sample_download_item(sample_song: Song, sample_result: Result) -> DownloadItem:
    """Create a sample download item for testing."""
    return DownloadItem(
        song=sample_song,
        result=sample_result,
        status=DownloadStatus.PENDING,
    )


class TestDownloadManagerInitialization:
    """Tests for DownloadManager initialization."""

    def test_init_default_settings(self, temp_settings: Settings) -> None:
        """Test initialization with default settings."""
        manager = DownloadManager(temp_settings)

        assert manager._settings == temp_settings
        assert manager._max_concurrent == temp_settings.threads
        assert isinstance(manager._downloader, Downloader)
        assert isinstance(manager._archive, Archive)
        assert manager._active_tasks == {}
        assert not manager._stop_event.is_set()

    def test_init_custom_max_concurrent(self, temp_settings: Settings) -> None:
        """Test initialization with custom max_concurrent."""
        manager = DownloadManager(temp_settings, max_concurrent=5)

        assert manager._max_concurrent == 5

    def test_init_with_archive(self, temp_settings: Settings, tmp_path: Path) -> None:
        """Test initialization with archive file."""
        archive_path = tmp_path / "archive.txt"
        archive_path.write_text("https://open.spotify.com/track/archived1\n")
        temp_settings.archive = archive_path

        with patch.object(Archive, "load") as mock_load:
            manager = DownloadManager(temp_settings)
            mock_load.assert_called_once_with(archive_path)

    def test_init_with_scan_for_songs(self, temp_settings: Settings) -> None:
        """Test initialization with scan_for_songs enabled."""
        temp_settings.scan_for_songs = True

        with patch.object(DownloadManager, "_scan_existing_songs") as mock_scan:
            manager = DownloadManager(temp_settings)
            mock_scan.assert_called_once()

    def test_scan_existing_songs_empty_directory(
        self, temp_settings: Settings
    ) -> None:
        """Test scanning when output directory is empty."""
        manager = DownloadManager(temp_settings)
        manager._scan_existing_songs()

        assert manager._known_songs == {}

    def test_scan_existing_songs_with_files(
        self, temp_settings: Settings, tmp_path: Path
    ) -> None:
        """Test scanning existing songs finds files with metadata."""
        # Create a mock file
        song_file = temp_settings.output_dir / "Test Artist - Test Song.mp3"
        song_file.touch()

        with patch(
            "spotdl_cli.core.downloader.extract_spotify_url",
            return_value="https://open.spotify.com/track/test123"
        ):
            manager = DownloadManager(temp_settings)
            manager._scan_existing_songs()

            assert "https://open.spotify.com/track/test123" in manager._known_songs
            assert song_file in manager._known_songs["https://open.spotify.com/track/test123"]

    def test_scan_existing_songs_handles_errors(
        self, temp_settings: Settings
    ) -> None:
        """Test scanning handles files without metadata gracefully."""
        song_file = temp_settings.output_dir / "broken.mp3"
        song_file.touch()

        with patch(
            "spotdl_cli.core.downloader.extract_spotify_url",
            side_effect=Exception("Metadata read error")
        ):
            manager = DownloadManager(temp_settings)
            manager._scan_existing_songs()

            # Should continue without crashing
            assert manager._known_songs == {}


class TestDownloadManagerSongFiltering:
    """Tests for song filtering functionality."""

    def test_is_song_archived(
        self, temp_settings: Settings, sample_song: Song
    ) -> None:
        """Test checking if song is archived."""
        manager = DownloadManager(temp_settings)
        manager._archive.add(sample_song.url)

        assert manager.is_song_archived(sample_song) is True

    def test_is_song_not_archived(
        self, temp_settings: Settings, sample_song: Song
    ) -> None:
        """Test checking if song is not archived."""
        manager = DownloadManager(temp_settings)

        assert manager.is_song_archived(sample_song) is False

    def test_is_song_known(
        self, temp_settings: Settings, sample_song: Song, tmp_path: Path
    ) -> None:
        """Test checking if song is in known songs."""
        manager = DownloadManager(temp_settings)
        manager._known_songs[sample_song.url] = [tmp_path / "song.mp3"]

        assert manager.is_song_known(sample_song) is True

    def test_is_song_not_known(
        self, temp_settings: Settings, sample_song: Song
    ) -> None:
        """Test checking if song is not known."""
        manager = DownloadManager(temp_settings)

        assert manager.is_song_known(sample_song) is False

    def test_filter_songs_removes_explicit(
        self, temp_settings: Settings, sample_song: Song, explicit_song: Song
    ) -> None:
        """Test filter removes explicit songs when skip_explicit is enabled."""
        temp_settings.skip_explicit = True
        manager = DownloadManager(temp_settings)

        songs = [sample_song, explicit_song]
        filtered = manager.filter_songs(songs)

        assert len(filtered) == 1
        assert filtered[0] == sample_song

    def test_filter_songs_keeps_explicit(
        self, temp_settings: Settings, sample_song: Song, explicit_song: Song
    ) -> None:
        """Test filter keeps explicit songs when skip_explicit is disabled."""
        temp_settings.skip_explicit = False
        manager = DownloadManager(temp_settings)

        songs = [sample_song, explicit_song]
        filtered = manager.filter_songs(songs)

        assert len(filtered) == 2

    def test_filter_songs_removes_archived(
        self, temp_settings: Settings, sample_song: Song
    ) -> None:
        """Test filter removes archived songs."""
        manager = DownloadManager(temp_settings)
        manager._archive.add(sample_song.url)

        songs = [sample_song]
        filtered = manager.filter_songs(songs)

        assert len(filtered) == 0

    def test_filter_songs_removes_known_with_skip(
        self, temp_settings: Settings, sample_song: Song, tmp_path: Path
    ) -> None:
        """Test filter removes known songs when overwrite is skip."""
        temp_settings.overwrite = "skip"
        manager = DownloadManager(temp_settings)
        manager._known_songs[sample_song.url] = [tmp_path / "song.mp3"]

        songs = [sample_song]
        filtered = manager.filter_songs(songs)

        assert len(filtered) == 0

    def test_filter_songs_keeps_known_with_overwrite(
        self, temp_settings: Settings, sample_song: Song, tmp_path: Path
    ) -> None:
        """Test filter keeps known songs when overwrite is enabled."""
        temp_settings.overwrite = "force"
        manager = DownloadManager(temp_settings)
        manager._known_songs[sample_song.url] = [tmp_path / "song.mp3"]

        songs = [sample_song]
        filtered = manager.filter_songs(songs)

        assert len(filtered) == 1


class TestDownloadManagerDownloadItem:
    """Tests for download_item functionality."""

    @pytest.mark.asyncio
    async def test_download_item_no_result(
        self, temp_settings: Settings, sample_song: Song
    ) -> None:
        """Test download_item with no result returns None and calls callback."""
        manager = DownloadManager(temp_settings)
        item = DownloadItem(song=sample_song, result=None)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status, error))

        result = await manager.download_item("test-id", item, callback)

        assert result is None
        assert len(status_updates) == 1
        assert status_updates[0][1] == DownloadStatus.FAILED
        assert "No download result" in status_updates[0][2]

    @pytest.mark.asyncio
    async def test_download_item_skip_explicit(
        self, temp_settings: Settings, explicit_song: Song, sample_result: Result
    ) -> None:
        """Test download_item skips explicit songs when configured."""
        temp_settings.skip_explicit = True
        manager = DownloadManager(temp_settings)
        item = DownloadItem(song=explicit_song, result=sample_result)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status))

        result = await manager.download_item("test-id", item, callback)

        assert result is None
        assert len(status_updates) == 1
        assert status_updates[0][1] == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_download_item_skip_archived(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item skips archived songs."""
        manager = DownloadManager(temp_settings)
        manager._archive.add(sample_download_item.song.url)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status))

        result = await manager.download_item("test-id", sample_download_item, callback)

        assert result is None
        assert status_updates[-1][1] == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_download_item_respect_skip_file(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item respects .skip files."""
        temp_settings.respect_skip_file = True
        manager = DownloadManager(temp_settings)

        # Create skip file
        expected_path = temp_settings.output_dir / "Test Artist - Test Song.mp3"
        skip_file = expected_path.with_suffix(".mp3.skip")
        skip_file.touch()

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status))

        with patch.object(
            manager._downloader, "get_output_template",
            return_value="Test Artist - Test Song"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result == expected_path
        assert status_updates[-1][1] == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_download_item_success(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test successful download_item execution."""
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status, progress))

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ) as mock_download, \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ) as mock_embed_meta, \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ) as mock_embed_lyrics, \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="Test Artist - Test Song"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result == output_file

        # Verify download was called
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[0][0] == sample_download_item.result.url

        # Verify metadata embedding
        mock_embed_meta.assert_called_once()
        embed_meta_call = mock_embed_meta.call_args
        assert embed_meta_call[0][0] == output_file
        assert isinstance(embed_meta_call[0][1], DownloadMeta)

        mock_embed_lyrics.assert_called_once_with(output_file, sample_download_item.song.lyrics)

        # Verify song was added to archive
        assert sample_download_item.song.url in manager._archive

        # Verify status progression
        statuses = [s[1] for s in status_updates]
        assert DownloadStatus.DOWNLOADING in statuses
        assert DownloadStatus.EMBEDDING in statuses
        assert DownloadStatus.COMPLETED in statuses

    @pytest.mark.asyncio
    async def test_download_item_with_progress_callback(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item progress callback is invoked."""
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        progress_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            progress_updates.append({
                "status": status,
                "progress": progress,
                "speed": speed,
                "eta": eta,
                "error": error,
            })

        # Capture the progress callback passed to download
        captured_progress_callback = None
        async def mock_download(url, meta, output_dir, progress_cb=None):
            nonlocal captured_progress_callback
            captured_progress_callback = progress_cb
            # Simulate progress updates
            if progress_cb:
                progress_cb(DownloadProgress(
                    status="downloading",
                    progress=50.0,
                    speed="1.5 MB/s",
                    eta="00:30",
                    filename="test.mp3"
                ))
                progress_cb(DownloadProgress(
                    status="finished",
                    progress=100.0,
                    speed="2.0 MB/s",
                    eta="00:00",
                    filename="test.mp3"
                ))
            return output_file

        with patch.object(
            manager._downloader, "download", side_effect=mock_download
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="Test Artist - Test Song"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        # Verify progress callbacks were received
        downloading_updates = [u for u in progress_updates if u["status"] == DownloadStatus.DOWNLOADING]
        assert len(downloading_updates) >= 1

        # Check for converting status (when status is "finished")
        converting_updates = [u for u in progress_updates if u["status"] == DownloadStatus.CONVERTING]
        assert len(converting_updates) >= 1

        # Verify progress values
        assert any(u["progress"] == 50.0 for u in progress_updates)

    @pytest.mark.asyncio
    async def test_download_item_creates_skip_file(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item creates skip file when configured."""
        temp_settings.create_skip_file = True
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"
        output_file.touch()

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item)

        skip_file = output_file.with_suffix(".mp3.skip")
        assert skip_file.exists()

    @pytest.mark.asyncio
    async def test_download_item_generates_lrc(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item generates LRC file when configured."""
        temp_settings.generate_lrc = True
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ), \
        patch("spotdl_cli.core.downloader.generate_lrc") as mock_generate_lrc:
            result = await manager.download_item("test-id", sample_download_item)

        mock_generate_lrc.assert_called_once()
        call_args = mock_generate_lrc.call_args[0]
        assert call_args[0] == sample_download_item.song.name
        assert call_args[1] == list(sample_download_item.song.artists)
        assert call_args[2] == output_file
        assert call_args[3] == sample_download_item.song.lyrics

    @pytest.mark.asyncio
    async def test_download_item_no_lyrics_skip_embed(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item skips lyrics embedding when song has no lyrics."""
        sample_download_item.song.lyrics = None
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ) as mock_embed_lyrics, \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item)

        mock_embed_lyrics.assert_not_called()


class TestDownloadManagerErrorHandling:
    """Tests for download error handling."""

    @pytest.mark.asyncio
    async def test_download_item_download_error(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item handles DownloadError."""
        manager = DownloadManager(temp_settings)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status, error))

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=DownloadError("Video unavailable")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result is None
        assert status_updates[-1][1] == DownloadStatus.FAILED
        assert "Video unavailable" in status_updates[-1][2]

    @pytest.mark.asyncio
    async def test_download_item_download_error_strips_ansi(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item strips ANSI codes from error messages."""
        manager = DownloadManager(temp_settings)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status, error))

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=DownloadError("\x1b[31mError message\x1b[0m")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result is None
        # ANSI codes should be stripped
        assert "\x1b" not in status_updates[-1][2]
        assert "Error message" in status_updates[-1][2]

    @pytest.mark.asyncio
    async def test_download_item_generic_exception(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item handles generic exceptions."""
        manager = DownloadManager(temp_settings)

        status_updates = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            status_updates.append((item_id, status, error))

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=ValueError("Unexpected error")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result is None
        assert status_updates[-1][1] == DownloadStatus.FAILED
        assert "Unexpected error" in status_updates[-1][2]

    @pytest.mark.asyncio
    async def test_download_item_add_unavailable_on_error(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item adds to archive when add_unavailable is enabled."""
        temp_settings.add_unavailable = True
        manager = DownloadManager(temp_settings)

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=DownloadError("Not found")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item)

        # Song should be added to archive
        assert sample_download_item.song.url in manager._archive

    @pytest.mark.asyncio
    async def test_download_item_log_error_print_errors(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test _log_error prints traceback when print_errors is enabled."""
        temp_settings.print_errors = True
        manager = DownloadManager(temp_settings)

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=DownloadError("Test error")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ), \
        patch("traceback.print_exc") as mock_print_exc:
            result = await manager.download_item("test-id", sample_download_item)

        mock_print_exc.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_item_log_error_save_errors(
        self, temp_settings: Settings, sample_download_item: DownloadItem,
        tmp_path: Path
    ) -> None:
        """Test _log_error saves errors to file when save_errors is configured."""
        error_file = tmp_path / "errors.txt"
        temp_settings.save_errors = str(error_file)
        manager = DownloadManager(temp_settings)

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            side_effect=DownloadError("Test error")
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item)

        # Error file should be created
        assert error_file.exists()
        content = error_file.read_text()
        assert "Test Artist - Test Song" in content
        assert sample_download_item.song.url in content
        assert "Test error" in content


class TestDownloadManagerCleanup:
    """Tests for cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_close_saves_archive(
        self, temp_settings: Settings, tmp_path: Path
    ) -> None:
        """Test close saves archive when configured."""
        archive_path = tmp_path / "archive.txt"
        temp_settings.archive = archive_path
        manager = DownloadManager(temp_settings)

        # Add some URLs to archive
        manager._archive.add("https://open.spotify.com/track/test1")
        manager._archive.add("https://open.spotify.com/track/test2")

        with patch.object(
            manager._downloader, "close", new_callable=AsyncMock
        ) as mock_close:
            await manager.close()

        # Verify downloader close was called
        mock_close.assert_called_once()

        # Verify archive was saved
        assert archive_path.exists()
        content = archive_path.read_text()
        assert "test1" in content
        assert "test2" in content

    @pytest.mark.asyncio
    async def test_close_sets_stop_event(self, temp_settings: Settings) -> None:
        """Test close sets the stop event."""
        manager = DownloadManager(temp_settings)

        with patch.object(manager._downloader, "close", new_callable=AsyncMock):
            await manager.close()

        assert manager._stop_event.is_set()

    @pytest.mark.asyncio
    async def test_close_cancels_active_tasks(self, temp_settings: Settings) -> None:
        """Test close cancels all active tasks."""
        manager = DownloadManager(temp_settings)

        # Create mock tasks
        mock_task1 = AsyncMock(spec=asyncio.Task)
        mock_task2 = AsyncMock(spec=asyncio.Task)
        manager._active_tasks = {
            "task1": mock_task1,
            "task2": mock_task2,
        }

        with patch.object(
            manager._downloader, "close", new_callable=AsyncMock
        ), \
        patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:
            await manager.close()

        # Verify tasks were cancelled
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()

        # Verify gather was called with return_exceptions=True
        mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_archive_no_save(self, temp_settings: Settings) -> None:
        """Test close doesn't save archive when not configured."""
        temp_settings.archive = None
        manager = DownloadManager(temp_settings)

        with patch.object(
            manager._downloader, "close", new_callable=AsyncMock
        ), \
        patch.object(Archive, "save") as mock_save:
            await manager.close()

        # Archive save should not be called
        mock_save.assert_not_called()


class TestDownloadManagerStatusCallbacks:
    """Tests for status callback functionality."""

    @pytest.mark.asyncio
    async def test_callback_not_provided(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test download_item works without callback."""
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, None)

        # Should complete successfully
        assert result == output_file

    @pytest.mark.asyncio
    async def test_callback_receives_all_parameters(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test callback receives all expected parameters."""
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        callback_calls = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            callback_calls.append({
                "item_id": item_id,
                "status": status,
                "progress": progress,
                "speed": speed,
                "eta": eta,
                "error": error,
            })

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        # Verify callback was called with proper parameters
        assert len(callback_calls) > 0
        for call in callback_calls:
            assert call["item_id"] == "test-id"
            assert isinstance(call["status"], DownloadStatus)
            assert isinstance(call["progress"], float)
            assert isinstance(call["speed"], str)
            assert isinstance(call["eta"], str)
            assert call["error"] is None or isinstance(call["error"], str)

    @pytest.mark.asyncio
    async def test_callback_status_progression(
        self, temp_settings: Settings, sample_download_item: DownloadItem
    ) -> None:
        """Test callback shows proper status progression."""
        manager = DownloadManager(temp_settings)
        output_file = temp_settings.output_dir / "output.mp3"

        statuses = []
        def callback(item_id: str, status: DownloadStatus, progress: float,
                     speed: str, eta: str, error: str | None) -> None:
            statuses.append(status)

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock,
            return_value=output_file
        ), \
        patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ), \
        patch.object(
            manager._downloader, "get_output_template",
            return_value="output"
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        # Verify proper status progression
        assert statuses[0] == DownloadStatus.DOWNLOADING
        assert DownloadStatus.EMBEDDING in statuses
        assert statuses[-1] == DownloadStatus.COMPLETED
