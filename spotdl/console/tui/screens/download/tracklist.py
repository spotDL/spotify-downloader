import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Set, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static
from textual.widgets.data_table import RowKey

from spotdl.console.save import save
from spotdl.console.tui import i18n
from spotdl.console.tui.bar import AppBar, VersionFooter, handle_appbar
from spotdl.console.tui.screens.download.confirm import ConfirmScreen
from spotdl.console.tui.settings import format_duration

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr

logger = logging.getLogger(__name__)


class TrackListScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("space", "toggle_select", "toggle"),
        Binding("l", "view_lyrics", "lyrics"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        super().__init__()
        self.operation = operation
        seen: Set[str] = set()
        unique_songs: List[Any] = []
        for song in songs:
            if song.url in seen:
                continue
            seen.add(song.url)
            unique_songs.append(song)
        removed = len(songs) - len(unique_songs)
        if removed:
            logger.warning(
                TR("tracklist.duplicates_removed", count=str(removed)),
            )
        self.songs = unique_songs
        self.options = options
        self._row_keys: Dict[str, RowKey] = {}
        self._selected: Set[str] = {song.url for song in self.songs}

    def compose(self) -> ComposeResult:
        yield AppBar(TR("appbar.title"))
        with Vertical(id="track-box", classes="box"):
            yield Static(
                TR("tracklist.title", count=str(len(self.songs))),
                id="track-title",
                classes="menu-title",
            )
            table: DataTable = DataTable(zebra_stripes=True, cursor_type="row")
            table.add_column(TR("tracklist.col_sel"), key="sel", width=5)
            table.add_column(TR("tracklist.col_title"), key="title", width=30)
            table.add_column(TR("tracklist.col_artist"), key="artist", width=22)
            table.add_column(TR("tracklist.col_album"), key="album", width=20)
            table.add_column(TR("tracklist.col_duration"), key="duration", width=10)
            table.add_column(TR("tracklist.col_explicit"), key="explicit", width=6)
            yield table

            with Horizontal(classes="row"):
                yield Button(TR("tracklist.btn_all"), id="all-btn")
                yield Button(TR("tracklist.btn_none"), id="none-btn")
                yield Button(TR("tracklist.btn_invert"), id="invert-btn")
                yield Button(
                    TR("tracklist.btn_proceed", n=0),
                    variant="primary",
                    id="proceed-btn",
                )
                yield Button(TR("tracklist.btn_back"), id="back-btn")
            yield Static("", id="status")
        yield VersionFooter()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for song in self.songs:
            is_sel = song.url in self._selected
            icon = (
                Text("[✓]", style="bold green") if is_sel else Text("[ ]", style="dim")
            )
            row_key = table.add_row(
                icon,
                song.display_name or song.name or "",
                ", ".join(song.artists) if song.artists else "",
                song.album_name or "",
                format_duration(song.duration),
                "Y" if getattr(song, "explicit", False) else "",
                key=song.url,
            )
            self._row_keys[song.url] = row_key
        self._refresh_selected()

    def action_back(self) -> None:
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

    def action_toggle_select(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            url = getattr(row_key, "value", None) or str(row_key)
            self._toggle_song(url)
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        url = getattr(event.row_key, "value", None) or str(event.row_key)
        self._toggle_song(url)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        url = getattr(event.cell_key.row_key, "value", None) or str(
            event.cell_key.row_key
        )
        self._toggle_song(url)

    def _toggle_song(self, url: str) -> None:
        if url in self._selected:
            self._selected.remove(url)
        else:
            self._selected.add(url)
        self._update_row_icon(url)
        self._refresh_selected()

    def _update_row_icon(self, url: str) -> None:
        table = self.query_one(DataTable)
        if url in self._row_keys:
            is_sel = url in self._selected
            icon = (
                Text("[✓]", style="bold green") if is_sel else Text("[ ]", style="dim")
            )
            table.update_cell(self._row_keys[url], "sel", icon)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if handle_appbar(self, event):
            return
        if event.button.id == "back-btn":
            self.action_back()
            return

        if event.button.id == "all-btn":
            self._selected = {song.url for song in self.songs}
        elif event.button.id == "none-btn":
            self._selected.clear()
        elif event.button.id == "invert-btn":
            all_urls = {song.url for song in self.songs}
            self._selected = all_urls - self._selected

        self._rebuild_checkboxes()
        if event.button.id == "proceed-btn":
            self._proceed()

    def _rebuild_checkboxes(self) -> None:
        for song in self.songs:
            self._update_row_icon(song.url)
        self._refresh_selected()

    def _refresh_selected(self) -> None:
        total_seconds = sum(
            song.duration or 0 for song in self.songs if song.url in self._selected
        )
        self.query_one("#status", Static).update(
            TR(
                "tracklist.total",
                count=str(len(self._selected)),
                duration=format_duration(total_seconds),
            )
        )
        self.query_one("#proceed-btn", Button).label = TR(
            "tracklist.btn_proceed", n=str(len(self._selected))
        )

    def _proceed(self) -> None:
        if not self._selected:
            self.query_one("#status", Static).update(TR("tracklist.none_selected"))
            return

        selected_songs = [song for song in self.songs if song.url in self._selected]
        if self.operation == "save":
            self._run_save(selected_songs)
        else:
            self.app.push_screen(
                ConfirmScreen(self.operation, selected_songs, self.options)
            )

    def _run_save(self, songs: List[Any]) -> None:
        options = dict(self.options)
        if not options.get("save_file"):
            options["save_file"] = "tui.spotdl"

        screen = self

        def run_save() -> None:
            app = cast("SpotdlApp", screen.app)
            try:
                app.state.ensure_spotify(user_auth=False)
                downloader = app.state.ensure_downloader(options)
                asyncio.set_event_loop(downloader.loop)
                save(query=[s.url for s in songs], downloader=downloader)
                app.call_from_thread(screen.app.pop_screen)
            except Exception as exc:
                app.call_from_thread(screen.app.notify, str(exc), severity="error")

        self.run_worker(run_save, thread=True, exclusive=True, group="save")

    def refresh_language(self) -> None:
        try:
            appbar = self.query_one(AppBar)
            appbar.set_title(TR("appbar.title"))
        except Exception:
            pass
        try:
            self.query_one("#track-title", Static).update(
                TR("tracklist.title", count=str(len(self.songs)))
            )
        except Exception:
            pass
        try:
            table = self.query_one(DataTable)
            column_keys = {
                "sel": "tracklist.col_sel",
                "title": "tracklist.col_title",
                "artist": "tracklist.col_artist",
                "album": "tracklist.col_album",
                "duration": "tracklist.col_duration",
                "explicit": "tracklist.col_explicit",
            }
            for key, tr_key in column_keys.items():
                table.columns[key].label = Text(TR(tr_key))  # type: ignore[index]
            table.refresh()
        except Exception:
            pass
        try:
            self.query_one("#all-btn", Button).label = TR("tracklist.btn_all")
            self.query_one("#none-btn", Button).label = TR("tracklist.btn_none")
            self.query_one("#invert-btn", Button).label = TR("tracklist.btn_invert")
            self.query_one("#back-btn", Button).label = TR("tracklist.btn_back")
        except Exception:
            pass
        try:
            self.query_one(VersionFooter).refresh_language()
        except Exception:
            pass
        self._refresh_selected()
