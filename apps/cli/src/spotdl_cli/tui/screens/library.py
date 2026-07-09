"""``LibraryScreen`` — completed downloads grouped by batch (CONTRACT C/F).

The library section (gated on ``SessionSnapshot.library``): it loads the completed
downloads through :class:`~spotdl_cli.viewmodels.library.LibraryViewModel` and renders
one block per submission batch — the batch's ``.spotdl`` save-file URL over a table of
its tracks (title, artists, local output path). Web parity with
``apps/web/src/routes/library.tsx``; all grouping lives in the view-model, so the
screen only paints.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import LibraryBatch

_COLUMNS = ("Title", "Artists", "File")


class LibraryScreen(SpotdlScreen):
    """Completed downloads, grouped by batch, with per-batch save-file links."""

    def __init__(self) -> None:
        super().__init__(name="library")

    def compose_content(self) -> ComposeResult:
        # Body is filled after the async load resolves in ``on_mount``.
        yield VerticalScroll(id="library-body")

    def on_mount(self) -> None:
        super().on_mount()
        self.run_worker(self._load(), exclusive=True)

    async def _load(self) -> None:
        result = await self.vm_factory.library().load()
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        body = self.query_one("#library-body", VerticalScroll)
        if not result.data:
            await body.mount(Static("Nothing downloaded yet.", classes="placeholder"))
            return
        for batch in result.data:
            await self._mount_batch(body, batch)

    async def _mount_batch(self, body: VerticalScroll, batch: LibraryBatch) -> None:
        heading = f"{len(batch.tracks)} {'track' if len(batch.tracks) == 1 else 'tracks'}"
        if batch.save_file_url is not None:
            heading = f"{heading}  ·  save file: {batch.save_file_url}"
        await body.mount(Static(heading, classes="library-batch-heading"))
        table: DataTable[str] = DataTable()
        table.cursor_type = "row"
        table.add_columns(*_COLUMNS)
        for track in batch.tracks:
            file_cell = track.output_path or f"skipped ({track.skip_reason or 'exists'})"
            table.add_row(track.title, track.artists, file_cell, key=str(track.job_id))
        await body.mount(table)
