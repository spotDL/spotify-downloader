"""
Screen that shows the progress of one download job.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pyperclip import PyperclipException
from pyperclip import copy as clipboard_copy
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, ProgressBar, RichLog, Static
from textual.widgets.data_table import CellDoesNotExist, ColumnKey, RowKey

from spotdl.console.tui import i18n
from spotdl.console.tui.lyrics.lyricspanel import LyricsScreen
from spotdl.console.tui.navigation import AppBar, VersionFooter

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr

logger = logging.getLogger(__name__)

_TERMINAL = {"done", "error", "cancelled"}

_STATUS_MAP = {
    "searching": ("searching", "download.status_searching"),
    "downloading": ("downloading", "download.status_downloading"),
    "converting": ("converting", "download.status_converting"),
    "metadata": ("embedding", "download.status_embedding"),
    "lyrics": ("lyrics", "download.status_lyrics"),
    "done": ("done", "download.status_done"),
    "error": ("error", "download.status_error"),
    "skip": ("skipped", "download.status_skipped"),
}

_COLUMNS = [
    ("song", "download.col_song", None),
    ("status", "download.col_status", 24),
    ("detail", "download.col_detail", 22),
]

_MILESTONES = {
    "error": ("X", "red"),
    "skipped": ("~", "yellow"),
    "done": ("v", "green"),
}

_NOISY_LOG_MARKERS = ("downloaded ", "downloading", "converting", "progress")


def _build_colored_bar(
    progress: int, status_type: str = "pending", width: int = 12
) -> Tuple[str, str]:
    percent = max(0, min(100, int(progress)))
    if status_type == "error":
        color = "red"
    elif status_type == "skipped":
        color = "orange"
    elif percent >= 100 or status_type == "done":
        color = "bold green"
    elif percent >= 75:
        color = "magenta"
    elif percent >= 45:
        color = "yellow"
    elif percent >= 25:
        color = "blue"
    else:
        color = "cyan"

    filled = int((percent / 100.0) * width)
    return f"[{color}]{'=' * filled}{'-' * (width - filled)}[/{color}]", color


def _status_of(tracker_status: str) -> Tuple[str, str]:
    status = (tracker_status or "").lower()
    for marker, (status_type, label_key) in _STATUS_MAP.items():
        if marker in status:
            return status_type, TR(label_key)
    return "pending", TR("download.status_pending")


class DownloadScreen(Screen):
    """
    Shows the per-song progress of one download job.

    The job itself runs in the application download manager, so leaving this
    screen or starting another download does not stop it.
    """

    BINDINGS = [
        Binding("escape", "back_menu", "menu"),
        Binding("l", "view_lyrics", "lyrics"),
    ]

    def __init__(
        self,
        operation: str,
        songs: List[Any],
        options: Dict[str, Any],
        job_id: Optional[str] = None,
        job_name: Optional[str] = None,
    ) -> None:
        """
        Create the screen.

        ### Arguments
        - operation: "download", "save" or "sync".
        - songs: Songs to process.
        - options: Options chosen in the query screen.
        - job_id: Existing job to show instead of starting a new one.
        - job_name: Name shown in the history.
        """

        super().__init__()
        self.operation = operation
        self.songs = songs
        self.options = options
        self.job_id = job_id
        self.job_name = job_name or self._history_name()
        self._songs_by_url = {song.url: song for song in songs}
        self._row_keys: Dict[str, RowKey] = {}
        self._completed_urls: set = set()
        self._log_history: List[str] = []
        self._done_count = 0
        self._error_count = 0
        self._skip_count = 0
        self._finished = False
        self._active = True
        self._log_cursor = 0

    def compose(self) -> ComposeResult:
        """
        Build the song table, the overall progress, the log and the buttons.
        """

        yield AppBar(TR("appbar.title"))
        with Vertical(id="track-box", classes="box"):
            yield Static(
                TR("download.title"), id="download-title", classes="menu-title"
            )
            table: DataTable = DataTable(zebra_stripes=True, cursor_type="row")
            for key, label_key, width in _COLUMNS:
                table.add_column(TR(label_key), key=key, width=width)
            yield table

            with Vertical(id="overall-box"):
                yield Label(TR("download.overall", done=0, total=str(len(self.songs))))
                yield ProgressBar(total=100, show_eta=False, id="overall")

            yield RichLog(highlight=True, markup=True, id="log", wrap=True)

            with Horizontal(classes="row"):
                yield Button(TR("download.btn_lyrics"), id="lyrics-btn")
                yield Button(TR("download.btn_stop"), id="stop-btn")
                yield Button(TR("download.btn_retry"), id="retry-btn")
                yield Button(TR("download.btn_copy_log"), id="copy-log-btn")
                yield Button(TR("download.btn_menu"), variant="primary", id="menu-btn")
            yield Static("", id="status")
            yield Static("", id="status-bar", classes="status-bar")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Fill the table, queue the job when needed and start polling it.
        """

        table = self.query_one(DataTable)
        bar_zero, _ = _build_colored_bar(0, "pending")
        for song in self.songs:
            if song.url not in self._row_keys:
                self._row_keys[song.url] = table.add_row(
                    song.display_name,
                    f"[white]{TR('download.status_pending')}[/white]",
                    f"{bar_zero} 0%",
                    key=song.url,
                )

        if self.job_id is None:
            manager = getattr(self.app, "downloads", None)
            if manager is not None:
                self.job_id = manager.submit(
                    self.job_name, self.operation, self.songs, self.options
                )

        self.set_interval(0.25, self._poll)
        self.query_one("#retry-btn", Button).disabled = True

    def action_back_menu(self) -> None:
        """
        Go back to the first screen, leaving the job running in the background.
        """

        self._active = False
        for _ in range(len(self.app.screen_stack) - 1):
            self.app.pop_screen()

    def action_view_lyrics(self) -> None:
        """
        Open the lyrics of the song under the cursor.
        """

        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except CellDoesNotExist:
            return
        song = self._songs_by_url.get(row_key.value)
        if song is not None:
            self.app.push_screen(
                LyricsScreen(song, output_dir=self.options.get("output_dir"))
            )

    def _write_log(self, markup_text: str, plain_text: str) -> None:
        if not self.is_attached:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#log", RichLog).write(f"[dim]{timestamp}[/dim] {markup_text}")
        self._log_history.append(f"[{timestamp}] {plain_text}")

    def copy_log(self) -> None:
        """
        Copy the plain text of the log to the clipboard.
        """

        status = self.query_one("#status", Static)
        if not self._log_history:
            status.update(TR("download.log_empty"))
            return
        try:
            clipboard_copy("\n".join(self._log_history))
        except PyperclipException:
            status.update(TR("download.log_copy_failed"))
            return
        status.update(TR("download.log_copied"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Open the lyrics, stop the job, copy the log or go back.
        """

        if event.button.id == "lyrics-btn":
            self.action_view_lyrics()
        elif event.button.id == "stop-btn" and self._active:
            self._active = False
            manager = getattr(self.app, "downloads", None)
            if manager is not None and self.job_id is not None:
                manager.cancel(self.job_id)
            self.query_one("#status", Static).update(
                TR("download.stopped") + " " + TR("download.background_note")
            )
            self._mark_remaining_stopped()
        elif event.button.id == "menu-btn":
            self.action_back_menu()
        elif event.button.id == "retry-btn":
            self._retry_failed()
        elif event.button.id == "copy-log-btn":
            self.copy_log()

    def _retry_failed(self) -> None:
        """
        Queue a new job with only the songs that failed.
        """

        manager = getattr(self.app, "downloads", None)
        if manager is None or self.job_id is None:
            return

        new_id = manager.retry_failed(self.job_id)
        if new_id is None:
            self.query_one("#status", Static).update(TR("download.retry_none"))
            return

        data = manager.job_options(new_id)
        if data is None:
            return

        name, operation, songs, options = data
        self.app.push_screen(
            DownloadScreen(operation, songs, options, job_id=new_id, job_name=name)
        )

    def _mark_remaining_stopped(self) -> None:
        table = self.query_one(DataTable)
        stopped = f"[orange]{TR('download.status_skipped')}[/orange]"
        for url, row_key in self._row_keys.items():
            if url not in self._completed_urls:
                table.update_cell(row_key, "status", stopped)

    def _poll(self) -> None:
        manager = getattr(self.app, "downloads", None)
        if manager is None or self.job_id is None or not self.is_attached:
            return

        progress = manager.song_progress(self.job_id)
        table = self.query_one(DataTable)
        for url, (percent, status, completed) in progress.items():
            row_key = self._row_keys.get(url)
            if row_key is None:
                continue
            status_type, status_text = _status_of(status)
            shown = 100 if completed else percent
            bar_markup, color = _build_colored_bar(shown, status_type)
            table.update_cell(row_key, "status", f"[{color}]{status_text}[/{color}]")
            table.update_cell(
                row_key, "detail", f"{bar_markup} [{color}]{int(shown)}%[/{color}]"
            )
            if completed and url not in self._completed_urls:
                self._completed_urls.add(url)
                self._log_song(url, status_type)

        new_logs = manager.job_logs(self.job_id, self._log_cursor)
        if new_logs:
            self._log_cursor += len(new_logs)
            for line in new_logs:
                clean = line.strip()
                if clean and not any(
                    marker in clean.lower() for marker in _NOISY_LOG_MARKERS
                ):
                    self._write_log(f"[dim]{clean}[/dim]", clean)

        info = next(
            (item for item in manager.snapshot() if item["id"] == self.job_id), None
        )
        if info is None:
            return

        self._refresh_progress(info)
        self.query_one("#retry-btn", Button).disabled = not info.get("can_retry", False)
        if info["status"] in _TERMINAL and not self._finished:
            self._finish(info)

    def _log_song(self, url: str, status_type: str) -> None:
        song = self._songs_by_url.get(url)
        name = getattr(song, "display_name", url)
        if status_type == "error":
            self._error_count += 1
            text = TR(
                "download.log_error", name=name, error=TR("download.status_error")
            )
        elif status_type == "skipped":
            self._skip_count += 1
            text = TR("download.log_skipped", name=name)
        else:
            self._done_count += 1
            text = TR("download.log_done", name=name)

        symbol, color = _MILESTONES.get(status_type, ("v", "green"))
        self._pending_log(symbol, color, text)

    def _pending_log(self, symbol: str, color: str, text: str) -> None:
        self._write_log(
            f"[bold {color}]{symbol}[/bold {color}] [{color}]{text}[/{color}]", text
        )

    def _finish(self, info: Dict[str, Any]) -> None:
        self._finished = True
        self._active = False
        ok = int(info.get("ok", 0))
        err = int(info.get("errors", 0))
        skipped = int(info.get("skipped", 0))

        if not self.is_attached:
            return

        self.query_one("#stop-btn", Button).disabled = True
        if info["status"] == "cancelled":
            self.query_one("#status", Static).update(TR("download.stopped"))
            return
        if info["status"] == "error":
            self._write_log(
                f"[bold red]X {info.get('error') or TR('download.status_error')}[/bold red]",
                str(info.get("error") or TR("download.status_error")),
            )
            return

        finish = TR(
            "download.log_finish", ok=str(ok), err=str(err), skipped=str(skipped)
        )
        self._write_log(f"[bold green]v {finish}[/bold green]", finish)
        self.query_one("#status", Static).update(
            TR("download.summary_ok", ok=str(ok), err=str(err))
        )

    def _history_name(self) -> str:
        if len(self.songs) == 1:
            return self.songs[0].display_name
        album_names = {getattr(song, "album_name", None) for song in self.songs}
        if len(album_names) == 1 and next(iter(album_names)):
            return str(next(iter(album_names)))
        return TR("history.track_count", count=str(len(self.songs)))

    def _refresh_progress(self, info: Dict[str, Any]) -> None:
        total = int(info.get("total", len(self.songs)))
        done = int(info.get("done", 0))
        ok = int(info.get("ok", 0))
        err = int(info.get("errors", 0))
        skipped = int(info.get("skipped", 0))

        self.query_one("#overall", ProgressBar).update(
            progress=min(100.0, float(info.get("percent", 0)))
        )
        self.query_one("#overall-box", Vertical).query_one(Label).update(
            TR("download.overall", done=str(done), total=str(total))
        )

        parts = []
        if ok:
            parts.append(f"[green]{TR('download.badge_ok')} {ok}[/green]")
        if err:
            parts.append(f"[red]X {err}[/red]")
        if skipped:
            parts.append(f"[orange]~ {skipped}[/orange]")
        if total > done:
            parts.append(f"[cyan]... {total - done}[/cyan]")
        self.query_one("#status-bar", Static).update(
            " | ".join(parts) if parts else f"[dim]{TR('download.waiting')}[/dim]"
        )

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#download-title", Static).update(TR("download.title"))
        table = self.query_one(DataTable)
        for key, label_key, _ in _COLUMNS:
            table.columns[ColumnKey(key)].label = Text(TR(label_key))
        table.refresh()
        self.query_one("#lyrics-btn", Button).label = TR("download.btn_lyrics")
        self.query_one("#stop-btn", Button).label = TR("download.btn_stop")
        self.query_one("#retry-btn", Button).label = TR("download.btn_retry")
        self.query_one("#copy-log-btn", Button).label = TR("download.btn_copy_log")
        self.query_one("#menu-btn", Button).label = TR("download.btn_menu")
        self.query_one(VersionFooter).refresh_language()
