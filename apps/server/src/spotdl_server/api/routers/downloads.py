"""``/api/v1/downloads`` — submit / list / cancel / file / batch / save-file.

The HTTP surface for the Plan 7 download system (CONTRACT 4 + file semantics
CONTRACT 6). A thin shell: every route delegates to the injected
:class:`~spotdl_server.services.downloads.DownloadQueueService` (resolve/expand/
read), the :class:`~spotdl_server.downloads.worker.DownloadWorkerPool` (enqueue/
cancel) and the :class:`~spotdl_server.api.progress_hub.ProgressHub` (queue-event
fan-out). No ORM import, no business logic — orchestration lives in the service /
pool. Mounted only in selfhost/embedded (hosted never mounts it — mode gating at
``create_app``); every route sits behind ``require_download_access`` (the mode/
auth matrix, spec §4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse

from spotdl_server.api.deps import (
    get_download_hub,
    get_download_pool,
    get_download_queue_service,
    get_settings,
    require_download_access,
)
from spotdl_server.api.schemas import (
    DownloadBatchOut,
    DownloadJobOut,
    DownloadListResponse,
    DownloadSubmitRequest,
    DownloadSubmitResponse,
    WsJobQueued,
)
from spotdl_server.db.enums import DownloadStatus
from spotdl_server.downloads.savefile import dump_save_file
from spotdl_server.services.downloads import DownloadQueueService
from spotdl_server.services.errors import DownloadConflict, NotFoundError
from spotdl_server.settings import Settings

router = APIRouter(prefix="/api/v1", tags=["downloads"])

_MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
}


def _content_disposition(name: str) -> str:
    """An ``attachment`` disposition with an RFC 5987 UTF-8 filename."""
    return f"attachment; filename*=UTF-8''{quote(name)}"


@router.post(
    "/downloads",
    response_model=DownloadSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_download(
    req: DownloadSubmitRequest,
    service: DownloadQueueService = Depends(get_download_queue_service),
    pool: Any = Depends(get_download_pool),
    hub: Any = Depends(get_download_hub),
    _auth: Any = Depends(require_download_access),
) -> DownloadSubmitResponse:
    """Resolve + expand a submission into a queued batch, then enqueue + announce.

    ``NoMatchFound`` (track with no viable match) → 404; ``UnsupportedBatchEntity``
    (e.g. an artist url) → 400 — both via the global handlers. The pool receives
    the ids and ``job_queued`` frames go out only after the service committed.
    """
    batch, job_ids = await service.submit(req)
    await pool.enqueue(job_ids)
    for job in batch.jobs:
        await hub.broadcast(
            WsJobQueued(
                job_id=job.id,
                batch_id=job.batch_id,
                track_name=job.track_name,
                list_position=job.list_position,
                list_length=batch.total_jobs,
            )
        )
    return DownloadSubmitResponse(batch=batch)


@router.get("/downloads", response_model=DownloadListResponse)
async def list_downloads(
    status: DownloadStatus | None = None,
    batch_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    service: DownloadQueueService = Depends(get_download_queue_service),
    _auth: Any = Depends(require_download_access),
) -> DownloadListResponse:
    """A newest-first page of jobs with optional ``status`` / ``batch_id`` filters."""
    return await service.list_jobs(status=status, batch_id=batch_id, limit=limit, offset=offset)


@router.get("/downloads/batches/{batch_id}", response_model=DownloadBatchOut)
async def get_batch(
    batch_id: UUID,
    service: DownloadQueueService = Depends(get_download_queue_service),
    _auth: Any = Depends(require_download_access),
) -> DownloadBatchOut:
    """The batch's per-status tally + job listing (404 if unknown)."""
    return await service.get_batch(batch_id)


@router.get("/downloads/batches/{batch_id}/save-file")
async def get_batch_save_file(
    batch_id: UUID,
    service: DownloadQueueService = Depends(get_download_queue_service),
    _auth: Any = Depends(require_download_access),
) -> Response:
    """Serve the batch's ``.spotdl`` v2 JSON as an attachment (CONTRACT 7)."""
    model = await service.build_batch_save_file(batch_id)
    filename = f"{model.name or 'download'}.spotdl"
    return Response(
        content=dump_save_file(model),
        media_type="application/json",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/downloads/{job_id}", response_model=DownloadJobOut)
async def get_download(
    job_id: UUID,
    service: DownloadQueueService = Depends(get_download_queue_service),
    _auth: Any = Depends(require_download_access),
) -> DownloadJobOut:
    """One job (the WS-less polling fallback); 404 if unknown."""
    return await service.get_job(job_id)


@router.delete("/downloads/{job_id}", response_model=DownloadJobOut)
async def cancel_download(
    job_id: UUID,
    service: DownloadQueueService = Depends(get_download_queue_service),
    pool: Any = Depends(get_download_pool),
    _auth: Any = Depends(require_download_access),
) -> DownloadJobOut:
    """Cancel a queued/running job; 409 if it is already terminal, 404 if unknown."""
    cancelled = await pool.request_cancel(job_id)
    job = await service.get_job(job_id)  # 404 if the id is unknown
    if not cancelled:
        raise DownloadConflict("already_terminal")
    return job


@router.get("/downloads/{job_id}/file")
async def download_file(
    job_id: UUID,
    service: DownloadQueueService = Depends(get_download_queue_service),
    settings: Settings = Depends(get_settings),
    _auth: Any = Depends(require_download_access),
) -> Response:
    """Deliver a completed job's audio file (CONTRACT 6).

    409 unless the job is a completed *real* download with an ``output_path``; a
    path outside the library root or a missing file → 404 (never leaked). Serves
    via Starlette ``FileResponse`` by default, or an ``X-Accel-Redirect`` internal
    redirect when ``download_x_accel_prefix`` delegates streaming to a proxy.
    """
    job = await service.get_job(job_id)  # 404 if unknown
    is_real_completion = (
        job.status is DownloadStatus.COMPLETED and job.skip_reason is None and bool(job.output_path)
    )
    if not is_real_completion or job.output_path is None:
        raise DownloadConflict("not_ready")

    root = settings.effective_library_path().resolve()
    resolved = Path(job.output_path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise NotFoundError(entity_type="download_file", entity_id=job_id)

    media_type = _MEDIA_TYPES.get(resolved.suffix.lower(), "application/octet-stream")
    disposition = _content_disposition(resolved.name)
    if settings.download_x_accel_prefix:
        relative = resolved.relative_to(root).as_posix()
        accel = f"{settings.download_x_accel_prefix.rstrip('/')}/{relative}"
        return Response(
            media_type=media_type,
            headers={"X-Accel-Redirect": accel, "Content-Disposition": disposition},
        )
    return FileResponse(
        resolved,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )
