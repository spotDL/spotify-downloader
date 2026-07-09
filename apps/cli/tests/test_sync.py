"""``spotdl sync`` — refresh a ``.spotdl`` v2 file, download new, prune removed.

Uses a fake client (patched onto ``download._open_client``, which ``sync``
reuses) whose ``fetch_save_file`` returns the "current source" tracklist; the
prune/rewrite/lrc logic runs against a real tmp filesystem.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli._generated.ws_models import WsMessage
from spotdl_cli.commands import download as dl
from spotdl_cli.commands import sync as sync_cmd
from spotdl_cli.errors import ExitCode
from spotdl_cli.savefile import dump_save_file, load_save_file
from spotdl_cli.views import BatchView, DownloadSubmit
from spotdl_server.downloads.savefile import SaveFileDownload, SaveFileSong, SaveFileV2
from typer.testing import CliRunner

BATCH_ID = "22222222-2222-2222-2222-222222222222"
JOB1 = "33333333-3333-3333-3333-333333333333"
SOURCE = "https://open.spotify.com/playlist/xyz"

runner = CliRunner()


def _frame(**data: Any) -> WsMessage:
    return WsMessage.model_validate(data)


def _success_frames() -> list[WsMessage]:
    return [
        _frame(
            type="job_queued",
            batch_id=BATCH_ID,
            job_id=JOB1,
            track_name="A",
            list_position=1,
            list_length=1,
        ),
        _frame(
            type="job_finished",
            batch_id=BATCH_ID,
            job_id=JOB1,
            output_path="/music/a.mp3",
            skip_reason=None,
            skipped=False,
            status="completed",
        ),
        _frame(
            type="batch_finished",
            batch_id=BATCH_ID,
            completed=1,
            failed=0,
            skipped=0,
            cancelled=0,
            m3u_paths=[],
            save_file_path=None,
        ),
    ]


def _song(name: str, url: str, output_path: str | None) -> SaveFileSong:
    return SaveFileSong(
        name=name,
        artists=["X"],
        artist="X",
        duration_ms=1000,
        track_url=url,
        download=SaveFileDownload(
            output_format="mp3",
            bitrate="auto",
            output_template="{title}.{output-ext}",
            output_path=output_path,
            status="completed",
        ),
    )


def _save(songs: list[SaveFileSong], *, source: str | None = None) -> SaveFileV2:
    return SaveFileV2(
        version=2,
        kind="playlist",
        name="Mix",
        source=source,
        created_at="2020-01-01T00:00:00",
        matcher_version=None,
        songs=songs,
    )


class SyncFakeClient:
    def __init__(self, new_save: SaveFileV2) -> None:
        self.new_save = new_save
        self.submitted: list[DownloadSubmit] = []

    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        self.submitted.append(req)
        return BatchView(
            batch_id=BATCH_ID, kind="playlist", finalized=False, total_jobs=1, counts={}, jobs=[]
        )

    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[WsMessage]]:
        async def _gen() -> AsyncIterator[WsMessage]:
            for frame in _success_frames():
                yield frame

        yield _gen()

    async def fetch_save_file(self, batch_id: Any) -> SaveFileV2:
        return self.new_save


@pytest.fixture
def patch_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _install(client: SyncFakeClient) -> None:
        @asynccontextmanager
        async def _open(*, offline: bool, settings_env: dict[str, str]) -> AsyncIterator[Any]:
            yield client

        monkeypatch.setattr(dl, "_open_client", _open)

    return _install


def test_sync_url_writes_save_file_and_downloads(patch_client: Any, tmp_path: Path) -> None:
    new = _save(
        [_song("A", "sp:a", "/music/a.mp3"), _song("B", "sp:b", "/music/b.mp3")], source=SOURCE
    )
    client = SyncFakeClient(new)
    patch_client(client)
    out = tmp_path / "mix.spotdl"

    result = runner.invoke(app, ["sync", SOURCE, "--save-file", str(out)])
    assert result.exit_code == ExitCode.OK, result.output
    assert client.submitted[0].query == SOURCE
    reloaded = load_save_file(out)
    assert [s.name for s in reloaded.songs] == ["A", "B"]


def test_sync_prunes_removed_track(patch_client: Any, tmp_path: Path) -> None:
    file_a = tmp_path / "a.mp3"
    file_b = tmp_path / "b.mp3"
    file_a.write_text("A", encoding="utf-8")
    file_b.write_text("B", encoding="utf-8")
    old = _save([_song("A", "sp:a", str(file_a)), _song("B", "sp:b", str(file_b))], source=SOURCE)
    spotdl_file = tmp_path / "mix.spotdl"
    spotdl_file.write_text(dump_save_file(old), encoding="utf-8")

    # The source now only has track A.
    patch_client(SyncFakeClient(_save([_song("A", "sp:a", str(file_a))], source=SOURCE)))
    result = runner.invoke(app, ["sync", str(spotdl_file)])
    assert result.exit_code == ExitCode.OK, result.output
    assert file_a.exists()
    assert not file_b.exists()  # pruned
    assert [s.name for s in load_save_file(spotdl_file).songs] == ["A"]


def test_sync_no_delete_keeps_removed_track(patch_client: Any, tmp_path: Path) -> None:
    file_a = tmp_path / "a.mp3"
    file_b = tmp_path / "b.mp3"
    file_a.write_text("A", encoding="utf-8")
    file_b.write_text("B", encoding="utf-8")
    old = _save([_song("A", "sp:a", str(file_a)), _song("B", "sp:b", str(file_b))], source=SOURCE)
    spotdl_file = tmp_path / "mix.spotdl"
    spotdl_file.write_text(dump_save_file(old), encoding="utf-8")

    patch_client(SyncFakeClient(_save([_song("A", "sp:a", str(file_a))], source=SOURCE)))
    result = runner.invoke(app, ["sync", str(spotdl_file), "--no-delete"])
    assert result.exit_code == ExitCode.OK, result.output
    assert file_b.exists()  # kept


def test_sync_remove_lrc_deletes_orphaned_lrc(patch_client: Any, tmp_path: Path) -> None:
    file_b = tmp_path / "b.mp3"
    lrc_b = tmp_path / "b.lrc"
    file_b.write_text("B", encoding="utf-8")
    lrc_b.write_text("lyrics", encoding="utf-8")
    old = _save([_song("B", "sp:b", str(file_b))], source=SOURCE)
    spotdl_file = tmp_path / "mix.spotdl"
    spotdl_file.write_text(dump_save_file(old), encoding="utf-8")

    patch_client(SyncFakeClient(_save([_song("A", "sp:a", "/music/a.mp3")], source=SOURCE)))
    result = runner.invoke(app, ["sync", str(spotdl_file), "--remove-lrc"])
    assert result.exit_code == ExitCode.OK, result.output
    assert not file_b.exists()
    assert not lrc_b.exists()


def test_sync_migrates_v4_in_place_with_notice(patch_client: Any, tmp_path: Path) -> None:
    v4 = tmp_path / "old.spotdl"
    v4.write_text(
        '[{"name": "A", "artists": ["X"], "duration": 10.0, '
        '"url": "sp:a", "download_url": "https://music.youtube.com/watch?v=a"}]',
        encoding="utf-8",
    )
    patch_client(SyncFakeClient(_save([_song("A", "sp:a", "/music/a.mp3")], source=None)))
    result = runner.invoke(app, ["sync", str(v4)])
    assert result.exit_code == ExitCode.OK, result.output
    assert "migrated" in result.output
    # The file is now v2 (a JSON object, not a bare array).
    assert v4.read_text(encoding="utf-8").lstrip().startswith("{")
    assert not sync_cmd.peek_is_v4(v4)


def test_sync_url_without_save_file_is_usage_error(patch_client: Any) -> None:
    patch_client(SyncFakeClient(_save([])))
    result = runner.invoke(app, ["sync", SOURCE])
    assert result.exit_code == ExitCode.USAGE
