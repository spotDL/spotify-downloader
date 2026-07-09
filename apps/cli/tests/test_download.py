"""``spotdl download`` — option resolution + WS progress + failure collection.

Downloads always run against the embedded transport (a sibling track wires the
real ``from_config``), so these tests inject a fake ``SpotdlClient`` by patching
``download._open_client`` and drive a controlled WS frame stream. Pure option
resolution is tested directly.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli._generated.ws_models import WsMessage
from spotdl_cli.commands import download as dl
from spotdl_cli.errors import ExitCode
from spotdl_cli.views import BatchView, DownloadSubmit
from typer.testing import CliRunner

BATCH_ID = "22222222-2222-2222-2222-222222222222"
JOB1 = "33333333-3333-3333-3333-333333333333"
JOB2 = "44444444-4444-4444-4444-444444444444"


def _frame(**data: Any) -> WsMessage:
    return WsMessage.model_validate(data)


def _queued(job_id: str, name: str) -> WsMessage:
    return _frame(
        type="job_queued",
        batch_id=BATCH_ID,
        job_id=job_id,
        track_name=name,
        list_position=1,
        list_length=1,
    )


def _finished(job_id: str, *, skipped: bool = False) -> WsMessage:
    return _frame(
        type="job_finished",
        batch_id=BATCH_ID,
        job_id=job_id,
        output_path=f"/music/{job_id}.mp3",
        skip_reason=None,
        skipped=skipped,
        status="completed",
    )


def _failed(job_id: str, step: str, error: str) -> WsMessage:
    return _frame(type="job_failed", batch_id=BATCH_ID, job_id=job_id, step=step, error=error)


def _batch_finished(*, completed: int, failed: int, skipped: int = 0) -> WsMessage:
    return _frame(
        type="batch_finished",
        batch_id=BATCH_ID,
        completed=completed,
        failed=failed,
        skipped=skipped,
        cancelled=0,
        m3u_paths=[],
        save_file_path=None,
    )


class FakeClient:
    """A stand-in ``SpotdlClient`` with a scripted progress stream."""

    def __init__(self, frames: list[WsMessage], *, save_file: Any = None) -> None:
        self._frames = frames
        self.submitted: list[DownloadSubmit] = []
        self.save_file = save_file
        self.fetched: list[UUID] = []

    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        self.submitted.append(req)
        return BatchView(
            batch_id=BATCH_ID,
            kind="single",
            finalized=False,
            total_jobs=1,
            counts={},
            jobs=[],
        )

    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[WsMessage]]:
        async def _gen() -> AsyncIterator[WsMessage]:
            for frame in self._frames:
                yield frame

        yield _gen()

    async def fetch_save_file(self, batch_id: UUID) -> Any:
        self.fetched.append(batch_id)
        return self.save_file


@pytest.fixture
def patch_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _install(client: FakeClient) -> None:
        @asynccontextmanager
        async def _open(*, offline: bool, settings_env: dict[str, str]) -> AsyncIterator[Any]:
            yield client

        monkeypatch.setattr(dl, "_open_client", _open)

    return _install


runner = CliRunner()


def test_download_success_exits_ok(patch_client: Any) -> None:
    client = FakeClient(
        [
            _queued(JOB1, "One More Time"),
            _finished(JOB1),
            _batch_finished(completed=1, failed=0),
        ]
    )
    patch_client(client)
    result = runner.invoke(app, ["download", "https://open.spotify.com/track/abc"])
    assert result.exit_code == ExitCode.OK, result.output
    assert len(client.submitted) == 1
    assert client.submitted[0].query == "https://open.spotify.com/track/abc"
    assert "1 downloaded" in result.output


def test_job_failure_collected_and_exit_code(patch_client: Any) -> None:
    client = FakeClient(
        [
            _queued(JOB1, "Good Song"),
            _queued(JOB2, "Bad Song"),
            _finished(JOB1),
            _failed(JOB2, "download", "yt-dlp exploded"),
            _batch_finished(completed=1, failed=1),
        ]
    )
    patch_client(client)
    result = runner.invoke(app, ["download", "https://open.spotify.com/album/xyz"])
    assert result.exit_code == ExitCode.DOWNLOAD_FAILURES, result.output
    assert "Bad Song" in result.output
    assert "1 downloaded" in result.output


def test_save_errors_writes_details(patch_client: Any, tmp_path: Path) -> None:
    client = FakeClient(
        [
            _queued(JOB2, "Bad Song"),
            _failed(JOB2, "convert", "ffmpeg missing"),
            _batch_finished(completed=0, failed=1),
        ]
    )
    patch_client(client)
    errors_file = tmp_path / "errors.txt"
    result = runner.invoke(
        app, ["download", "https://open.spotify.com/track/bad", "--save-errors", str(errors_file)]
    )
    assert result.exit_code == ExitCode.DOWNLOAD_FAILURES, result.output
    body = errors_file.read_text(encoding="utf-8")
    assert "Bad Song" in body
    assert "convert" in body
    assert "ffmpeg missing" in body


def test_spotdl_file_argument_loads_and_submits(patch_client: Any, tmp_path: Path) -> None:
    v4 = [
        {
            "name": "One More Time",
            "artists": ["Daft Punk"],
            "artist": "Daft Punk",
            "duration": 320.0,
            "url": "https://open.spotify.com/track/omt",
            "download_url": "https://music.youtube.com/watch?v=abc",
        }
    ]
    spotdl_file = tmp_path / "playlist.spotdl"
    spotdl_file.write_text(json.dumps(v4), encoding="utf-8")

    client = FakeClient(
        [_queued(JOB1, "One More Time"), _finished(JOB1), _batch_finished(completed=1, failed=0)]
    )
    patch_client(client)
    result = runner.invoke(app, ["download", str(spotdl_file)])
    assert result.exit_code == ExitCode.OK, result.output
    assert len(client.submitted) == 1
    assert client.submitted[0].query == "https://open.spotify.com/track/omt"


async def test_write_save_file_merges_all_batches(tmp_path: Path) -> None:
    """``--save-file`` with multiple batches merges every batch's songs (no drop)."""
    from spotdl_server.downloads.savefile import SaveFileDownload, SaveFileSong, SaveFileV2

    b1 = UUID("22222222-2222-2222-2222-222222222222")
    b2 = UUID("55555555-5555-5555-5555-555555555555")

    def _song(name: str) -> SaveFileSong:
        return SaveFileSong(
            name=name,
            artists=["A"],
            duration_ms=1000,
            download=SaveFileDownload(
                output_format="mp3", bitrate="auto", output_template="t", status="completed"
            ),
        )

    saves = {
        b1: SaveFileV2(
            kind="single", name="first", created_at="2020-01-01T00:00:00+00:00", songs=[_song("A")]
        ),
        b2: SaveFileV2(
            kind="single", name="second", created_at="2021-01-01T00:00:00+00:00", songs=[_song("B")]
        ),
    }

    class _Client:
        def __init__(self) -> None:
            self.fetched: list[UUID] = []

        async def fetch_save_file(self, batch_id: UUID) -> Any:
            self.fetched.append(batch_id)
            return saves[batch_id]

    out = tmp_path / "out.spotdl"
    await dl._write_save_file(_Client(), {str(b1), str(b2)}, out)  # type: ignore[arg-type]

    data = json.loads(out.read_text(encoding="utf-8"))
    assert [s["name"] for s in data["songs"]] == ["A", "B"]  # both batches survive
    # Collection metadata comes from the first batch (sorted by id).
    assert data["name"] == "first"


