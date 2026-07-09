"""``HomeSearchScreen`` — the query/paste box + results table (CONTRACT C, Task 5).

The always-on landing section. It owns no search logic: an ``Input`` submission is
handed to :class:`~spotdl_cli.viewmodels.search.SearchViewModel` — a plain query
runs ``search`` and fills the table, a pasted link runs ``open`` (``resolve`` → an
:class:`EntityRef`) and posts :class:`NavigateTo` for the app to route. Selecting a
result row posts ``NavigateTo`` for that track. Both remote calls run in an
exclusive background worker so the UI never blocks; errors become a toast.
"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input

from spotdl_cli.tui.messages import DegradedChanged, NavigateTo
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import EntityRef, TrackRow

_COLUMNS = ("#", "Artist — Title", "Album", "Duration")


def _looks_like_link(query: str) -> bool:
    """A pasted URL/URI is routed through ``open``; a bare phrase is searched."""
    return "://" in query or query.startswith("spotify:")


class HomeSearchScreen(SpotdlScreen):
    BINDINGS = [
        Binding("slash", "focus_search", "Search", show=False),
    ]

    def __init__(self) -> None:
        super().__init__(name="home")
        self._rows: dict[str, TrackRow] = {}

    def compose_content(self) -> ComposeResult:
        yield Input(placeholder="Search tracks, or paste a Spotify link", id="search-input")
        yield DataTable(id="search-results", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        super().on_mount()
        table = self.query_one("#search-results", DataTable)
        table.add_columns(*_COLUMNS)
        # Keep focus off the Input so the global number/? keys aren't swallowed as
        # text; ``/`` is how you drop into the search box (a vim-like landing).
        table.focus()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        if _looks_like_link(query):
            self._open(query)
        else:
            self._search(query)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        row = self._rows.get(key) if key is not None else None
        if row is not None:
            self.post_message(NavigateTo(EntityRef("track", row.id, row.title)))

    @work(exclusive=True, group="home-search")
    async def _search(self, query: str) -> None:
        result = await self.vm_factory.search().search(query)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            self._render_rows(())
            return
        assert result.data is not None
        self.post_message(DegradedChanged(result.data.degraded))
        self._render_rows(result.data.rows)

    @work(exclusive=True, group="home-search")
    async def _open(self, query: str) -> None:
        result = await self.vm_factory.search().open(query)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self.post_message(DegradedChanged(result.data.degraded))
        self.post_message(NavigateTo(result.data.ref))

    def _render_rows(self, rows: tuple[TrackRow, ...]) -> None:
        table = self.query_one("#search-results", DataTable)
        table.clear()
        self._rows.clear()
        for index, row in enumerate(rows, start=1):
            key = str(row.id)
            self._rows[key] = row
            title = f"{row.artists} — {row.title}"
            table.add_row(str(index), title, row.album, row.duration, key=key)
        if rows:
            table.focus()
