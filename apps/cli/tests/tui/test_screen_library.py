"""Pilot tests for the library section (Plan 9 fable fix).

Runs headless via ``App.run_test``. The contract: the library section is reachable
when ``config.features.library`` is on (CONTRACT F), renders the completed downloads
grouped by batch with each batch's save-file URL and each track's output path, and is
hidden when the feature is off.
"""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.library import LibraryScreen
from spotdl_cli.viewmodels.factory import ViewModelFactory
from textual.widgets import DataTable, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_config, make_download_page, make_features, make_job

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(client: FakeSpotdlClient) -> ViewModelFactory:
    return ViewModelFactory(
        client,
        FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


async def test_library_section_lists_completed_downloads() -> None:
    client = FakeSpotdlClient()
    batch = uuid4()
    client.download_page = make_download_page(
        jobs=[
            make_job(status="completed", batch_id=batch, output_path="/music/one.mp3"),
            make_job(status="completed", batch_id=batch, output_path="/music/two.mp3"),
        ]
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")
        assert app.current_mode == "library"
        assert isinstance(app.screen, LibraryScreen)
        await pilot.pause()
        table = app.screen.query_one(DataTable)
        assert table.row_count == 2
        headings = " ".join(
            str(node.render()) for node in app.screen.query(".library-batch-heading")
        )
        assert f"/api/v1/downloads/batches/{batch}/save-file" in headings
        # the completed job requested the completed-only page
        method, _, kwargs = next(c for c in reversed(client.calls) if c[0] == "list_downloads")
        assert kwargs["status"] == "completed"


async def test_library_empty_state() -> None:
    client = FakeSpotdlClient()
    client.download_page = make_download_page(jobs=[])
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        body = " ".join(str(node.render()) for node in app.screen.query(Static))
        assert "No downloads yet" in body


async def test_library_batch_list_and_save_file_action() -> None:
    client = FakeSpotdlClient()
    batch = uuid4()
    client.download_page = make_download_page(
        jobs=[make_job(status="completed", batch_id=batch, output_path="/music/one.mp3")]
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        from textual.widgets import ListView

        batches = app.screen.query_one("#library-batches", ListView)
        assert len(batches.children) == 1  # one batch in the left list
        files = app.screen.query_one("#library-files", DataTable)
        assert files.get_row_at(0)[0] == "/music/one.mp3"  # file path shown
        await pilot.press("s")  # echo the batch save-file path
        await pilot.pause()
        assert any(
            f"/api/v1/downloads/batches/{batch}/save-file" in n.message for n in app._notifications
        )


async def test_library_batch_list_shows_real_name_not_id() -> None:
    """The batch list labels each batch by its name/kind, not a raw id (metadata gap fix)."""
    from textual.widgets import Label, ListView

    client = FakeSpotdlClient()
    batch = uuid4()
    client.download_page = make_download_page(
        jobs=[
            make_job(
                status="completed",
                batch_id=batch,
                batch_name="Random Access Memories",
                batch_kind="album",
                output_path="/music/one.mp3",
            )
        ]
    )
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        labels = " ".join(
            str(node.render())
            for node in app.screen.query_one("#library-batches", ListView).query(Label)
        )
        assert "Random Access Memories" in labels
        assert "Album" in labels  # kind-prefixed
        assert batch.hex[:8] not in labels  # not the raw id fallback


async def test_library_section_hidden_when_feature_off() -> None:
    client = FakeSpotdlClient(config=make_config(features=make_features(library=False)))
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")  # gated off — no-op
        assert app.current_mode == "home"
