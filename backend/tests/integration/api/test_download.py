"""Tests for download API endpoints."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from spotdl.core.services.download import DownloadProgress, DownloadStatus


@pytest.mark.asyncio
async def test_start_download_disabled(authenticated_client: AsyncClient):
    """Test starting a download when downloads are disabled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = False

        response = await authenticated_client.post(
            "/api/v1/download/start",
            json={
                "url": "https://www.youtube.com/watch?v=test123",
                "title": "Test Song",
                "artist": "Test Artist",
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_download_requires_url(authenticated_client: AsyncClient):
    """Test starting a download requires URL."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = True

        response = await authenticated_client.post(
            "/api/v1/download/start",
            json={
                "title": "Test Song",
                "artist": "Test Artist",
            },
        )

        assert response.status_code == 422  # Missing required field


@pytest.mark.asyncio
async def test_start_download_requires_title(authenticated_client: AsyncClient):
    """Test starting a download requires title."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = True

        response = await authenticated_client.post(
            "/api/v1/download/start",
            json={
                "url": "https://www.youtube.com/watch?v=test123",
                "artist": "Test Artist",
            },
        )

        assert response.status_code == 422  # Missing required field


@pytest.mark.asyncio
async def test_get_download_status_not_found(authenticated_client: AsyncClient):
    """Test getting status of non-existent download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=None)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get(
                "/api/v1/download/status/nonexistent-id"
            )

            assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_download_status_success(authenticated_client: AsyncClient):
    """Test getting status of an existing download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-123",
                status=DownloadStatus.DOWNLOADING,
                progress=0.5,
                speed="1.2 MB/s",
                eta="00:30",
                filename="test.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/status/test-123")

            assert response.status_code == 200
            data = response.json()
            assert data["download_id"] == "test-123"
            assert data["status"] == "downloading"
            assert data["progress"] == 0.5
            assert data["speed"] == "1.2 MB/s"


@pytest.mark.asyncio
async def test_get_download_status_completed(authenticated_client: AsyncClient):
    """Test getting status of a completed download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-456",
                status=DownloadStatus.COMPLETED,
                progress=1.0,
                speed=None,
                eta=None,
                filename="completed.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/status/test-456")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 1.0
            assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_list_downloads(authenticated_client: AsyncClient):
    """Test listing all downloads."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_downloads = [
                DownloadProgress(
                    download_id=f"test-{i}",
                    status=DownloadStatus.DOWNLOADING if i % 2 == 0 else DownloadStatus.COMPLETED,
                    progress=0.5 if i % 2 == 0 else 1.0,
                    speed="1.0 MB/s" if i % 2 == 0 else None,
                    eta="00:30" if i % 2 == 0 else None,
                    filename=f"file-{i}.mp3",
                    error=None,
                    created_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc) if i % 2 == 1 else None,
                )
                for i in range(5)
            ]

            mock_mgr = MagicMock()
            mock_mgr.get_all_downloads = MagicMock(return_value=mock_downloads)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/list")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 5
            assert len(data["downloads"]) == 5


@pytest.mark.asyncio
async def test_list_downloads_empty(authenticated_client: AsyncClient):
    """Test listing downloads when there are none."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_mgr = MagicMock()
            mock_mgr.get_all_downloads = MagicMock(return_value=[])
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/list")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["downloads"]) == 0


@pytest.mark.asyncio
async def test_get_download_file_not_found(authenticated_client: AsyncClient):
    """Test getting file for non-existent download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=None)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/file/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_download_file_not_completed(authenticated_client: AsyncClient):
    """Test getting file for download that's not completed."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-789",
                status=DownloadStatus.DOWNLOADING,
                progress=0.7,
                speed="1.5 MB/s",
                eta="00:15",
                filename="incomplete.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/file/test-789")

            assert response.status_code == 400
            assert "not ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_download_file_no_file_path(authenticated_client: AsyncClient):
    """Test getting file when file path doesn't exist."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-abc",
                status=DownloadStatus.COMPLETED,
                progress=1.0,
                speed=None,
                eta=None,
                filename="missing.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_mgr.get_file_path = MagicMock(return_value=None)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.get("/api/v1/download/file/test-abc")

            assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_download_not_found(authenticated_client: AsyncClient):
    """Test cancelling non-existent download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=None)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.post(
                "/api/v1/download/cancel/nonexistent"
            )

            assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_download_success(authenticated_client: AsyncClient):
    """Test successfully cancelling a download."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-cancel",
                status=DownloadStatus.DOWNLOADING,
                progress=0.3,
                speed="1.0 MB/s",
                eta="01:00",
                filename="cancel.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=None,
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_mgr.cancel_download = AsyncMock(return_value=True)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.post(
                "/api/v1/download/cancel/test-cancel"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
            assert data["download_id"] == "test-cancel"


@pytest.mark.asyncio
async def test_cancel_download_failed(authenticated_client: AsyncClient):
    """Test cancelling a download that can't be cancelled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        with patch("spotdl.api.v1.download.get_download_manager") as mock_manager:
            mock_settings.return_value.downloads_enabled = True

            mock_progress = DownloadProgress(
                download_id="test-fail",
                status=DownloadStatus.COMPLETED,
                progress=1.0,
                speed=None,
                eta=None,
                filename="complete.mp3",
                error=None,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )

            mock_mgr = MagicMock()
            mock_mgr.get_progress = MagicMock(return_value=mock_progress)
            mock_mgr.cancel_download = AsyncMock(return_value=False)
            mock_manager.return_value = mock_mgr

            response = await authenticated_client.post("/api/v1/download/cancel/test-fail")

            assert response.status_code == 400
            assert "Could not cancel" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_status_disabled(authenticated_client: AsyncClient):
    """Test accessing download status when downloads are disabled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = False

        response = await authenticated_client.get("/api/v1/download/status/test-id")

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_downloads_disabled(authenticated_client: AsyncClient):
    """Test listing downloads when feature is disabled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = False

        response = await authenticated_client.get("/api/v1/download/list")

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_download_file_disabled(authenticated_client: AsyncClient):
    """Test getting download file when feature is disabled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = False

        response = await authenticated_client.get("/api/v1/download/file/test-id")

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_cancel_download_disabled(authenticated_client: AsyncClient):
    """Test cancelling download when feature is disabled."""
    with patch("spotdl.api.v1.download.get_settings") as mock_settings:
        mock_settings.return_value.downloads_enabled = False

        response = await authenticated_client.post("/api/v1/download/cancel/test-id")

        assert response.status_code == 403
