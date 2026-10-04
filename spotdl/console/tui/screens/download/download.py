"""
Screen that downloads the selected songs and shows the progress of each one.
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, cast

from pyperclip import PyperclipException
from pyperclip import copy as clipboard_copy
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, ProgressBar, RichLog, Static
from textual.widgets.data_table import CellDoesNotExist, ColumnKey, RowKey

from spotdl.console.save import save
from spotdl.console.sync import sync
from spotdl.console.tui import i18n
from spotdl.console.tui.history import add_download_entry
from spotdl.console.tui.log_handler import BufferLogHandler
from spotdl.console.tui.lyrics.lyricspanel import LyricsScreen
from spotdl.console.tui.navigation import AppBar, VersionFooter

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp
    from spotdl.download.progress_handler import SongTracker

TR = i18n.tr

logger = logging.getLogger(__name__)

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
    "error": ("✗", "red"),
    "skipped": ("~", "yellow"),
    "done": ("✓", "green"),
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
    status = tracker_status.lower()
    for marker, (status_type, label_key) in _STATUS_MAP.items():
        if marker in status:
            return status_type, TR(label_key)
    return "pending", TR("download.status_pending")


class DownloadScreen(Screen):
    """
    Downloads (or saves) the selected songs in a worker thread.

    Progress reported by the downloader threads is buffered and applied to the
    table and log four times per second.
    """

    BINDINGS = [
        Binding("escape", "back_menu", "menu"),
        Binding("l", "view_lyrics", "lyrics"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        """
        Create the screen.

        ### Arguments
        - operation: "download" or "save".
        - songs: Songs to process.
        - options: Options chosen in the query screen.
        """

        super().__init__()
        self.operation = operation
        self.songs = songs
        self.options = options
        self._state_lock = threading.Lock()
        self._row_keys: Dict[str, RowKey] = {}
        self._done_count = 0
        self._error_count = 0
        self._skip_count = 0
        self._active = True
        self._completed_urls: Set[str] = set()
        self._pending_cell_updates: Dict[str, Tuple[str, str]] = {}
        self._pending_logs: List[Tuple[str, str]] = []
        self._log_history: List[str] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

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
                yield Button(TR("download.btn_copy_log"), id="copy-log-btn")
                yield Button(TR("download.btn_menu"), variant="primary", id="menu-btn")
            yield Static("", id="status")
            yield Static("", id="status-bar", classes="status-bar")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Add one row per song and start the downloads.
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

        self.set_interval(0.25, self._flush_pending)
        self._run_downloads()

    def action_back_menu(self) -> None:
        """
        Go back to the first screen, leaving running downloads in the background.
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
        song = next((s for s in self.songs if s.url == row_key.value), None)
        if song is not None:
            self.app.push_screen(
                LyricsScreen(song, output_dir=self.options.get("output_dir"))
            )

    def _write_log(self, markup_text: str, plain_text: str) -> None:
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
        Open the lyrics, stop the downloads, copy the log or go back.
        """

        if event.button.id == "lyrics-btn":
            self.action_view_lyrics()
        elif event.button.id == "stop-btn" and self._active:
            self._active = False
            self.stop_downloads()
            self.query_one("#status", Static).update(
                TR("download.stopped") + " " + TR("download.background_note")
            )
            self._mark_remaining_stopped()
        elif event.button.id == "menu-btn":
            self.action_back_menu()
        elif event.button.id == "copy-log-btn":
            self.copy_log()

    def stop_downloads(self) -> None:
        """
        Cancel every song that has not started yet. Songs being processed
        finish their current step and nothing else starts.
        """

        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(
                lambda: [task.cancel() for task in asyncio.all_tasks(loop)]
            )

    def _mark_remaining_stopped(self) -> None:
        table = self.query_one(DataTable)
        with self._state_lock:
            completed = set(self._completed_urls)
        stopped = f"[orange]{TR('download.status_skipped')}[/orange]"
        for url, row_key in self._row_keys.items():
            if url not in completed:
                table.update_cell(row_key, "status", stopped)

    def _on_progress(self, tracker: "SongTracker", message: Optional[str]) -> None:
        url = tracker.song.url
        if not self._active or url not in self._row_keys:
            return

        status_type, status_text = _status_of(tracker.status)
        progress = int(tracker.progress or 0)
        bar_markup, color = _build_colored_bar(progress, status_type)

        with self._state_lock:
            self._pending_cell_updates[url] = (
                f"[{color}]{status_text}[/{color}]",
                f"{bar_markup} [{color}]{progress}%[/{color}]",
            )

            if status_type not in _MILESTONES or url in self._completed_urls:
                return

            self._completed_urls.add(url)
            self._done_count += 1
            name = tracker.song.display_name
            if status_type == "error":
                self._error_count += 1
                text = TR(
                    "download.log_error",
                    name=name,
                    error=message or tracker.status or "Error",
                )
            elif status_type == "skipped":
                self._skip_count += 1
                text = TR("download.log_skipped", name=name)
            else:
                text = TR("download.log_done", name=name)

            symbol, color = _MILESTONES[status_type]
            self._pending_logs.append(
                (
                    f"[bold {color}]{symbol}[/bold {color}] [{color}]{text}[/{color}]",
                    f"{symbol} {text}",
                )
            )

    def _on_log_record(self, message: str) -> None:
        clean = message.strip()
        if clean and not any(marker in clean.lower() for marker in _NOISY_LOG_MARKERS):
            with self._state_lock:
                self._pending_logs.append((f"[dim]{clean}[/dim]", clean))

    @work(thread=True, exclusive=True, group="download")
    def _run_downloads(self) -> None:
        app = cast("SpotdlApp", self.app)

        start = TR(
            "download.log_start",
            count=str(len(self.songs)),
            threads=str(self.options.get("threads") or 4),
        )
        with self._state_lock:
            self._pending_logs.append(
                (f"[bold cyan]● {start}[/bold cyan]", f"● {start}")
            )

        spotdl_logger = logging.getLogger("spotdl")
        previous_level = spotdl_logger.level
        log_handler = BufferLogHandler(self._on_log_record)
        log_handler.setLevel(logging.INFO)
        log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        spotdl_logger.addHandler(log_handler)
        if spotdl_logger.getEffectiveLevel() > logging.INFO:
            spotdl_logger.setLevel(logging.INFO)

        try:
            app.state.ensure_spotify(user_auth=False)
            downloader = app.state.ensure_downloader(self.options)
            self._loop = downloader.loop
            asyncio.set_event_loop(downloader.loop)
            downloader.progress_handler.update_callback = self._on_progress
            downloader.progress_handler.set_songs(self.songs)
            if self.operation == "save":
                save(query=[song.url for song in self.songs], downloader=downloader)
            elif self.operation == "sync":
                sync(query=self.options["query"], downloader=downloader)
            else:
                downloader.download_multiple_songs(self.songs)
        except asyncio.CancelledError:
            app.call_from_thread(self._finish)
        except Exception as exc:
            logger.error(TR("download.failed"), exc_info=exc)
            app.call_from_thread(self._fail, exc)
        else:
            app.call_from_thread(self._finish)
        finally:
            spotdl_logger.removeHandler(log_handler)
            spotdl_logger.setLevel(previous_level)

    def _counts(self) -> Tuple[int, int, int]:
        with self._state_lock:
            ok = self._done_count - self._error_count - self._skip_count
            return max(0, ok), self._error_count, self._skip_count

    def _finish(self) -> None:
        self._active = False
        ok, err, skipped = self._counts()
        add_download_entry(
            name=self._history_name(),
            url=(self.options.get("query") or [None])[0],
            count=len(self.songs),
            ok=ok,
            err=err,
            skipped=skipped,
            operation=self.operation,
        )
        if not self.is_attached:
            return

        self._flush_pending()
        finish = TR(
            "download.log_finish", ok=str(ok), err=str(err), skipped=str(skipped)
        )
        self._write_log(f"[bold green]✓ {finish}[/bold green]", f"✓ {finish}")
        self.query_one("#status", Static).update(
            TR("download.summary_ok", ok=str(ok), err=str(err))
        )
        self.query_one("#stop-btn", Button).disabled = True

    def _history_name(self) -> str:
        if len(self.songs) == 1:
            return self.songs[0].display_name
        album_names = {getattr(song, "album_name", None) for song in self.songs}
        if len(album_names) == 1 and next(iter(album_names)):
            return str(next(iter(album_names)))
        return TR("history.track_count", count=str(len(self.songs)))

    def _flush_pending(self) -> None:
        with self._state_lock:
            cell_updates = self._pending_cell_updates
            self._pending_cell_updates = {}
            pending_logs = self._pending_logs
            self._pending_logs = []

        table = self.query_one(DataTable)
        for url, (status_text, detail) in cell_updates.items():
            row_key = self._row_keys[url]
            table.update_cell(row_key, "status", status_text)
            table.update_cell(row_key, "detail", detail)

        for markup_text, plain_text in pending_logs:
            self._write_log(markup_text, plain_text)

        self._refresh_progress()

    def _refresh_progress(self) -> None:
        total = len(self.songs)
        with self._state_lock:
            done = self._done_count
        ok, err, skipped = self._counts()

        self.query_one("#overall", ProgressBar).update(
            progress=min(100.0, done / max(1, total) * 100.0)
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

    def _fail(self, exc: Exception) -> None:
        self._active = False
        if not self.is_attached:
            return
        self._write_log(f"[bold red]✗ {exc}[/bold red]", f"✗ {exc}")
        self.query_one("#status", Static).update(TR("query.error", message=str(exc)))
        self.query_one("#stop-btn", Button).disabled = True

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
        self._refresh_progress()
        self.query_one("#lyrics-btn", Button).label = TR("download.btn_lyrics")
        self.query_one("#stop-btn", Button).label = TR("download.btn_stop")
        self.query_one("#copy-log-btn", Button).label = TR("download.btn_copy_log")
        self.query_one("#menu-btn", Button).label = TR("download.btn_menu")
        self.query_one(VersionFooter).refresh_language()