def test_resolve_maps_flags_to_request_and_env() -> None:
    resolved = dl._resolve(
        ["https://x/track"],
        output="~/Music/{artists}/{title}.{output-ext}",
        output_format="flac",
        bitrate="320k",
        overwrite="force",
        restrict="strict",
        threads=8,
        save_file=Path("out.spotdl"),
        scan=True,
        skip_explicit=True,
    )
    submit = resolved.submits[0]
    assert submit.output_format == "flac"
    assert submit.bitrate == "320k"
    assert submit.overwrite == "force"
    assert submit.output_template == "{artists}/{title}.{output-ext}"
    assert submit.generate_save_file is True
    env = resolved.settings_env
    assert env["SPOTDL_LIBRARY_PATH"] == "~/Music"
    assert env["SPOTDL_DOWNLOAD_RESTRICT"] == "strict"
    assert env["SPOTDL_DOWNLOAD_CONCURRENCY"] == "8"
    assert env["SPOTDL_DOWNLOAD_SCAN_EXISTING"] == "true"
    assert env["SPOTDL_DOWNLOAD_SKIP_EXPLICIT"] == "true"


def test_split_output_template() -> None:
    assert dl.split_output_template("~/Music/{artists}/{title}.{output-ext}") == (
        "~/Music",
        "{artists}/{title}.{output-ext}",
    )
    assert dl.split_output_template("{title}.{output-ext}") == (None, "{title}.{output-ext}")
    assert dl.split_output_template("/abs/dir/{title}.mp3") == ("/abs/dir", "{title}.mp3")


def test_transport_error_renders_clean_no_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ReadTimeout wrapped in a TaskGroup ExceptionGroup must render as one
    line and exit TRANSPORT — never dump a raw traceback (live-download bug)."""
    import httpx

    @asynccontextmanager
    async def _boom(*, offline: bool, settings_env: dict[str, str]) -> AsyncIterator[Any]:
        class _C:
            async def submit_download(self, *a: Any, **k: Any) -> Any:
                # The real crash: submit's synchronous server-side resolve outran
                # the client read timeout, surfacing inside a TaskGroup.
                raise BaseExceptionGroup("unhandled errors in a TaskGroup", [httpx.ReadTimeout("")])

            @asynccontextmanager
            async def progress(self, *a: Any, **k: Any) -> AsyncIterator[Any]:
                async def _empty() -> AsyncIterator[Any]:
                    return
                    yield  # pragma: no cover

                yield _empty()

        yield _C()

    monkeypatch.setattr(dl, "_open_client", _boom)
    result = runner.invoke(app, ["download", "https://open.spotify.com/track/x"])
    assert result.exit_code == int(ExitCode.TRANSPORT)
    assert "Traceback" not in result.output
    assert "download failed" in result.output
    assert "ReadTimeout" in result.output
