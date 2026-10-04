"""
Screen that lists the songs found for a query and lets the user pick them.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, cast

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static
from textual.widgets.data_table import CellDoesNotExist, ColumnKey, RowKey

from spotdl.console.save import save
from spotdl.console.tui import i18n
from spotdl.console.tui.lyrics.lyricspanel import LyricsScreen
from spotdl.console.tui.navigation import AppBar, VersionFooter
from spotdl.console.tui.screens.download.confirm import ConfirmScreen
from spotdl.console.tui.settings import format_duration

if TYPE_CHECKING:
    from spotdl.console.tui.app import SpotdlApp

TR = i18n.tr

logger = logging.getLogger(__name__)

_COLUMNS = [
    ("sel", "tracklist.col_sel", 5),
    ("title", "tracklist.col_title", 38),
    ("artist", "tracklist.col_artist", 25),
    ("album", "tracklist.col_album", 25),
    ("duration", "tracklist.col_duration", 10),
    ("explicit", "tracklist.col_explicit", 6),
]


def _selection_icon(selected: bool) -> Text:
    return Text("[✓]", style="bold green") if selected else Text("[ ]", style="dim")


def _display_title(song: Any) -> str:
    title = song.name or ""
    for artist in [song.artist, *(song.artists or [])]:
        if artist and title.lower().startswith(f"{artist.lower()} - "):
            return title[len(artist) + 3 :].strip()
    return title


class TrackListScreen(Screen):
    """
    Table of songs with checkboxes, used before downloading or saving.
    """

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("space", "toggle_select", "toggle"),
        Binding("l", "view_lyrics", "lyrics"),
    ]

    def __init__(
        self, operation: str, songs: List[Any], options: Dict[str, Any]
    ) -> None:
        """
        Create the screen, dropping songs that share the same url.

        ### Arguments
        - operation: Operation that runs with the selected songs.
        - songs: Songs found for the query.
        - options: Options chosen in the query screen.
        """

        super().__init__()
        self.operation = operation
        seen: Set[str] = set()
        unique_songs: List[Any] = []
        for song in songs:
            if song.url not in seen:
                seen.add(song.url)
                unique_songs.append(song)
        removed = len(songs) - len(unique_songs)
        if removed:
            logger.warning(TR("tracklist.duplicates_removed", count=str(removed)))
        self.songs = unique_songs
        self.options = options
        self._row_keys: Dict[str, RowKey] = {}
        self._selected: Set[str] = {song.url for song in self.songs}

    def compose(self) -> ComposeResult:
        """
        Build the song table and the selection buttons.
        """

        yield AppBar(TR("appbar.title"))
        with Vertical(id="track-box", classes="box"):
            yield Static(
                TR("tracklist.title", count=str(len(self.songs))),
                id="track-title",
                classes="menu-title",
            )
            table: DataTable = DataTable(zebra_stripes=True, cursor_type="row")
            for key, label_key, width in _COLUMNS:
                table.add_column(TR(label_key), key=key, width=width)
            yield table

            with Horizontal(classes="row"):
                yield Button(TR("tracklist.btn_all"), id="all-btn")
                yield Button(TR("tracklist.btn_none"), id="none-btn")
                yield Button(TR("tracklist.btn_invert"), id="invert-btn")
                yield Button(TR("tracklist.btn_lyrics"), id="lyrics-btn")
                yield Button(
                    TR("tracklist.btn_proceed", n=0),
                    variant="primary",
                    id="proceed-btn",
                )
                yield Button(TR("tracklist.btn_back"), id="back-btn")
            yield Static("", id="status")
        yield VersionFooter()

    def on_mount(self) -> None:
        """
        Fill the table with the songs.
        """

        table = self.query_one(DataTable)
        for song in self.songs:
            artists = ", ".join(song.artists) if song.artists else (song.artist or "")
            self._row_keys[song.url] = table.add_row(
                _selection_icon(song.url in self._selected),
                _display_title(song),
                artists,
                song.album_name or getattr(song, "list_name", "") or "-",
                format_duration(song.duration),
                "Y" if getattr(song, "explicit", False) else "",
                key=song.url,
            )
        self._refresh_selected()

    def _song_under_cursor(self) -> Optional[Any]:
        table = self.query_one(DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except CellDoesNotExist:
            return None
        return next((song for song in self.songs if song.url == row_key.value), None)

    def action_back(self) -> None:
        """
        Go back to the previous screen.
        """

        self.app.pop_screen()

    def action_view_lyrics(self) -> None:
        """
        Open the lyrics of the song under the cursor.
        """

        song = self._song_under_cursor()
        if song is not None:
            self.app.push_screen(
                LyricsScreen(song, output_dir=self.options.get("output_dir"))
            )

    def action_toggle_select(self) -> None:
        """
        Select or unselect the song under the cursor.
        """

        song = self._song_under_cursor()
        if song is not None:
            self._toggle_song(song.url)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Select or unselect the clicked song.
        """

        if event.row_key.value is not None:
            self._toggle_song(event.row_key.value)

    def _toggle_song(self, url: str) -> None:
        if url in self._selected:
            self._selected.remove(url)
        else:
            self._selected.add(url)
        self._update_row_icon(url)
        self._refresh_selected()

    def _update_row_icon(self, url: str) -> None:
        if url in self._row_keys:
            self.query_one(DataTable).update_cell(
                self._row_keys[url], "sel", _selection_icon(url in self._selected)
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Change the selection, open the lyrics or continue.
        """

        button_id = event.button.id
        if button_id == "back-btn":
            self.action_back()
            return
        if button_id == "lyrics-btn":
            self.action_view_lyrics()
            return

        if button_id == "all-btn":
            self._selected = {song.url for song in self.songs}
        elif button_id == "none-btn":
            self._selected.clear()
        elif button_id == "invert-btn":
            self._selected = {song.url for song in self.songs} - self._selected

        for song in self.songs:
            self._update_row_icon(song.url)
        self._refresh_selected()
        if button_id == "proceed-btn":
            self._proceed()

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
            options = dict(self.options)
            options["save_file"] = options.get("save_file") or "tui.spotdl"
            self._run_save(selected_songs, options)
        else:
            self.app.push_screen(
                ConfirmScreen(self.operation, selected_songs, self.options)
            )

    @work(thread=True, exclusive=True, group="save")
    def _run_save(self, songs: List[Any], options: Dict[str, Any]) -> None:
        app = cast("SpotdlApp", self.app)
        try:
            app.state.ensure_spotify(user_auth=False)
            downloader = app.state.ensure_downloader(options)
            asyncio.set_event_loop(downloader.loop)
            save(query=[song.url for song in songs], downloader=downloader)
        except Exception as exc:
            app.call_from_thread(app.notify, str(exc), severity="error")
            return
        app.call_from_thread(app.pop_screen)

    def refresh_language(self) -> None:
        """
        Translate the screen to the current language.
        """

        self.query_one(AppBar).set_title(TR("appbar.title"))
        self.query_one("#track-title", Static).update(
            TR("tracklist.title", count=str(len(self.songs)))
        )
        table = self.query_one(DataTable)
        for key, label_key, _ in _COLUMNS:
            table.columns[ColumnKey(key)].label = Text(TR(label_key))
        table.refresh()
        self.query_one("#all-btn", Button).label = TR("tracklist.btn_all")
        self.query_one("#none-btn", Button).label = TR("tracklist.btn_none")
        self.query_one("#invert-btn", Button).label = TR("tracklist.btn_invert")
        self.query_one("#lyrics-btn", Button).label = TR("tracklist.btn_lyrics")
        self.query_one("#back-btn", Button).label = TR("tracklist.btn_back")
        self.query_one(VersionFooter).refresh_language()
        self._refresh_selected()
