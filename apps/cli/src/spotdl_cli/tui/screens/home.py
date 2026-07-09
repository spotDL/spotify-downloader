"""``HomeSearchScreen`` — the query/paste box + results table (CONTRACT C, §4).

The always-on landing section. A big bordered input tops a results panel that fills:
a plain query runs :class:`~spotdl_cli.viewmodels.search.SearchViewModel` ``search``
and fills the table (# · Title · Artists · Duration · Source); a pasted link runs
``open`` (``resolve`` → an :class:`EntityRef`) and posts :class:`NavigateTo`. Selecting
a row opens its track; ``d`` enqueues the cursor row (when downloads are available).
When the query is empty the results panel shows recent searches (or the offline
metadata note). Two banners pin atop the results: an involuntary remote→embedded
fallback warning (``app.fallback_active``) and a degraded-sources notice. Remote calls
run in an exclusive worker so the UI never blocks; errors become a toast.
"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static

from spotdl_cli.tui.messages import DegradedChanged, NavigateTo
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import EntityRef, TrackRow

_COLUMNS = ("#", "Title", "Artists", "Duration", "Source")
_RESULTS_HINT = "enter open · d download"
_RECENT_LIMIT = 8
_OFFLINE_EMPTY = "offline mode — metadata from local providers only"
_ONLINE_EMPTY = "Type a query and press enter, or paste a Spotify link"


def _looks_like_link(query: str) -> bool:
    """A pasted URL/URI is routed through ``open``; a bare phrase is searched."""
    return "://" in query or query.startswith("spotify:")


class HomeSearchScreen(SpotdlScreen):
    BINDINGS = [
        Binding("slash", "focus_search", "Search", show=False),
        Binding("d", "download_selected", "Download"),
    ]

    def __init__(self) -> None:
        super().__init__(name="home")
        self._rows: dict[str, TrackRow] = {}
        self._recent: list[str] = []

    def compose_content(self) -> ComposeResult:
        with Vertical(id="search-box", classes="panel"):
            yield Input(placeholder="Search tracks, or paste a Spotify link", id="search-input")
        yield Static("● Tracks   ○ All", id="filter-chips")
        with Vertical(id="results-panel", classes="panel"):
            yield Static("", id="fallback-banner", classes="banner banner--warn hidden")
            yield Static("", id="degraded-banner", classes="banner banner--degraded hidden")
            yield DataTable(id="search-results", cursor_type="row", zebra_stripes=True)
            yield Static("", id="results-empty", classes="results-empty")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#search-box", Vertical).border_title = "Search or paste a link"
        panel = self.query_one("#results-panel", Vertical)
        panel.border_title = "Results"
        panel.border_subtitle = _RESULTS_HINT
        table = self.query_one("#search-results", DataTable)
        table.add_columns(*_COLUMNS)
        self._refresh_banners()
        self._refresh_empty()
        # Keep focus off the Input so the global number/? keys aren't swallowed as
        # text; ``/`` is how you drop into the search box (a vim-like landing).
        table.focus()

    def on_screen_resume(self) -> None:
        # A degraded resolve or a connection switch elsewhere may have changed state.
        self._refresh_banners()

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
        row = self._row_for(event.row_key.value)
        if row is not None:
            self.post_message(NavigateTo(EntityRef("track", row.id, row.title)))

    # -- download-from-search (the panel's "d download" hint) -----------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "download_selected":
            session = self.spotdl_app.session
            return session is not None and session.can_download
        return True

    def action_download_selected(self) -> None:
        table = self.query_one("#search-results", DataTable)
        if table.row_count == 0:
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        row = self._row_for(row_key.value)
        if row is not None:
            self._download(row)

    @work(exclusive=True, group="home-download")
    async def _download(self, row: TrackRow) -> None:
        result = await self.vm_factory.queue().enqueue(str(row.id))
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self.notify(f"queued {row.title}")

    # -- search + resolve -----------------------------------------------------
    @work(exclusive=True, group="home-search")
    async def _search(self, query: str) -> None:
        result = await self.vm_factory.search().search(query)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            self._render_rows(())
            return
        assert result.data is not None
        self._remember(query)
        self.post_message(DegradedChanged(result.data.degraded))
        self._set_degraded_banner(result.data.degraded_sources)
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

    def _row_for(self, key: str | None) -> TrackRow | None:
        return self._rows.get(key) if key is not None else None

    def _remember(self, query: str) -> None:
        if query in self._recent:
            self._recent.remove(query)
        self._recent.insert(0, query)
        del self._recent[_RECENT_LIMIT:]

    def _render_rows(self, rows: tuple[TrackRow, ...]) -> None:
        table = self.query_one("#search-results", DataTable)
        table.clear()
        self._rows.clear()
        for index, row in enumerate(rows, start=1):
            key = str(row.id)
            self._rows[key] = row
            source = row.provider or "—"
            table.add_row(str(index), row.title, row.artists, row.duration, source, key=key)
        self._refresh_empty()
        if rows:
            table.focus()

    # -- empty state + banners ------------------------------------------------
    def _refresh_empty(self) -> None:
        table = self.query_one("#search-results", DataTable)
        empty = self.query_one("#results-empty", Static)
        has_rows = table.row_count > 0
        table.set_class(not has_rows, "hidden")
        empty.set_class(has_rows, "hidden")
        if not has_rows:
            empty.update(self._empty_text())

    def _empty_text(self) -> str:
        if self._recent:
            recent = "\n".join(f"  ↳ {query}" for query in self._recent)
            return f"Recent searches\n\n{recent}"
        session = self.spotdl_app.session
        if session is not None and session.mode == "embedded":
            return _OFFLINE_EMPTY
        return _ONLINE_EMPTY

    def _refresh_banners(self) -> None:
        fallback = self.query_one("#fallback-banner", Static)
        show = self.spotdl_app.fallback_active
        fallback.set_class(not show, "hidden")
        if show:
            fallback.update(
                "⚠  remote server unreachable — using the offline engine. Press 0 to reconnect."
            )

    def _set_degraded_banner(self, sources: tuple[str, ...]) -> None:
        banner = self.query_one("#degraded-banner", Static)
        banner.set_class(not sources, "hidden")
        if sources:
            banner.update(f"⚠  some sources unavailable: {', '.join(sources)}")
