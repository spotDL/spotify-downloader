"""``spotdl url`` / ``save`` / ``meta`` — resolution + embedded-batch commands.

A fake :class:`SpotdlClient` (injected through ``_support.open_client``) records
the façade calls each command makes, so the routing (top-match URL for ``url``,
``generate_save_file`` for ``save``, ``overwrite`` mode for ``meta``) is asserted
without a live transport.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli.commands import _support
from spotdl_cli.views import BatchView, DownloadSubmit, EntityView, MatchView, TrackView
from typer.testing import CliRunner

runner = CliRunner()

BATCH_ID = "22222222-2222-2222-2222-222222222222"
TRACK_ID = "11111111-1111-1111-1111-111111111111"


def _match(url: str) -> MatchView:
    return MatchView(
        id="m1",
        status="auto",
        score=0.9,
        net_score=1,
        upvotes=1,
        downvotes=0,
        matcher_version="1.0",
        target_provider="youtube",
        target_id="yt1",
        target_url=url,
    )


def _track(track_id: str = TRACK_ID, name: str = "One More Time") -> TrackView:
    return TrackView(id=track_id, name=name, artists=["Daft Punk"], duration_ms=224_000)


class FakeClient:
    """Records façade calls; returns canned entities/matches/batches."""

    def __init__(
        self,
        *,
        entity: EntityView | None = None,
        matches: dict[str, list[MatchView]] | None = None,
        save_file: dict[str, object] | None = None,
        batch_counts: dict[str, int] | None = None,
    ) -> None:
        self._entity = entity
        self._matches = matches or {}
        self._save_file = save_file or {}
        self._batch_counts = batch_counts or {}
        self.submits: list[DownloadSubmit] = []
        self.fetched: list[UUID] = []

    async def resolve(self, query: str) -> EntityView:
        assert self._entity is not None
        return self._entity

    async def matches(self, track_id: UUID) -> list[MatchView]:
        return self._matches.get(str(track_id), [])

    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        self.submits.append(req)
        return self._batch(finalized=False)

    async def get_batch(self, batch_id: UUID) -> BatchView:
        return self._batch(finalized=True)

    async def fetch_save_file(self, batch_id: UUID) -> dict[str, object]:
        self.fetched.append(batch_id)
        return self._save_file

    def _batch(self, *, finalized: bool) -> BatchView:
        return BatchView(
            batch_id=BATCH_ID,
            kind="single",
            finalized=finalized,
            total_jobs=1,
            counts=self._batch_counts,
            jobs=[],
        )


@pytest.fixture
def install_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[object], None]]:
    def install(client: object) -> None:
        @asynccontextmanager
        async def _open(**_: object) -> AsyncIterator[object]:
            yield client

        monkeypatch.setattr(_support, "open_client", _open)

    yield install


# ---- url --------------------------------------------------------------------


def test_url_prints_top_target(install_client: Callable[[object], None]) -> None:
    entity = EntityView(type="track", track=_track())
    install_client(FakeClient(entity=entity, matches={TRACK_ID: [_match("https://yt/watch?v=1")]}))

    result = runner.invoke(app, ["url", "https://open.spotify.com/track/x"])

    assert result.exit_code == 0
    assert "https://yt/watch?v=1" in result.output


def test_url_warns_when_unmatched(install_client: Callable[[object], None]) -> None:
    entity = EntityView(type="track", track=_track())
    install_client(FakeClient(entity=entity, matches={}))

    result = runner.invoke(app, ["url", "https://open.spotify.com/track/x"])

    assert result.exit_code == 0
    assert "no audio match" in result.output


# ---- save -------------------------------------------------------------------


def test_save_writes_file(install_client: Callable[[object], None], tmp_path) -> None:
    client = FakeClient(save_file={"version": 2, "songs": [{"name": "t"}]})
    install_client(client)
    out = tmp_path / "list.spotdl"

    result = runner.invoke(
        app, ["save", "https://open.spotify.com/album/x", "--save-file", str(out)]
    )

    assert result.exit_code == 0
    assert client.submits[0].generate_save_file is True
    assert json.loads(out.read_text())["songs"][0]["name"] == "t"


def test_save_to_stdout(install_client: Callable[[object], None]) -> None:
    install_client(FakeClient(save_file={"version": 2, "songs": []}))

    result = runner.invoke(app, ["save", "spotify:album:x", "--save-file", "-"])

    assert result.exit_code == 0
    assert '"version": 2' in result.output


def test_save_requires_save_file(install_client: Callable[[object], None]) -> None:
    install_client(FakeClient(save_file={}))

    result = runner.invoke(app, ["save", "spotify:album:x"])

    assert result.exit_code == 2


# ---- meta -------------------------------------------------------------------


def test_meta_submits_metadata_retag(install_client: Callable[[object], None], tmp_path) -> None:
    client = FakeClient(batch_counts={"completed": 1})
    install_client(client)
    f1 = tmp_path / "Daft Punk - One More Time.mp3"
    f1.write_bytes(b"")

    result = runner.invoke(app, ["meta", str(f1)])

    assert result.exit_code == 0
    assert len(client.submits) == 1
    assert client.submits[0].overwrite == "metadata"
    assert client.submits[0].query == "Daft Punk - One More Time"


def test_meta_redownload_forces(install_client: Callable[[object], None], tmp_path) -> None:
    client = FakeClient(batch_counts={"completed": 1})
    install_client(client)
    f1 = tmp_path / "song.mp3"
    f1.write_bytes(b"")

    result = runner.invoke(app, ["meta", str(f1), "--redownload"])

    assert result.exit_code == 0
    assert client.submits[0].overwrite == "force"


def test_meta_failure_exits_nonzero(install_client: Callable[[object], None], tmp_path) -> None:
    client = FakeClient(batch_counts={"failed": 1})
    install_client(client)
    f1 = tmp_path / "song.mp3"
    f1.write_bytes(b"")

    result = runner.invoke(app, ["meta", str(f1)])

    assert result.exit_code == 1
