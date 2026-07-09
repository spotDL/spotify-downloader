"""``LibraryViewModel`` — completed downloads grouped by batch (CONTRACT A)."""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.library import LibraryViewModel

from .fakes import FakeSpotdlClient, make_download_page, make_job

ORIGIN = "https://api.example.test"


def _vm(client: FakeSpotdlClient) -> LibraryViewModel:
    return LibraryViewModel(client, server_origin=ORIGIN)


async def test_groups_completed_jobs_by_batch_with_save_file_urls() -> None:
    client = FakeSpotdlClient()
    batch_a, batch_b = uuid4(), uuid4()
    client.download_page = make_download_page(
        jobs=[
            make_job(status="completed", batch_id=batch_a, output_path="/music/a1.mp3"),
            make_job(status="completed", batch_id=batch_a, output_path="/music/a2.mp3"),
            make_job(status="completed", batch_id=batch_b, output_path="/music/b1.mp3"),
        ]
    )
    result = await _vm(client).load()

    assert result.state is LoadState.READY
    assert result.data is not None
    groups = result.data
    assert [len(g.tracks) for g in groups] == [2, 1]
    assert groups[0].batch_id == batch_a
    assert groups[0].save_file_url == (f"{ORIGIN}/api/v1/downloads/batches/{batch_a}/save-file")
    assert groups[0].tracks[0].output_path == "/music/a1.mp3"
    assert groups[1].batch_id == batch_b


async def test_load_requests_only_completed_downloads() -> None:
    client = FakeSpotdlClient()
    await _vm(client).load()

    method, _, kwargs = client.calls[-1]
    assert method == "list_downloads"
    assert kwargs["status"] == "completed"


async def test_skipped_job_keeps_its_reason_and_no_path() -> None:
    client = FakeSpotdlClient()
    batch = uuid4()
    client.download_page = make_download_page(
        jobs=[make_job(status="completed", batch_id=batch, skip_reason="already exists")]
    )
    result = await _vm(client).load()

    assert result.data is not None
    track = result.data[0].tracks[0]
    assert track.output_path is None
    assert track.skip_reason == "already exists"


async def test_unbatched_job_has_no_save_file_url() -> None:
    client = FakeSpotdlClient()
    client.download_page = make_download_page(
        jobs=[make_job(status="completed", batch_id=None, output_path="/music/loose.mp3")]
    )
    result = await _vm(client).load()

    assert result.data is not None
    assert result.data[0].batch_id is None
    assert result.data[0].save_file_url is None


async def test_error_is_surfaced() -> None:
    client = FakeSpotdlClient()
    client.errors["list_downloads"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    result = await _vm(client).load()

    assert result.state is LoadState.ERROR
    assert result.error is not None
