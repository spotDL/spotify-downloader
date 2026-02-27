"""Tests for DownloadService."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from spotdl.core.services.download import (
    ALLOWED_SCHEMES,
    COVER_URL_ALLOWLIST,
    DownloadService,
    DownloadProgress,
    DownloadRequest,
    DownloadSettings,
    DownloadStatus,
    create_download_id,
    get_download_service,
    is_safe_url,
)
from spotdl_core.download import DownloadError, DownloadMeta


class TestIsSafeUrl:
    """Tests for URL validation."""

    def test_safe_url_spotify(self) -> None:
        """Test that Spotify CDN URLs are safe."""
        assert is_safe_url("https://i.scdn.co/image/abc123") is True

    def test_safe_url_youtube(self) -> None:
        """Test that YouTube CDN URLs are safe."""
        assert is_safe_url("https://i.ytimg.com/vi/abc123/maxresdefault.jpg") is True

    def test_safe_url_apple(self) -> None:
        """Test that Apple Music CDN URLs are safe."""
        assert is_safe_url("https://is1-ssl.mzstatic.com/image/thumb/abc123") is True

    def test_unsafe_url_http(self) -> None:
        """Test that HTTP URLs are allowed (they get upgraded to HTTPS)."""
        # HTTP is in ALLOWED_SCHEMES, so it returns True
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (None, None, None, None, ("1.2.3.4", 80))
            ]
            with patch("ipaddress.ip_address") as mock_ip:
                mock_ip_instance = Mock()
                mock_ip_instance.is_private = False
                mock_ip_instance.is_loopback = False
                mock_ip_instance.is_link_local = False
                mock_ip_instance.is_reserved = False
                mock_ip_instance.is_multicast = False
                mock_ip_instance.__str__ = Mock(return_value="1.2.3.4")
                mock_ip.return_value = mock_ip_instance
                assert is_safe_url("http://i.scdn.co/image/abc123") is True

    def test_unsafe_url_ftp(self) -> None:
        """Test that FTP URLs are rejected."""
        assert is_safe_url("ftp://example.com/file") is False

    def test_unsafe_url_invalid_domain(self) -> None:
        """Test that URLs from non-whitelisted domains are rejected."""
        assert is_safe_url("https://evil.com/image.jpg") is False

    def test_unsafe_url_no_hostname(self) -> None:
        """Test that URLs without hostname are rejected."""
        assert is_safe_url("https:///path/file") is False

    def test_unsafe_url_private_ip(self) -> None:
        """Test that private IP addresses are rejected."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (None, None, None, None, ("192.168.1.1", 80))
            ]
            assert is_safe_url("https://i.scdn.co/image/test") is False

    def test_unsafe_url_loopback(self) -> None:
        """Test that loopback addresses are rejected."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (None, None, None, None, ("127.0.0.1", 80))
            ]
            assert is_safe_url("https://i.scdn.co/image/test") is False

    def test_unsafe_url_metadata_service(self) -> None:
        """Test that AWS metadata service IP is rejected."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (None, None, None, None, ("169.254.169.254", 80))
            ]
            assert is_safe_url("https://i.scdn.co/image/test") is False

    def test_unsafe_url_dns_error(self) -> None:
        """Test that DNS errors result in rejection."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            import socket

            mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")
            assert is_safe_url("https://i.scdn.co/image/test") is False

    def test_unsafe_url_malformed(self) -> None:
        """Test that malformed URLs are rejected."""
        assert is_safe_url("not a url") is False

    def test_safe_url_subdomain(self) -> None:
        """Test that subdomains of whitelisted domains are accepted."""
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (None, None, None, None, ("1.2.3.4", 80))
            ]
            with patch("ipaddress.ip_address") as mock_ip:
                mock_ip_instance = Mock()
                mock_ip_instance.is_private = False
                mock_ip_instance.is_loopback = False
                mock_ip_instance.is_link_local = False
                mock_ip_instance.is_reserved = False
                mock_ip_instance.is_multicast = False
                mock_ip_instance.__str__ = Mock(return_value="1.2.3.4")
                mock_ip.return_value = mock_ip_instance
                assert is_safe_url("https://cdn.i.scdn.co/image/test") is True


class TestDownloadStatus:
    """Tests for DownloadStatus enum."""

    def test_status_values(self) -> None:
        """Test that all status values are strings."""
        assert DownloadStatus.PENDING.value == "pending"
        assert DownloadStatus.DOWNLOADING.value == "downloading"
        assert DownloadStatus.PROCESSING.value == "processing"
        assert DownloadStatus.EMBEDDING.value == "embedding"
        assert DownloadStatus.COMPLETED.value == "completed"
        assert DownloadStatus.FAILED.value == "failed"
        assert DownloadStatus.CANCELLED.value == "cancelled"


class TestDownloadSettings:
    """Tests for DownloadSettings."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = DownloadSettings()
        assert settings.audio_format == "mp3"
        assert settings.audio_quality == "best"
        assert settings.output_template == "{artist} - {title}"
        assert settings.max_filename_length == 255
        assert settings.embed_metadata is True
        assert settings.embed_lyrics is True
        assert settings.embed_cover is True
        assert settings.id3_separator == "/"
        assert settings.sponsor_block is False
        assert settings.generate_lrc is False

    def test_from_defaults(self) -> None:
        """Test from_defaults class method."""
        settings = DownloadSettings.from_defaults()
        assert isinstance(settings, DownloadSettings)
        assert settings.audio_format == "mp3"

    def test_from_user_settings(self) -> None:
        """Test from_user_settings with mock user settings."""
        mock_settings = Mock()
        mock_settings.audio_format = "flac"
        mock_settings.audio_quality = "320k"
        mock_settings.bitrate = "320k"
        mock_settings.output_template = "{title}"
        mock_settings.max_filename_length = 200
        mock_settings.restrict = "ascii"
        mock_settings.overwrite = "force"
        mock_settings.embed_metadata = False
        mock_settings.embed_lyrics = False
        mock_settings.embed_cover = False
        mock_settings.id3_separator = ","
        mock_settings.sponsor_block = True
        mock_settings.generate_lrc = True
        mock_settings.playlist_numbering = True
        mock_settings.skip_explicit = True
        mock_settings.ffmpeg_args = "-vn"
        mock_settings.yt_dlp_args = "--no-warnings"
        mock_settings.proxy = "http://proxy:8080"
        mock_settings.cookie_file = "/tmp/cookies.txt"
        mock_settings.archive = "/tmp/archive.txt"

        settings = DownloadSettings.from_user_settings(mock_settings)
        assert settings.audio_format == "flac"
        assert settings.audio_quality == "320k"
        assert settings.bitrate == "320k"
        assert settings.embed_metadata is False
        assert settings.sponsor_block is True

    def test_from_user_settings_none_values(self) -> None:
        """Test from_user_settings with None values uses defaults."""
        mock_settings = Mock()
        mock_settings.audio_format = None
        mock_settings.audio_quality = None
        mock_settings.bitrate = None
        mock_settings.output_template = None
        mock_settings.max_filename_length = None
        mock_settings.restrict = None
        mock_settings.overwrite = None
        mock_settings.embed_metadata = None
        mock_settings.embed_lyrics = None
        mock_settings.embed_cover = None
        mock_settings.id3_separator = None
        mock_settings.sponsor_block = False
        mock_settings.generate_lrc = False
        mock_settings.playlist_numbering = False
        mock_settings.skip_explicit = False
        mock_settings.ffmpeg_args = None
        mock_settings.yt_dlp_args = None
        mock_settings.proxy = None
        mock_settings.cookie_file = None
        mock_settings.archive = None

        settings = DownloadSettings.from_user_settings(mock_settings)
        assert settings.audio_format == "mp3"
        assert settings.audio_quality == "best"
        assert settings.embed_metadata is True

    def test_to_core_settings(self) -> None:
        """Test conversion to core settings."""
        settings = DownloadSettings(
            audio_format="flac",
            audio_quality="best",
            embed_metadata=True,
        )
        core_settings = settings.to_core_settings()
        assert core_settings.audio_format == "flac"
        assert core_settings.audio_quality == "best"
        assert core_settings.embed_metadata is True

    def test_to_core_settings_with_cookie_file(self) -> None:
        """Test conversion with existing cookie file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cookie_path = tmp.name

        try:
            settings = DownloadSettings(cookie_file=cookie_path)
            core_settings = settings.to_core_settings()
            assert core_settings.cookies_path == Path(cookie_path)
        finally:
            Path(cookie_path).unlink()

    def test_to_core_settings_with_nonexistent_cookie_file(self) -> None:
        """Test conversion with non-existent cookie file."""
        settings = DownloadSettings(cookie_file="/nonexistent/cookies.txt")
        core_settings = settings.to_core_settings()
        assert core_settings.cookies_path is None


class TestDownloadProgress:
    """Tests for DownloadProgress."""

    def test_progress_creation(self) -> None:
        """Test creating download progress."""
        progress = DownloadProgress(
            download_id="test-id",
            status=DownloadStatus.PENDING,
        )
        assert progress.download_id == "test-id"
        assert progress.status == DownloadStatus.PENDING
        assert progress.progress == 0.0
        assert progress.speed is None
        assert progress.eta is None
        assert progress.filename is None
        assert progress.error is None
        assert isinstance(progress.created_at, datetime)
        assert progress.completed_at is None

    def test_progress_to_dict(self) -> None:
        """Test converting progress to dict."""
        progress = DownloadProgress(
            download_id="test-id",
            status=DownloadStatus.DOWNLOADING,
            progress=50.0,
            speed="1.5 MiB/s",
            eta="00:30",
            filename="test.mp3",
        )
        data = progress.to_dict()
        assert data["download_id"] == "test-id"
        assert data["status"] == "downloading"
        assert data["progress"] == 50.0
        assert data["speed"] == "1.5 MiB/s"
        assert data["eta"] == "00:30"
        assert data["filename"] == "test.mp3"
        assert data["error"] is None
        assert "created_at" in data
        assert data["completed_at"] is None

    def test_progress_to_dict_with_completed(self) -> None:
        """Test converting completed progress to dict."""
        completed_at = datetime.now()
        progress = DownloadProgress(
            download_id="test-id",
            status=DownloadStatus.COMPLETED,
            progress=100.0,
            completed_at=completed_at,
        )
        data = progress.to_dict()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        assert data["completed_at"] == completed_at.isoformat()


class TestDownloadRequest:
    """Tests for DownloadRequest."""

    def test_request_creation(self) -> None:
        """Test creating download request."""
        request = DownloadRequest(
            download_id="test-id",
            url="https://youtube.com/watch?v=test",
            title="Test Song",
            artist="Test Artist",
        )
        assert request.download_id == "test-id"
        assert request.url == "https://youtube.com/watch?v=test"
        assert request.title == "Test Song"
        assert request.artist == "Test Artist"

    def test_request_to_meta(self) -> None:
        """Test converting request to DownloadMeta."""
        request = DownloadRequest(
            download_id="test-id",
            url="https://youtube.com/watch?v=test",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            cover_url="https://i.scdn.co/image/abc123",
            duration=180,
            artists=["Artist 1", "Artist 2"],
            year=2024,
            track_number=1,
            isrc="USRC12345678",
        )
        meta = request.to_meta()
        assert isinstance(meta, DownloadMeta)
        assert meta.title == "Test Song"
        assert meta.artist == "Test Artist"
        assert meta.artists == ["Artist 1", "Artist 2"]
        assert meta.album == "Test Album"
        assert meta.year == 2024
        assert meta.track_number == 1
        assert meta.isrc == "USRC12345678"

    def test_request_to_meta_with_unsafe_cover(self) -> None:
        """Test that unsafe cover URLs are filtered out."""
        request = DownloadRequest(
            download_id="test-id",
            url="https://youtube.com/watch?v=test",
            title="Test Song",
            artist="Test Artist",
            cover_url="https://evil.com/image.jpg",
        )
        meta = request.to_meta()
        assert meta.cover_url is None

    def test_request_to_meta_with_safe_cover(self) -> None:
        """Test that safe cover URLs are preserved."""
        with patch("spotdl.core.services.download.is_safe_url", return_value=True):
            request = DownloadRequest(
                download_id="test-id",
                url="https://youtube.com/watch?v=test",
                title="Test Song",
                artist="Test Artist",
                cover_url="https://i.scdn.co/image/abc123",
            )
            meta = request.to_meta()
            assert meta.cover_url == "https://i.scdn.co/image/abc123"

    def test_request_to_meta_default_artists(self) -> None:
        """Test that artist is used as default for artists list."""
        request = DownloadRequest(
            download_id="test-id",
            url="https://youtube.com/watch?v=test",
            title="Test Song",
            artist="Test Artist",
        )
        meta = request.to_meta()
        assert meta.artists == ["Test Artist"]


class TestDownloadService:
    """Tests for DownloadService."""

    @pytest.fixture
    def download_manager(self, tmp_path: Path) -> DownloadService:
        """Create a download manager with temporary directory."""
        return DownloadService(download_dir=tmp_path)

    @pytest.fixture
    def sample_request(self) -> DownloadRequest:
        """Create a sample download request."""
        return DownloadRequest(
            download_id="test-download-123",
            url="https://youtube.com/watch?v=test123",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
        )

    def test_init_default_dir(self) -> None:
        """Test initialization with default directory."""
        manager = DownloadService()
        assert manager.download_dir.exists()

    def test_init_custom_dir(self, tmp_path: Path) -> None:
        """Test initialization with custom directory."""
        manager = DownloadService(download_dir=tmp_path)
        assert manager.download_dir == tmp_path
        assert manager.download_dir.exists()

    def test_get_progress_nonexistent(self, download_manager: DownloadService) -> None:
        """Test getting progress for nonexistent download."""
        progress = download_manager.get_progress("nonexistent")
        assert progress is None

    def test_get_all_downloads_empty(self, download_manager: DownloadService) -> None:
        """Test getting all downloads when empty."""
        downloads = download_manager.get_all_downloads()
        assert downloads == []

    @pytest.mark.asyncio
    async def test_start_download(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
    ) -> None:
        """Test starting a download."""
        with patch.object(
            download_manager, "_download_task", new_callable=AsyncMock
        ) as mock_task:
            mock_task.return_value = None

            download_id = await download_manager.start_download(sample_request)
            assert download_id == "test-download-123"

            progress = download_manager.get_progress(download_id)
            assert progress is not None
            assert progress.status == DownloadStatus.PENDING
            assert progress.download_id == download_id

    @pytest.mark.asyncio
    async def test_start_download_with_settings(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
    ) -> None:
        """Test starting download with custom settings."""
        settings = DownloadSettings(audio_format="flac", audio_quality="best")

        with patch.object(
            download_manager, "_download_task", new_callable=AsyncMock
        ) as mock_task:
            mock_task.return_value = None

            download_id = await download_manager.start_download(
                sample_request, settings
            )
            assert download_id == "test-download-123"

    @pytest.mark.asyncio
    async def test_cancel_download(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
    ) -> None:
        """Test cancelling a download."""
        with patch.object(
            download_manager, "_download_task", new_callable=AsyncMock
        ) as mock_task:
            mock_task.return_value = None

            download_id = await download_manager.start_download(sample_request)

            # Create a mock task
            mock_async_task = AsyncMock()
            download_manager._tasks[download_id] = mock_async_task

            result = await download_manager.cancel_download(download_id)
            assert result is True

            mock_async_task.cancel.assert_called_once()

            progress = download_manager.get_progress(download_id)
            assert progress.status == DownloadStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_download(
        self, download_manager: DownloadService
    ) -> None:
        """Test cancelling nonexistent download."""
        result = await download_manager.cancel_download("nonexistent")
        assert result is False

    def test_register_callback(self, download_manager: DownloadService) -> None:
        """Test registering progress callback."""
        callback = Mock()
        download_manager.register_callback("test-id", callback)
        assert "test-id" in download_manager._progress_callbacks
        assert callback in download_manager._progress_callbacks["test-id"]

    def test_unregister_callback(self, download_manager: DownloadService) -> None:
        """Test unregistering progress callback."""
        callback = Mock()
        download_manager.register_callback("test-id", callback)
        download_manager.unregister_callback("test-id", callback)
        assert callback not in download_manager._progress_callbacks["test-id"]

    def test_unregister_nonexistent_callback(
        self, download_manager: DownloadService
    ) -> None:
        """Test unregistering nonexistent callback doesn't raise."""
        callback = Mock()
        download_manager.unregister_callback("test-id", callback)

    def test_notify_progress(self, download_manager: DownloadService) -> None:
        """Test notifying progress callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        download_manager._downloads["test-id"] = DownloadProgress(
            download_id="test-id",
            status=DownloadStatus.DOWNLOADING,
            progress=50.0,
        )

        download_manager.register_callback("test-id", callback1)
        download_manager.register_callback("test-id", callback2)

        download_manager._notify_progress("test-id")

        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_notify_progress_with_error(
        self, download_manager: DownloadService
    ) -> None:
        """Test that callback errors are handled gracefully."""
        callback = Mock(side_effect=Exception("Callback error"))

        download_manager._downloads["test-id"] = DownloadProgress(
            download_id="test-id",
            status=DownloadStatus.DOWNLOADING,
        )

        download_manager.register_callback("test-id", callback)
        download_manager._notify_progress("test-id")

    def test_get_file_path_completed(
        self, download_manager: DownloadService, tmp_path: Path
    ) -> None:
        """Test getting file path for completed download."""
        download_id = "test-id"
        filename = "Test Artist - Test Song.mp3"

        download_manager._downloads[download_id] = DownloadProgress(
            download_id=download_id,
            status=DownloadStatus.COMPLETED,
            filename=filename,
        )

        download_dir = download_manager.download_dir / download_id
        download_dir.mkdir(parents=True, exist_ok=True)
        file_path = download_dir / filename
        file_path.touch()

        result = download_manager.get_file_path(download_id)
        assert result == file_path

    def test_get_file_path_not_completed(
        self, download_manager: DownloadService
    ) -> None:
        """Test getting file path for incomplete download."""
        download_id = "test-id"

        download_manager._downloads[download_id] = DownloadProgress(
            download_id=download_id,
            status=DownloadStatus.DOWNLOADING,
        )

        result = download_manager.get_file_path(download_id)
        assert result is None

    def test_get_file_path_file_not_found(
        self, download_manager: DownloadService
    ) -> None:
        """Test getting file path when file doesn't exist."""
        download_id = "test-id"

        download_manager._downloads[download_id] = DownloadProgress(
            download_id=download_id,
            status=DownloadStatus.COMPLETED,
            filename="nonexistent.mp3",
        )

        result = download_manager.get_file_path(download_id)
        assert result is None

    def test_get_file_path_fallback_search(
        self, download_manager: DownloadService, tmp_path: Path
    ) -> None:
        """Test fallback file search when exact filename doesn't exist."""
        download_id = "test-id"

        download_manager._downloads[download_id] = DownloadProgress(
            download_id=download_id,
            status=DownloadStatus.COMPLETED,
            filename="wrong-name.mp3",
        )

        download_dir = download_manager.download_dir / download_id
        download_dir.mkdir(parents=True, exist_ok=True)
        actual_file = download_dir / "actual-file.mp3"
        actual_file.touch()

        result = download_manager.get_file_path(download_id)
        assert result == actual_file

    @pytest.mark.asyncio
    async def test_download_task_success(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
        tmp_path: Path,
    ) -> None:
        """Test successful download task."""
        output_file = tmp_path / "output.mp3"
        output_file.touch()

        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.return_value = output_file
        mock_downloader.embed_metadata.return_value = None
        mock_downloader.embed_lyrics.return_value = None
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            with patch.object(download_manager, "_fetch_lyrics", return_value=None):
                result = await download_manager._download_task(sample_request)

        assert result == output_file
        mock_downloader.download.assert_called_once()
        mock_downloader.embed_metadata.assert_called_once()
        mock_downloader.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_task_with_lyrics(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
        tmp_path: Path,
    ) -> None:
        """Test download task with lyrics."""
        output_file = tmp_path / "output.mp3"
        output_file.touch()

        sample_request.lyrics = "Test lyrics"

        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.return_value = output_file
        mock_downloader.embed_metadata.return_value = None
        mock_downloader.embed_lyrics.return_value = None
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            result = await download_manager._download_task(sample_request)

        assert result == output_file
        mock_downloader.embed_lyrics.assert_called_once_with(output_file, "Test lyrics")

    @pytest.mark.asyncio
    async def test_download_task_with_lrc_generation(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
        tmp_path: Path,
    ) -> None:
        """Test download task with LRC file generation."""
        output_file = tmp_path / "output.mp3"
        output_file.touch()

        settings = DownloadSettings(generate_lrc=True)

        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.return_value = output_file
        mock_downloader.embed_metadata.return_value = None
        mock_downloader.embed_lyrics.return_value = None
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            with patch("spotdl.core.services.download.generate_lrc") as mock_lrc:
                with patch.object(download_manager, "_fetch_lyrics", return_value=None):
                    result = await download_manager._download_task(sample_request, settings)

        assert result == output_file
        mock_lrc.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_task_with_format_override(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
        tmp_path: Path,
    ) -> None:
        """Test download task with format override."""
        output_file = tmp_path / "output.flac"
        output_file.touch()

        sample_request.output_format = "flac"
        sample_request.quality = "best"

        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.return_value = output_file
        mock_downloader.embed_metadata.return_value = None
        mock_downloader.embed_lyrics.return_value = None
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            with patch.object(download_manager, "_fetch_lyrics", return_value=None):
                result = await download_manager._download_task(sample_request)

        assert result == output_file

    @pytest.mark.asyncio
    async def test_download_task_cancelled(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
    ) -> None:
        """Test download task cancellation."""
        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.side_effect = asyncio.CancelledError()
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            with pytest.raises(asyncio.CancelledError):
                await download_manager._download_task(sample_request)

        mock_downloader.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_task_error(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
    ) -> None:
        """Test download task error handling."""
        # Initialize progress before running task
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.side_effect = DownloadError("Download failed")
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            result = await download_manager._download_task(sample_request)

        assert result is None
        mock_downloader.close.assert_called_once()

        # Check that progress is updated with error
        progress = download_manager.get_progress(sample_request.download_id)
        assert progress is not None
        assert progress.status == DownloadStatus.FAILED
        assert "Download failed" in progress.error

    @pytest.mark.asyncio
    async def test_download_task_progress_updates(
        self,
        download_manager: DownloadService,
        sample_request: DownloadRequest,
        tmp_path: Path,
    ) -> None:
        """Test that download task updates progress."""
        output_file = tmp_path / "output.mp3"
        output_file.touch()

        # Initialize progress
        download_manager._downloads[sample_request.download_id] = DownloadProgress(
            download_id=sample_request.download_id,
            status=DownloadStatus.PENDING,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download.return_value = output_file
        mock_downloader.embed_metadata.return_value = None
        mock_downloader.embed_lyrics.return_value = None
        mock_downloader.close.return_value = None

        with patch("spotdl.core.services.download.Downloader", return_value=mock_downloader):
            with patch.object(download_manager, "_fetch_lyrics", return_value=None):
                result = await download_manager._download_task(sample_request)

        progress = download_manager.get_progress(sample_request.download_id)
        assert progress.status == DownloadStatus.COMPLETED
        assert progress.progress == 100.0
        assert progress.completed_at is not None

    @pytest.mark.asyncio
    async def test_fetch_lyrics_success(
        self, download_manager: DownloadService
    ) -> None:
        """Test fetching lyrics successfully."""
        mock_provider = AsyncMock()
        mock_provider.get_lyrics.return_value = "Test lyrics content"

        with patch("spotdl.providers.lyrics.genius.GeniusWebProvider", return_value=mock_provider):
            with patch("httpx.AsyncClient"):
                lyrics = await download_manager._fetch_lyrics("Test Song", "Test Artist")

        assert lyrics == "Test lyrics content"

    @pytest.mark.asyncio
    async def test_fetch_lyrics_provider_error(
        self, download_manager: DownloadService
    ) -> None:
        """Test fetching lyrics with provider error."""
        mock_provider = AsyncMock()
        mock_provider.get_lyrics.side_effect = Exception("Provider error")

        with patch("spotdl.providers.lyrics.genius.GeniusWebProvider", return_value=mock_provider):
            with patch("httpx.AsyncClient"):
                lyrics = await download_manager._fetch_lyrics("Test Song", "Test Artist")

        assert lyrics is None


class TestGetDownloadService:
    """Tests for get_download_service function."""

    def test_get_download_service_returns_instance(self) -> None:
        """Test get_download_service returns a DownloadService."""
        import spotdl.core.services.download as download_module

        download_module._download_manager = None

        manager = get_download_service()
        assert isinstance(manager, DownloadService)

    def test_get_download_service_singleton(self) -> None:
        """Test get_download_service returns same instance."""
        import spotdl.core.services.download as download_module

        download_module._download_manager = None

        manager1 = get_download_service()
        manager2 = get_download_service()
        assert manager1 is manager2


class TestCreateDownloadId:
    """Tests for create_download_id function."""

    def test_create_download_id_returns_string(self) -> None:
        """Test that create_download_id returns a string."""
        download_id = create_download_id()
        assert isinstance(download_id, str)

    def test_create_download_id_unique(self) -> None:
        """Test that create_download_id returns unique IDs."""
        id1 = create_download_id()
        id2 = create_download_id()
        assert id1 != id2

    def test_create_download_id_format(self) -> None:
        """Test that create_download_id returns valid UUID format."""
        import uuid

        download_id = create_download_id()
        # Should not raise ValueError
        uuid.UUID(download_id)
