"""Download API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from spotdl.core.services.download import (
    DownloadManager,
    DownloadProgress,
    DownloadRequest,
    DownloadStatus,
    create_download_id,
    get_download_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/download")


class StartDownloadRequest(BaseModel):
    """Request to start a download."""

    url: str
    title: str
    artist: str
    album: str | None = None
    cover_url: str | None = None
    duration: int | None = None
    output_format: str = "mp3"
    quality: str = "320"


class StartDownloadResponse(BaseModel):
    """Response for starting a download."""

    download_id: str
    status: str
    message: str


class DownloadProgressResponse(BaseModel):
    """Download progress response."""

    download_id: str
    status: str
    progress: float
    speed: str | None
    eta: str | None
    filename: str | None
    error: str | None
    created_at: str
    completed_at: str | None


class DownloadListResponse(BaseModel):
    """List of downloads response."""

    downloads: list[DownloadProgressResponse]
    total: int


def progress_to_response(progress: DownloadProgress) -> DownloadProgressResponse:
    """Convert DownloadProgress to response model."""
    return DownloadProgressResponse(
        download_id=progress.download_id,
        status=progress.status.value,
        progress=progress.progress,
        speed=progress.speed,
        eta=progress.eta,
        filename=progress.filename,
        error=progress.error,
        created_at=progress.created_at.isoformat(),
        completed_at=progress.completed_at.isoformat() if progress.completed_at else None,
    )


@router.post("/start")
async def start_download(request: StartDownloadRequest) -> StartDownloadResponse:
    """
    Start a new download.

    Takes a URL (typically YouTube/YouTube Music) and metadata,
    downloads the audio, embeds metadata, and makes it available for download.
    """
    manager = get_download_manager()

    # Create download request
    download_id = create_download_id()
    download_request = DownloadRequest(
        download_id=download_id,
        url=request.url,
        title=request.title,
        artist=request.artist,
        album=request.album,
        cover_url=request.cover_url,
        duration=request.duration,
        output_format=request.output_format,
        quality=request.quality,
    )

    # Start the download
    await manager.start_download(download_request)

    logger.info(f"Started download {download_id} for: {request.title} by {request.artist}")

    return StartDownloadResponse(
        download_id=download_id,
        status="started",
        message=f"Download started for {request.title}",
    )


@router.get("/status/{download_id}")
async def get_download_status(download_id: str) -> DownloadProgressResponse:
    """Get the status of a download."""
    manager = get_download_manager()
    progress = manager.get_progress(download_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Download not found")

    return progress_to_response(progress)


@router.get("/list")
async def list_downloads() -> DownloadListResponse:
    """List all downloads."""
    manager = get_download_manager()
    downloads = manager.get_all_downloads()

    return DownloadListResponse(
        downloads=[progress_to_response(d) for d in downloads],
        total=len(downloads),
    )


@router.get("/file/{download_id}")
async def get_download_file(download_id: str) -> FileResponse:
    """
    Get the downloaded file.

    Returns the audio file for a completed download.
    """
    manager = get_download_manager()
    progress = manager.get_progress(download_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Download not found")

    if progress.status != DownloadStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Download not ready. Status: {progress.status.value}",
        )

    file_path = manager.get_file_path(download_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=progress.filename or file_path.name,
        media_type="audio/mpeg",
    )


@router.post("/cancel/{download_id}")
async def cancel_download(download_id: str) -> dict[str, str]:
    """Cancel a download in progress."""
    manager = get_download_manager()

    if not manager.get_progress(download_id):
        raise HTTPException(status_code=404, detail="Download not found")

    success = await manager.cancel_download(download_id)

    if success:
        return {"status": "cancelled", "download_id": download_id}
    else:
        raise HTTPException(status_code=400, detail="Could not cancel download")
