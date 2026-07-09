"""Task 2 — download API request/response models + WS message union (CONTRACT 3/4).

Every field here is fixed by the OpenAPI + WS-protocol contracts (Plan 8 codegen
depends on it). These tests pin the request defaults, the discriminated-union
parsing (including ``hello``), the protocol-version constant, and that the ``*Out``
models serialize their status as the ``DownloadStatus`` value.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError
from spotdl_core.download import OverwriteMode
from spotdl_server.api.schemas import (
    WS_PROTOCOL_VERSION,
    DownloadBatchOut,
    DownloadJobOut,
    DownloadSubmitRequest,
    WsBatchFinished,
    WsHello,
    WsJobCancelled,
    WsJobFailed,
    WsJobFinished,
    WsJobQueued,
    WsJobStarted,
    WsMessage,
    WsProgress,
)
from spotdl_server.db.enums import BatchKind, DownloadStatus


# --------------------------------------------------------------------------- #
# CONTRACT 4 — request/response
# --------------------------------------------------------------------------- #
def test_submit_request_defaults() -> None:
    req = DownloadSubmitRequest(query="https://open.spotify.com/track/x")
    assert req.output_format is None
    assert req.bitrate is None
    assert req.output_template is None
    assert req.overwrite is None
    assert req.embed_lyrics is True
    assert req.generate_lrc is False
    assert req.sponsor_block is False
    assert req.generate_m3u is False
    assert req.m3u_template is None
    assert req.generate_save_file is False
    assert req.update_archive is False


def test_submit_request_roundtrip() -> None:
    req = DownloadSubmitRequest(
        query="q", overwrite=OverwriteMode.FORCE, embed_lyrics=False, generate_m3u=True
    )
    again = DownloadSubmitRequest.model_validate_json(req.model_dump_json())
    assert again == req
    assert again.overwrite is OverwriteMode.FORCE


def test_job_out_serializes_status_value() -> None:
    from datetime import UTC, datetime

    job = DownloadJobOut(
        id=uuid4(),
        batch_id=None,
        status=DownloadStatus.COMPLETED,
        track_id=None,
        track_name="X",
        artists=["A"],
        output_format="mp3",
        bitrate="auto",
        output_template="t",
        output_path=None,
        progress=1.0,
        skip_reason=None,
        error_step=None,
        error_message=None,
        list_position=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )
    dumped = job.model_dump(mode="json")
    assert dumped["status"] == "completed"


def test_batch_out_serializes_kind_value() -> None:
    batch = DownloadBatchOut(
        batch_id=uuid4(),
        kind=BatchKind.PLAYLIST,
        name="P",
        total_jobs=3,
        counts={"queued": 1, "running": 0, "completed": 2, "failed": 0, "cancelled": 0},
        finalized=False,
        jobs=[],
    )
    dumped = batch.model_dump(mode="json")
    assert dumped["kind"] == "playlist"


# --------------------------------------------------------------------------- #
# CONTRACT 3 — WS message union
# --------------------------------------------------------------------------- #
def test_ws_protocol_version_and_hello() -> None:
    assert WS_PROTOCOL_VERSION == 1
    assert WsHello().protocol_version == WS_PROTOCOL_VERSION
    assert WsHello().type == "hello"


_ADAPTER: TypeAdapter[WsMessage] = TypeAdapter(WsMessage)  # type: ignore[valid-type]


@pytest.mark.parametrize(
    ("payload", "cls"),
    [
        ({"type": "hello", "protocol_version": 1}, WsHello),
        (
            {
                "type": "job_queued",
                "job_id": str(uuid4()),
                "batch_id": None,
                "track_name": "T",
                "list_position": 1,
                "list_length": 3,
            },
            WsJobQueued,
        ),
        ({"type": "job_started", "job_id": str(uuid4()), "batch_id": None}, WsJobStarted),
        (
            {
                "type": "progress",
                "job_id": str(uuid4()),
                "batch_id": None,
                "phase": "fetch",
                "percent": 42,
                "overall": 0.3,
            },
            WsProgress,
        ),
        (
            {
                "type": "job_finished",
                "job_id": str(uuid4()),
                "batch_id": None,
                "status": "completed",
                "skipped": False,
                "skip_reason": None,
                "output_path": "/x.mp3",
            },
            WsJobFinished,
        ),
        (
            {
                "type": "job_failed",
                "job_id": str(uuid4()),
                "batch_id": None,
                "step": "convert",
                "error": "boom",
            },
            WsJobFailed,
        ),
        ({"type": "job_cancelled", "job_id": str(uuid4()), "batch_id": None}, WsJobCancelled),
        (
            {
                "type": "batch_finished",
                "batch_id": str(uuid4()),
                "completed": 2,
                "failed": 0,
                "skipped": 1,
                "cancelled": 0,
                "m3u_paths": ["/p.m3u8"],
                "save_file_path": None,
            },
            WsBatchFinished,
        ),
    ],
)
def test_ws_message_union_dispatch(payload: dict, cls: type) -> None:  # type: ignore[type-arg]
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, cls)


def test_ws_message_union_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python({"type": "nope", "job_id": str(uuid4())})
