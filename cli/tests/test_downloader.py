"""Tests for downloader module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from spotdl_cli.config import Settings
from spotdl_cli.core.downloader import (
    Downloader,
    DownloadManager,
    DownloadProgress,
    DownloadError,
)
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Song,
    TargetPlatform,
)


class TestDownloader:
    """Tests for Downloader class."""

    @pytest.fixture
    def downloader(self, settings: Settings, tmp_path: Path) -> Downloader:
        """Create test downloader with temp directory."""
        settings.output_dir = tmp_path / "downloads"
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        return Downloader(settings)

    def test_sanitize_filename(self) -> None:
        """Test filename sanitization."""
        assert Downloader._sanitize_filename("Normal Name") == "Normal Name"
        assert Downloader._sanitize_filename("Name/With/Slashes") == "Name_With_Slashes"
        assert Downloader._sanitize_filename("Name:With:Colons") == "Name_With_Colons"
        assert Downloader._sanitize_filename("...Leading") == "Leading"
        assert Downloader._sanitize_filename("   Spaces   ") == "Spaces"
        assert Downloader._sanitize_filename("") == "Unknown"

        # Test length limit
        long_name = "A" * 300
        result = Downloader._sanitize_filename(long_name)
        assert len(result) <= 200

    def test_format_speed(self) -> None:
        """Test speed formatting."""
        assert Downloader._format_speed(500) == "500 B/s"
        assert Downloader._format_speed(1500) == "1.5 KB/s"
        assert Downloader._format_speed(1500000) == "1.4 MB/s"

    def test_format_eta(self) -> None:
        """Test ETA formatting."""
        assert Downloader._format_eta(30) == "30s"
        assert Downloader._format_eta(90) == "1m 30s"
        assert Downloader._format_eta(3700) == "1h 1m"

    def test_get_output_template(
        self, downloader: Downloader, sample_song: Song
    ) -> None:
        """Test output template generation."""
        result = downloader._get_output_template(sample_song)
        assert "Test Artist" in result
        assert "Test Song" in result

    def test_get_output_template_custom(
        self, settings: Settings, sample_song: Song, tmp_path: Path
    ) -> None:
        """Test custom output template."""
        settings.output_dir = tmp_path
        settings.output_template = "{album}/{artist} - {title}"
        downloader = Downloader(settings)

        result = downloader._get_output_template(sample_song)
        assert "Test Album" in result
        assert "Test Artist" in result
        assert "Test Song" in result

    @pytest.mark.asyncio
    async def test_close(self, downloader: Downloader) -> None:
        """Test closing the downloader."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        downloader._http_client = mock_client

        await downloader.close()

        mock_client.aclose.assert_called_once()
        assert downloader._http_client is None

    @pytest.mark.asyncio
    async def test_download_cover_success(self, downloader: Downloader) -> None:
        """Test downloading cover art."""
        mock_response = MagicMock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(downloader, "_get_http_client", return_value=mock_client):
            result = await downloader._download_cover("https://example.com/cover.jpg")

        assert result == b"fake image data"

    @pytest.mark.asyncio
    async def test_download_cover_failure(self, downloader: Downloader) -> None:
        """Test downloading cover art failure."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch.object(downloader, "_get_http_client", return_value=mock_client):
            result = await downloader._download_cover("https://example.com/cover.jpg")

        assert result is None

    def test_find_output_file(
        self, downloader: Downloader, settings: Settings
    ) -> None:
        """Test finding output file."""
        output_dir = settings.output_dir
        base_path = output_dir / "test_file"

        # No file exists
        assert downloader._find_output_file(base_path) is None

        # Create mp3 file
        mp3_path = base_path.with_suffix(".mp3")
        mp3_path.touch()

        assert downloader._find_output_file(base_path) == mp3_path

    def test_get_yt_dlp_options(
        self, downloader: Downloader, settings: Settings
    ) -> None:
        """Test yt-dlp options generation."""
        output_path = Path("/tmp/test")
        options = downloader._get_yt_dlp_options(output_path)

        assert options["format"] == "bestaudio/best"
        assert options["quiet"] is True
        assert "postprocessors" in options

        # Check audio format
        postprocessor = options["postprocessors"][0]
        assert postprocessor["key"] == "FFmpegExtractAudio"
        assert postprocessor["preferredcodec"] == "mp3"

    def test_get_yt_dlp_options_with_progress_callback(
        self, downloader: Downloader
    ) -> None:
        """Test yt-dlp options with progress callback."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        output_path = Path("/tmp/test")
        options = downloader._get_yt_dlp_options(output_path, callback)

        assert "progress_hooks" in options
        assert len(options["progress_hooks"]) == 1

        # Simulate progress hook call
        hook = options["progress_hooks"][0]
        hook({
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 100,
            "_speed_str": "1.5 MB/s",
            "_eta_str": "00:30",
        })

        assert len(progress_updates) == 1
        assert progress_updates[0].progress == 50.0
        assert progress_updates[0].speed == "1.5 MB/s"


class TestDownloadProgress:
    """Tests for DownloadProgress class."""

    def test_default_values(self) -> None:
        """Test default progress values."""
        progress = DownloadProgress()

        assert progress.status == ""
        assert progress.progress == 0.0
        assert progress.speed == ""
        assert progress.eta == ""
        assert progress.filename == ""


class TestDownloadManager:
    """Tests for DownloadManager class."""

    @pytest.fixture
    def manager(self, settings: Settings) -> DownloadManager:
        """Create test download manager."""
        return DownloadManager(settings, max_concurrent=2)

    @pytest.mark.asyncio
    async def test_close(self, manager: DownloadManager) -> None:
        """Test closing the manager."""
        with patch.object(manager._downloader, "close", new_callable=AsyncMock) as mock_close:
            await manager.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_item_no_result(
        self,
        manager: DownloadManager,
        sample_song: Song,
    ) -> None:
        """Test download_item with no result."""
        item = DownloadItem(song=sample_song, result=None)
        status_updates = []

        def callback(
            item_id: str,
            status: DownloadStatus,
            progress: float,
            speed: str,
            eta: str,
            error: str | None,
        ) -> None:
            status_updates.append((item_id, status, error))

        result = await manager.download_item("test-id", item, callback)

        assert result is None
        assert len(status_updates) == 1
        assert status_updates[0][1] == DownloadStatus.FAILED
        assert "No download result" in status_updates[0][2]

    @pytest.mark.asyncio
    async def test_download_item_success(
        self,
        manager: DownloadManager,
        sample_download_item: DownloadItem,
        tmp_path: Path,
    ) -> None:
        """Test successful download."""
        output_file = tmp_path / "output.mp3"
        output_file.touch()

        status_updates = []

        def callback(
            item_id: str,
            status: DownloadStatus,
            progress: float,
            speed: str,
            eta: str,
            error: str | None,
        ) -> None:
            status_updates.append((item_id, status))

        with patch.object(
            manager._downloader, "download", new_callable=AsyncMock, return_value=output_file
        ), patch.object(
            manager._downloader, "embed_metadata", new_callable=AsyncMock
        ), patch.object(
            manager._downloader, "embed_lyrics", new_callable=AsyncMock
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result == output_file
        # Check status progression
        statuses = [s[1] for s in status_updates]
        assert DownloadStatus.DOWNLOADING in statuses
        assert DownloadStatus.EMBEDDING in statuses
        assert DownloadStatus.COMPLETED in statuses

    @pytest.mark.asyncio
    async def test_download_item_error(
        self,
        manager: DownloadManager,
        sample_download_item: DownloadItem,
    ) -> None:
        """Test download with error."""
        status_updates = []

        def callback(
            item_id: str,
            status: DownloadStatus,
            progress: float,
            speed: str,
            eta: str,
            error: str | None,
        ) -> None:
            status_updates.append((item_id, status, error))

        with patch.object(
            manager._downloader,
            "download",
            new_callable=AsyncMock,
            side_effect=DownloadError("Test error"),
        ):
            result = await manager.download_item("test-id", sample_download_item, callback)

        assert result is None
        # Last status should be failed
        assert status_updates[-1][1] == DownloadStatus.FAILED
        assert "Test error" in status_updates[-1][2]
