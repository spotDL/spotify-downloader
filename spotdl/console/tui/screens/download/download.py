import asyncio
import concurrent.futures
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, cast

from pyperclip import copy as clipboard_copy
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, ProgressBar, RichLog, Static
from textual.widgets.data_table import RowKey

from spotdl.console.save import save
from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.history import add_download_entry
from spotdl.console.tui.log_handler import BufferLogHandler

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

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

_COLOR_MAP = {
    "pending": "white",
    "searching": "cyan",
    "downloading": "blue",
    "converting": "magenta",
    "embedding": "yellow",
    "lyrics": "green",
    "done": "green",
    "error": "red",
    "skipped": "orange",
}


class DownloadScreen(Screen):
    BINDINGS = [
        Binding("escape", "back_menu", "menu"),
        Binding("l", "view_lyrics", "lyrics"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        super().__init__()
        self.operation = operation
        self.songs = songs
        self.options = options
        self._row_keys: Dict[str, RowKey] = {}
        self._done_count = 0
        self._error_count = 0
        self._skip_count = 0
        self._active = True
        self._pending_updates: List[tuple] = []
        self._pending_logs: List[str] = []

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Vertical(id="track-box", classes="box"):
            yield Static(
                TR("download.title"), id="download-title", classes="menu-title"
            )
            table: DataTable = DataTable(zebra_stripes=True, cursor_type="row")
            table.add_column(TR("download.col_song"), key="song")
            table.add_column(TR("download.col_status"), key="status", width=22)
            table.add_column(TR("download.col_detail"), key="detail", width=12)
            yield table

            with Vertical(id="overall-box"):
                yield Label(TR("download.overall", done=0, total=str(len(self.songs))))
                yield ProgressBar(total=100, show_eta=False, id="overall")

            yield RichLog(highlight=True, markup=True, id="log", wrap=True)

            with Horizontal(classes="row"):
                yield Button(TR("download.btn_stop"), id="stop-btn")
                yield Button(TR("download.btn_copy_log"), id="copy-log-btn")
                yield Button(TR("download.btn_menu"), variant="primary", id="menu-btn")
            yield Static("", id="status")
            yield Static("", id="status-bar", classes="status-bar")
        yield VersionFooter()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for song in self.songs:
            if song.url in self._row_keys:
                continue
            row_key = table.add_row(
                song.display_name,
                "[white]" + TR("download.status_pending") + "[/white]",
                "0%",
                key=song.url,
            )
            self._row_keys[song.url] = row_key

        self.set_timer(0.5, self._refresh_ui)

        self.run_worker(
            self._run_downloads,
            thread=True,
            exclusive=True,
            group="download",
            name="download-worker",
        )

    def _refresh_ui(self) -> None:
        if not self._active:
            return
        self._flush_pending()
        self.set_timer(0.5, self._refresh_ui)

    def _refresh_status_bar(self) -> None:
        if not self._active:
            return
        total = len(self.songs)
        table = self.query_one(DataTable)
        error_count = 0
        skipped_count = 0
        done_count = 0
        for song in self.songs:
            if song.url in self._row_keys:
                try:
                    row = table.get_row_at(
                        table.get_row_index(self._row_keys[song.url])
                    )
                    status = row[1] if len(row) > 1 else ""
                    if "[red]" in status:
                        error_count += 1
                    elif "[orange]" in status:
                        skipped_count += 1
                    elif "[green]" in status:
                        done_count += 1
                except Exception:
                    pass
        status_bar = self.query_one("#status-bar", Static)
        parts = []
        if done_count:
            parts.append(f"[green]{TR('download.badge_ok')} {done_count}[/green]")
        if error_count:
            parts.append(f"[red]X {error_count}[/red]")
        if skipped_count:
            parts.append(f"[orange]~ {skipped_count}[/orange]")
        pending = total - done_count - error_count - skipped_count
        if pending > 0:
            parts.append(f"[cyan]... {pending}[/cyan]")
        status_bar.update(
            " | ".join(parts) if parts else f"[dim]{TR('download.waiting')}[/dim]"
        )

    def action_back_menu(self) -> None:
        self._active = False
        self.app.pop_screen()
        self.app.pop_screen()

    def action_view_lyrics(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return
        url = getattr(row_key, "value", None) or str(row_key)
        song = next((s for s in self.songs if s.url == url), None)
        if song is not None:
            from spotdl.console.tui.lyrics import LyricsScreen

            self.app.push_screen(LyricsScreen(song))

    def copy_log(self) -> None:
        log_widget = self.query_one("#log", RichLog)
        lines = getattr(log_widget, "lines", []) or []
        texts = []
        for line in lines:
            plain = getattr(line, "plain", None) or str(line)
            texts.append(plain)
        text = "\n".join(texts)
        if not text:
            self.query_one("#status", Static).update(TR("download.log_empty"))
            return
        try:
            clipboard_copy(text)
            self.query_one("#status", Static).update(TR("download.log_copied"))
        except Exception:
            self.query_one("#status", Static).update(TR("download.log_copy_failed"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "stop-btn" and self._active:
            self._active = False
            for worker in self.app.workers:
                if worker.name == "download-worker":
                    worker.cancel()
            self.query_one("#status", Static).update(
                TR("download.stopped") + " " + TR("download.background_note")
            )
            self._mark_remaining_stopped()
        elif event.button.id == "menu-btn":
            self.action_back_menu()
        elif event.button.id == "copy-log-btn":
            self.copy_log()

    def _mark_remaining_stopped(self) -> None:
        table = self.query_one(DataTable)
        for song in self.songs:
            if song.url in self._row_keys:
                current = table.get_row_at(
                    table.get_row_index(self._row_keys[song.url])
                )
                if current[1] == "[white]" + TR("download.status_pending") + "[/white]":
                    table.update_cell(
                        self._row_keys[song.url],
                        "status",
                        "[orange]" + TR("download.status_skipped") + "[/orange]",
                    )

    def _run_downloads(self) -> None:
        app = cast("SpotdlApp", self.app)

        spotdl_logger = logging.getLogger("spotdl")
        previous_level = spotdl_logger.level
        log_handler = BufferLogHandler(self._pending_logs)
        log_handler.setLevel(logging.INFO)
        log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        spotdl_logger.addHandler(log_handler)
        if spotdl_logger.getEffectiveLevel() > logging.INFO:
            spotdl_logger.setLevel(logging.INFO)

        try:
            app.state.ensure_spotify(user_auth=False)
            downloader = app.state.ensure_downloader(self.options)

            asyncio.set_event_loop(downloader.loop)

            def _init_thread_loop() -> None:
                asyncio.set_event_loop(asyncio.new_event_loop())

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=downloader.settings.get("threads", 4),
                initializer=_init_thread_loop,
            ) as custom_executor:
                downloader.loop.set_default_executor(custom_executor)

                screen = self

                def progress_cb(tracker, message):
                    if not screen._active:
                        return
                    try:
                        url = tracker.song.url
                        row_key = screen._row_keys.get(url)
                        if not row_key:
                            return
                        status = tracker.status.lower()
                        status_type = "pending"
                        status_text = TR("download.status_pending")
                        for key, (stype, label_key) in _STATUS_MAP.items():
                            if key in status:
                                status_type = stype
                                status_text = TR(label_key)
                                break
                        color = _COLOR_MAP.get(status_type, "white")
                        colored_status = f"[{color}]{status_text}[/{color}]"
                        screen._pending_updates.append(
                            (row_key, colored_status, f"{int(tracker.progress or 0)}%")
                        )
                        if status_type in ("done", "error", "skipped"):
                            screen._done_count += 1
                            if status_type == "error":
                                screen._error_count += 1
                            elif status_type == "skipped":
                                screen._skip_count += 1
                    except Exception:
                        pass

                downloader.progress_handler.update_callback = progress_cb
                downloader.progress_handler.set_songs(self.songs)
                if self.operation == "save":
                    save_query = [s.url for s in self.songs]
                    save(query=save_query, downloader=downloader)
                else:
                    downloader.download_multiple_songs(self.songs)
                app.call_from_thread(self._finish)
        except Exception as exc:
            logger.error(TR("download.failed"), exc_info=exc)
            app.call_from_thread(self._fail, exc)
        finally:
            spotdl_logger.removeHandler(log_handler)
            spotdl_logger.setLevel(previous_level)

    def _refresh_overall(self) -> None:
        total = max(1, len(self.songs))
        percent = min(100.0, self._done_count / total * 100.0)
        self.query_one("#overall", ProgressBar).update(progress=percent)
        self.query_one("#overall-box", Vertical).query_one(Label).update(
            TR("download.overall", done=str(self._done_count), total=str(total))
        )

    def _finish(self) -> None:
        self._active = False
        self._flush_pending()
        ok = self._done_count - self._error_count - self._skip_count
        self.query_one("#status", Static).update(
            TR(
                "download.summary_ok",
                ok=str(max(0, ok)),
                err=str(self._error_count),
            )
        )
        self.query_one("#stop-btn", Button).disabled = True
        add_download_entry(
            self._history_name(),
            (self.options.get("query") or [None])[0],
            len(self.songs),
            max(0, ok),
            self._error_count,
        )

    def _history_name(self) -> str:
        if len(self.songs) == 1:
            return self.songs[0].display_name
        album_names = {getattr(song, "album_name", None) for song in self.songs}
        if len(album_names) == 1 and next(iter(album_names)):
            return str(next(iter(album_names)))
        return TR("history.track_count", count=str(len(self.songs)))

    def _flush_pending(self) -> None:
        table = self.query_one(DataTable)
        while self._pending_updates:
            row_key, status_text, detail = self._pending_updates.pop(0)
            try:
                table.update_cell(row_key, "status", status_text)
                table.update_cell(row_key, "detail", detail)
            except ValueError:
                pass
        if self._pending_logs:
            log_widget = self.query_one("#log", RichLog)
            while self._pending_logs:
                raw = self._pending_logs.pop(0)
                ts = datetime.now().strftime("%H:%M:%S")
                formatted = f"[dim]{ts}[/dim] {raw}"
                log_widget.write(formatted)
        total = max(1, len(self.songs))
        percent = min(100.0, self._done_count / total * 100.0)
        self.query_one("#overall", ProgressBar).update(progress=percent)
        self.query_one("#overall-box", Vertical).query_one(Label).update(
            TR("download.overall", done=str(self._done_count), total=str(total))
        )
        self._refresh_status_bar()

    def _fail(self, exc: Exception) -> None:
        self._active = False
        self.query_one("#status", Static).update(TR("query.error", message=str(exc)))
        self.query_one("#log", RichLog).write(str(exc))
        self.query_one("#stop-btn", Button).disabled = True
