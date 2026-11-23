"""
Screen that lists every queued and running download job.
"""

from typing import Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static
from textual.widgets.data_table import CellDoesNotExist, ColumnKey, RowKey

from spotdl.console.tui import i18n
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.download import (
    DownloadScreen,
    _build_colored_bar,
)
from spotdl.console.tui.widgets import FailedLinksModal

TR = i18n.tr

_COLUMNS = [
    ("name", "downloads.col_name", None),
    ("status", "downloads.col_status", 14),
    ("progress", "downloads.col_progress", 18),
    ("songs", "downloads.col_songs", 10),
]

_STATUS_COLORS = {
    "queued": "dim",
    "running": "cyan",
    "done": "green",
    "error": "red",
    "cancelled": "orange",
}


def _status_label(status: str) -> str:
    return TR(f"downloads.status_{status}")


class DownloadsScreen(Screen):
    """
    Lists the jobs handled by the application download manager.

    Queued jobs start automatically when a slot is free, so several playlists
    can be added without waiting for the previous one to finish.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("d", "cancel", "cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._row_keys: Dict[str, RowKey] = {}

    def compose(self) -> ComposeResult:
        """
        Build the job table and the action buttons.
        """

        yield AppBar(TR("downloads.title"))
        with Vertical(id="downloads-box", classes="box"):
            yield Static(
                TR("downloads.title"), id="downloads-title", classes="menu-title"
            )
            table: DataTable = DataTable(zebra_stripes=True, cursor_type="row")
            for key, label_key, width in _COLUMNS:
                table.add_column(TR(label_key), key=key, width=width)
            yield table

            with Horizontal(classes="row"):
                yield Button(TR("downloads.btn_open"), id="downloads-open-btn")
                yield Button(TR("downloads.btn_retry"), id="downloads-retry-btn")
                yield Button(TR("downloads.btn_links"), id="downloads-links-btn")
                yield Button(TR("downloads.btn_cancel"), id="downloads-cancel-btn")
                yield Button(TR("downloads.btn_clear"), id="downloads-clear-btn")
                yield Button(
                    TR("downloads.btn_back"),
                    variant="primary",
                    id="downloads-back-btn",
                )
            yield Static("", id="downloads-status")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Fill the table and keep it updated while the screen is open.
        """

        self.refresh_jobs()
        self.set_interval(0.5, self.refresh_jobs)

    def _selected_job(self) -> Optional[str]:
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except CellDoesNotExist:
            return None
        return row_key.value

    def refresh_jobs(self) -> None:
        """
        Add, update or remove the rows that belong to the current jobs.
        """

        manager = getattr(self.app, "downloads", None)
        if manager is None or not self.is_attached:
            return

        snapshot = manager.snapshot()
        table = self.query_one(DataTable)
        seen = set()

        for info in snapshot:
            job_id = info["id"]
            seen.add(job_id)
            color = _STATUS_COLORS.get(info["status"], "white")
            status_text = f"[{color}]{_status_label(info['status'])}[/{color}]"
            percent = int(info["percent"])
            progress_bar, _ = _build_colored_bar(percent, info["status"])
            progress_text = f"{progress_bar} {percent}%"
            songs_text = f"{info['done']}/{info['total']}"

            row_key = self._row_keys.get(job_id)
            if row_key is None:
                self._row_keys[job_id] = table.add_row(
                    info["name"], status_text, progress_text, songs_text, key=job_id
                )
            else:
                table.update_cell(row_key, "name", info["name"])
                table.update_cell(row_key, "status", status_text)
                table.update_cell(row_key, "progress", progress_text)
                table.update_cell(row_key, "songs", songs_text)

        for job_id in list(self._row_keys):
            if job_id not in seen:
                table.remove_row(self._row_keys.pop(job_id))

        status = self.query_one("#downloads-status", Static)
        if snapshot:
            status.update("")
        else:
            status.update(TR("downloads.empty"))

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def action_cancel(self) -> None:
        """
        Cancel the selected job.
        """

        job_id = self._selected_job()
        manager = getattr(self.app, "downloads", None)
        if job_id and manager is not None:
            manager.cancel(job_id)
            self.refresh_jobs()

    def action_open(self) -> None:
        """
        Open the selected job in the download screen.
        """

        job_id = self._selected_job()
        if job_id:
            self._open_job(job_id)

    def _open_job(self, job_id: str) -> None:
        manager = getattr(self.app, "downloads", None)
        if manager is None:
            return

        data = manager.job_options(job_id)
        if data is None:
            return

        name, operation, songs, options = data
        self.app.push_screen(
            DownloadScreen(operation, songs, options, job_id=job_id, job_name=name)
        )

    def action_retry(self) -> None:
        """
        Retry only the songs that failed in the selected job.
        """

        job_id = self._selected_job()
        manager = getattr(self.app, "downloads", None)
        if not job_id or manager is None:
            return

        new_id = manager.retry_failed(job_id)
        if new_id is None:
            self.query_one("#downloads-status", Static).update(
                TR("downloads.retry_none")
            )
            return

        self._open_job(new_id)

    def action_retry_with_links(self) -> None:
        """
        Ask for a link per failed song, then retry them with those links.
        """

        job_id = self._selected_job()
        manager = getattr(self.app, "downloads", None)
        if not job_id or manager is None:
            return

        songs = manager.failed_songs(job_id)
        if not songs:
            self.query_one("#downloads-status", Static).update(
                TR("downloads.retry_none")
            )
            return

        def _retry(links: Optional[Dict[str, str]]) -> None:
            if links is None:
                return
            new_id = manager.retry_failed(job_id, links)
            if new_id is not None:
                self._open_job(new_id)

        self.app.push_screen(FailedLinksModal(songs), _retry)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Open, cancel, clear or go back.
        """

        if event.button.id == "downloads-back-btn":
            self.action_back()
        elif event.button.id == "downloads-cancel-btn":
            self.action_cancel()
        elif event.button.id == "downloads-retry-btn":
            self.action_retry()
        elif event.button.id == "downloads-links-btn":
            self.action_retry_with_links()
        elif event.button.id == "downloads-open-btn":
            self.action_open()
        elif event.button.id == "downloads-clear-btn":
            manager = getattr(self.app, "downloads", None)
            if manager is not None:
                manager.clear_finished()
                self.refresh_jobs()

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("downloads.title"))
        self.query_one("#downloads-title", Static).update(TR("downloads.title"))
        table = self.query_one(DataTable)
        for key, label_key, _ in _COLUMNS:
            table.columns[ColumnKey(key)].label = Text(TR(label_key))
        table.refresh()
        self.query_one("#downloads-open-btn", Button).label = TR("downloads.btn_open")
        self.query_one("#downloads-retry-btn", Button).label = TR("downloads.btn_retry")
        self.query_one("#downloads-links-btn", Button).label = TR("downloads.btn_links")
        self.query_one("#downloads-cancel-btn", Button).label = TR(
            "downloads.btn_cancel"
        )
        self.query_one("#downloads-clear-btn", Button).label = TR("downloads.btn_clear")
        self.query_one("#downloads-back-btn", Button).label = TR("downloads.btn_back")
        self.refresh_jobs()
        self.query_one(VersionFooter).refresh_language()
