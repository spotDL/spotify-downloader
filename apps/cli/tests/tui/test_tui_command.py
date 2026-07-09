"""Wiring + dispatch + end-to-end pilot for the real ``spotdl tui`` command (Task 11).

Three concerns, all offline (no real terminal, server, or network):

* **command wiring** — ``spotdl tui`` opens a ``SpotdlClient`` at the ``from_config``
  seam, builds a ``ViewModelFactory`` with the config-backed stores, runs
  ``SpotdlApp``, and closes the client cleanly on exit (both seams patched);
* **TTY dispatch** — a bare ``spotdl`` in a TTY launches the TUI, while a non-TTY
  keeps Typer's help (Plan 8 behaviour), and a bare query still sugars to download;
* **the pilot** — the real ``build_factory`` wiring drives ``SpotdlApp`` over a fake
  client through one flow that crosses every section: boot → search → open a track →
  vote → enqueue → watch the queue update → open settings → quit.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from spotdl_cli import __main__ as main_mod
from spotdl_cli.commands import tui as tui_cmd
from spotdl_cli.config import CliConfig
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.queue import QueueScreen
from spotdl_cli.tui.screens.settings import SettingsScreen
from spotdl_cli.tui.screens.track import TrackScreen
from spotdl_cli.tui.widgets.match_gauge import MatchGauge
from spotdl_cli.tui.widgets.queue_table import QueueTable
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import DataTable, Input
from typer.testing import CliRunner

from .fakes import (
    FakeSpotdlClient,
    make_batch,
    make_job,
    make_lyrics,
    make_match,
    make_track,
    ws_progress,
    ws_queued,
    ws_started,
)

runner = CliRunner()


# --- command wiring ----------------------------------------------------------


def test_tui_command_builds_factory_runs_app_and_closes_client(monkeypatch) -> None:
    """The command wires the real factory over the ``from_config`` seam, no stub."""
    fake = FakeSpotdlClient()
    state: dict[str, object] = {"closed": False, "factory": None}

    @asynccontextmanager
    async def fake_open(cfg, *, offline):
        try:
            yield fake
        finally:
            state["closed"] = True

    async def fake_run_app(factory, **kwargs):
        state["factory"] = factory

    monkeypatch.setattr(tui_cmd, "_open_client", fake_open)
    monkeypatch.setattr(tui_cmd, "_run_app", fake_run_app)

    result = runner.invoke(main_mod.app, ["tui"])

    assert result.exit_code == 0, result.output
    assert isinstance(state["factory"], ViewModelFactory)
    assert state["closed"] is True  # from_config's context manager tore the client down
    # not the Plan 8 placeholder: no "coming later" copy, the real app seam ran.
    assert "later release" not in result.output


def test_tui_command_offline_flag_reaches_from_config(monkeypatch) -> None:
    seen: dict[str, object] = {}

    @asynccontextmanager
    async def fake_open(cfg, *, offline):
        seen["offline"] = offline
        yield FakeSpotdlClient()

    async def fake_run_app(factory, **kwargs):
        return None

    monkeypatch.setattr(tui_cmd, "_open_client", fake_open)
    monkeypatch.setattr(tui_cmd, "_run_app", fake_run_app)

    result = runner.invoke(main_mod.app, ["tui", "--offline"])

    assert result.exit_code == 0, result.output
    assert seen["offline"] is True


# --- TTY dispatch ------------------------------------------------------------


class _FakeStdout:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_bare_spotdl_in_a_tty_launches_the_tui(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(main_mod, "app", lambda args: calls.append(list(args)))
    monkeypatch.setattr(main_mod.sys, "stdout", _FakeStdout(True))

    main_mod.main([])

    assert calls == [["tui"]]


def test_bare_spotdl_without_a_tty_shows_help(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(main_mod, "app", lambda args: calls.append(list(args)))
    monkeypatch.setattr(main_mod.sys, "stdout", _FakeStdout(False))

    main_mod.main([])

    assert calls == [[]]  # empty argv → Typer's no_args_is_help (Plan 8 behaviour)


def test_bare_query_still_sugars_to_download_in_a_tty(monkeypatch) -> None:
    """The TTY launch only fires for *no* arguments; a bare query still downloads."""
    calls: list[list[str]] = []
    monkeypatch.setattr(main_mod, "app", lambda args: calls.append(list(args)))
    monkeypatch.setattr(main_mod.sys, "stdout", _FakeStdout(True))

    main_mod.main(["https://open.spotify.com/track/x"])

    assert calls == [["download", "https://open.spotify.com/track/x"]]


# --- end-to-end pilot --------------------------------------------------------


async def test_end_to_end_pilot_crosses_every_section() -> None:
    track_id, match_id = uuid4(), uuid4()
    client = FakeSpotdlClient()  # default config: self_host, every feature on
    track = make_track(id=track_id, name="One More Time", artists=["Daft Punk"])
    client.search_results = [track]
    client.tracks[str(track_id)] = track
    client.matches_by_track[str(track_id)] = [
        make_match(id=match_id, provider="youtube", upvotes=4, downvotes=1)
    ]
    client.lyrics_by_track[str(track_id)] = [make_lyrics()]
    # A vote returns fresh tallies only (blank structural fields), like the façade.
    client.vote_match_result = make_match(
        id=match_id, provider="", url="", score=0.0, upvotes=10, downvotes=2, net_score=8
    )
    client.submit_download_result = make_batch(jobs=[make_job()])

    factory = tui_cmd.build_factory(client, CliConfig(), offline=False)
    app = SpotdlApp(factory)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_mode == "home"

        # 1) search
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("o", "n", "e", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        results = app.screen.query_one("#search-results", DataTable)
        assert results.row_count == 1
        assert client.called("search")

        # 2) open the track
        results.focus()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, TrackScreen)

        # 3) cast a vote — fresh tallies merge onto the gauge (up arrow votes up)
        gauge = app.screen.query_one(MatchGauge)
        gauge.focus()
        await pilot.press("up")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert client.called("vote_match")

        # 4) enqueue the track (d = Download)
        await pilot.press("d")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert client.called("submit_download")

        # 5) open the queue and watch a live frame land
        await pilot.press("2")
        await pilot.pause()
        assert isinstance(app.screen, QueueScreen)
        job, batch = uuid4(), uuid4()
        client.push_ws(ws_queued(job, batch, track_name="One More Time"))
        client.push_ws(ws_started(job, batch))
        client.push_ws(ws_progress(job, batch, phase="convert", percent=60))
        await pilot.pause()
        assert app.screen.query_one(QueueTable).row_count == 1

        # 6) open settings
        await pilot.press("4")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)

        # 7) quit
        await pilot.press("q")
