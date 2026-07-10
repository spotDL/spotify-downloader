"""``LibraryScreen`` — completed downloads, browsed batch → files (§4, CONTRACT C/F).

The library section (gated on ``SessionSnapshot.library``): it loads the completed
downloads through :class:`~spotdl_cli.viewmodels.library.LibraryViewModel`, which groups
them by submission batch. The screen is two panes (§4): a left ``ListView`` of batches
(id + file count) and, for the highlighted batch, a right files table (path · format ·
size when the file is stat-able) under a heading that carries the batch's ``.spotdl``
save-file URL. ``s`` echoes that save-file path; ``o`` reveals the selected file in the
platform file manager. Under 110 cols the two panes stack (``on_resize``). All grouping
lives in the view-model — the screen only paints and reveals.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.widgets import DataTable, Label, ListItem, ListView, Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.patterns import EmptyState, LoadingPane
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import LibraryBatch, LibraryTrack

_COLUMNS = ("File", "Format", "Size")
_NARROW_WIDTH = 110


class LibraryScreen(SpotdlScreen):
    """Completed downloads: a batch list left, its files table right (§4)."""

    BINDINGS = [
        Binding("s", "save_file", "Save-file path"),
        Binding("o", "reveal", "Reveal file"),
    ]

    def __init__(self) -> None:
        super().__init__(name="library")
        self._batches: tuple[LibraryBatch, ...] = ()

    def compose_content(self) -> ComposeResult:
        yield Vertical(LoadingPane("Loading library…"), id="library-body")

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
        self._batches = result.data
        body = self.query_one("#library-body", Vertical)
        await body.remove_children()
        if not self._batches:
            await body.mount(
                EmptyState(
                    "▦", "No downloads yet", key_hint="press 1 to search, then d to download"
                )
            )
            return
        await body.mount(self._build_main())
        self._apply_width(self.size.width)
        self._select_batch(0)

    def _build_main(self) -> Horizontal:
        items = [
            ListItem(Label(_batch_label(batch)), id=f"batch-{index}")
            for index, batch in enumerate(self._batches)
        ]
        batches = ListView(*items, id="library-batches", classes="panel")
        batches.border_title = "Batches"
        detail = Vertical(
            Static("", id="library-detail-head", classes="library-batch-heading"),
            DataTable(id="library-files", cursor_type="row", zebra_stripes=True),
            id="library-detail",
            classes="panel",
        )
        detail.border_title = "Files"
        return Horizontal(batches, detail, id="library-main")

    # -- selection ------------------------------------------------------------
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is not None and event.item.id is not None:
            self._select_batch(int(event.item.id.removeprefix("batch-")))

    def _select_batch(self, index: int) -> None:
        if not 0 <= index < len(self._batches):
            return
        batch = self._batches[index]
        head = self.query_one("#library-detail-head", Static)
        head.update(_heading(batch))
        table = self.query_one("#library-files", DataTable)
        table.clear(columns=True)
        table.add_columns(*_COLUMNS)
        for track in batch.tracks:
            table.add_row(*_file_cells(track), key=str(track.job_id))

    # -- actions --------------------------------------------------------------
    def action_save_file(self) -> None:
        batch = self._current_batch()
        if batch is None:
            return
        if batch.save_file_url is None:
            self.notify("no save file for this group", severity="warning")
            return
        self.notify(f"save file: {batch.save_file_url}")

    def action_reveal(self) -> None:
        path = self._focused_path()
        if path is None:
            self.notify("no file to reveal", severity="warning")
            return
        self.notify(f"revealing {path}")
        _reveal(path)

    # -- responsive collapse --------------------------------------------------
    def on_resize(self, event: Resize) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        main = self.query("#library-main")
        if main:
            main.first().set_class(width < _NARROW_WIDTH, "narrow")

    # -- helpers --------------------------------------------------------------
    def _current_batch(self) -> LibraryBatch | None:
        index = self.query_one("#library-batches", ListView).index
        if index is None or not 0 <= index < len(self._batches):
            return None
        return self._batches[index]

    def _focused_path(self) -> str | None:
        batch = self._current_batch()
        if batch is None:
            return None
        table = self.query_one("#library-files", DataTable)
        row = table.cursor_row
        if not 0 <= row < len(batch.tracks):
            return None
        return batch.tracks[row].output_path


def _batch_label(batch: LibraryBatch) -> str:
    if batch.name:
        title = f"{batch.kind.capitalize()} · {batch.name}" if batch.kind else batch.name
    elif batch.batch_id is not None:
        title = batch.batch_id.hex[:8]
    else:
        title = "unbatched"
    count = len(batch.tracks)
    return f"{title}\n{count} {'file' if count == 1 else 'files'}"


def _heading(batch: LibraryBatch) -> str:
    if batch.save_file_url is not None:
        return f"save file: {batch.save_file_url}   ([s] copy · [o] reveal)"
    return "no save file for this group   ([o] reveal)"


def _file_cells(track: LibraryTrack) -> tuple[str, str, str]:
    if track.output_path is None:
        return (f"skipped ({track.skip_reason or 'exists'})", "—", "—")
    path = Path(track.output_path)
    fmt = path.suffix.lstrip(".") or "—"
    return (track.output_path, fmt, _size(path))


def _size(path: Path) -> str:
    try:
        return _human_size(path.stat().st_size)
    except OSError:
        return "—"  # server path, or a file not present locally


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _reveal(path: str) -> None:
    """Open the file's folder in the platform file manager (best-effort, guarded)."""
    if not os.path.exists(path):
        return  # server path or missing file — nothing to reveal locally
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])  # noqa: S603, S607 — reveal in Finder
        elif sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", path])  # noqa: S603, S607
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])  # noqa: S603, S607
    except OSError:
        pass
