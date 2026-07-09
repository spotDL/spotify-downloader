"""Flow 1 (redesign §5.1): offline search → download → queue completes → library.

Drives the real ``SpotdlApp`` over :class:`FakeSpotdlClient` end to end, entirely
offline: an embedded-mode session searches, opens a track, enqueues a download, watches
the queue job run to completion over the fake WS source, then opens the library and
sees the finished file. The search step goes through the existing home-screen APIs
(``#search-input`` + results table) — this flow owns the download→queue→library legs.
"""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.library import LibraryScreen
from spotdl_cli.tui.screens.queue import QueueScreen
from spotdl_cli.tui.screens.track import TrackScreen
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import DataTable, Input, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import (
    FakeSpotdlClient,
    make_batch,
    make_config,
    make_download_page,
    make_features,
    make_job,
    make_lyrics,
    make_match,
    make_track,
    ws_finished,
    ws_queued,
    ws_started,
)

_ORIGIN = "https://api.example.test"


def _factory(client: FakeSpotdlClient) -> ViewModelFactory:
    return ViewModelFactory(
        client,
        FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label="offline · embedded",
    )


async def test_offline_search_download_queue_library_flow() -> None:
    track_id, batch = uuid4(), uuid4()
    config = make_config(mode="embedded", features=make_features(downloads=True, library=True))
    client = FakeSpotdlClient(config=config, download_config=config)
    track = make_track(id=track_id, name="Harder Better", artists=["Daft Punk"])
    client.search_results = [track]
    client.tracks[str(track_id)] = track
    client.matches_by_track[str(track_id)] = [make_match(id=uuid4())]
    client.lyrics_by_track[str(track_id)] = [make_lyrics()]
    client.submit_download_result = make_batch(batch_id=batch, jobs=[make_job(batch_id=batch)])
    client.download_page = make_download_page(jobs=[])  # empty until the job finishes

    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()

        # 1) search (via the existing home screen) and open the track.
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press(*"harder", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        results = app.screen.query_one("#search-results", DataTable)
        assert results.row_count == 1
        results.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TrackScreen)

        # 2) enqueue the download.
        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert client.called("submit_download")

        # 3) open the queue and run the job to completion over the fake WS.
        await pilot.press("2")
        await pilot.pause()
        assert isinstance(app.screen, QueueScreen)
        job = uuid4()
        client.push_ws(ws_queued(job, batch, track_name="Harder Better"))
        client.push_ws(ws_started(job, batch))
        client.push_ws(ws_finished(job, batch, output_path="/music/harder.mp3"))
        await pilot.pause()
        summary = str(app.screen.query_one("#queue-summary", Static).render())
        assert "completed 1" in summary

        # 4) the finished file now lists in the library.
        client.download_page = make_download_page(
            jobs=[make_job(status="completed", batch_id=batch, output_path="/music/harder.mp3")]
        )
        await pilot.press("3")
        await pilot.pause()
        assert isinstance(app.screen, LibraryScreen)
        files = app.screen.query_one("#library-files", DataTable)
        assert files.get_row_at(0)[0] == "/music/harder.mp3"
