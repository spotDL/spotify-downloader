"""``HomeSearchScreen`` — the universal search box + sectioned results (CONTRACT C, §4).

The always-on landing section. A big bordered input tops a results panel that fills
with four labeled sections — Artists · Albums · Songs · Playlists — each with a count
(``SearchViewModel.search`` returns all four groups). A plain query runs ``search``; a
pasted link runs ``open`` (``resolve`` → an :class:`EntityRef`) and posts
:class:`NavigateTo`. ``f`` cycles a filter (All / one section) so a crowded result set
narrows to one group. Selecting a song row resolves its provider snapshot then opens the
track; selecting an artist/album/playlist row routes straight to that collection screen;
``d`` enqueues the cursor song (when downloads are available). When the query is empty the
panel shows recent searches (or the offline metadata note). Two banners pin atop the
results: an involuntary remote→embedded fallback warning and a degraded-sources notice.
Remote calls run in an exclusive worker so the UI never blocks; errors become a toast.
"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import DataTable, Input, Static

from spotdl_cli.tui.messages import DegradedChanged, NavigateTo
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import EntityRef, SearchHit, SearchResult, TrackRow

_SONG_COLUMNS = ("#", "Title", "Artists", "Duration", "Source")
_RESULTS_HINT = "enter open · d download · f filter"
_RECENT_LIMIT = 8
_OFFLINE_EMPTY = "offline mode — metadata from local providers only"
_ONLINE_EMPTY = "Type a query and press enter, or paste a Spotify link"
_NO_HITS = "no results — try another query"

# Filter cycle order; "all" shows every non-empty section, else just that one.
_FILTERS = ("all", "artists", "albums", "songs", "playlists")

# Every universal-search section in render order: (filter key, title, table id, title id,
# columns). The "songs" section renders a TrackRow (five columns); the rest render a
# SearchHit preview (three columns). ``search-results`` keeps its id for CONTRACT C.
_SECTIONS = (
    ("artists", "Artists", "artists-results", "artists-title", ("Artist", "Genres", "Followers")),
    ("albums", "Albums", "albums-results", "albums-title", ("Album", "Artist", "Type / Year")),
    ("songs", "Songs", "search-results", "songs-title", _SONG_COLUMNS),
    (
        "playlists",
        "Playlists",
        "playlists-results",
        "playlists-title",
        ("Playlist", "Owner", "Tracks"),
    ),
)


def _looks_like_link(query: str) -> bool:
    """A pasted URL/URI is routed through ``open``; a bare phrase is searched."""
    return "://" in query or query.startswith("spotify:")


class HomeSearchScreen(SpotdlScreen):
    BINDINGS = [
        Binding("slash", "focus_search", "Search", show=False),
        Binding("f", "cycle_filter", "Filter"),
        Binding("d", "download_selected", "Download"),
    ]

    def __init__(self) -> None:
        super().__init__(name="home")
        self._rows: dict[str, TrackRow] = {}
        self._hits: dict[str, SearchHit] = {}
        self._recent: list[str] = []
        self._filter = "all"
        self._last: SearchResult | None = None

    def compose_content(self) -> ComposeResult:
        with Vertical(id="search-box", classes="panel"):
            yield Input(
                placeholder="Search tracks, albums, artists, playlists, or paste a link",
                id="search-input",
            )
        yield Static("", id="filter-chips")
        with Vertical(id="results-panel", classes="panel"):
            yield Static("", id="fallback-banner", classes="banner banner--warn hidden")
            yield Static("", id="degraded-banner", classes="banner banner--degraded hidden")
            with VerticalScroll(id="results-scroll"):
                for _key, _title, table_id, title_id, columns in _SECTIONS:
                    yield Static("", id=title_id, classes="section-title hidden")
                    table: DataTable[str] = DataTable(
                        id=table_id, cursor_type="row", zebra_stripes=True
                    )
                    table.add_class("section-table", "hidden")
                    table.add_columns(*columns)
                    yield table
            yield Static("", id="results-empty", classes="results-empty")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#search-box", Vertical).border_title = "Search or paste a link"
        panel = self.query_one("#results-panel", Vertical)
        panel.border_title = "Results"
        panel.border_subtitle = _RESULTS_HINT
        self._refresh_banners()
        self._refresh_chips()
        self._apply_filter()
        # Keep focus off the Input so the global number/? keys aren't swallowed as
        # text; ``/`` is how you drop into the search box (a vim-like landing).
        self.query_one("#search-results", DataTable).focus()

    def on_screen_resume(self) -> None:
        # A degraded resolve or a connection switch elsewhere may have changed state.
        self._refresh_banners()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_cycle_filter(self) -> None:
        self._filter = _FILTERS[(_FILTERS.index(self._filter) + 1) % len(_FILTERS)]
        self._refresh_chips()
        self._apply_filter()

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
        if event.data_table.id == "search-results":
            self._open_song(key)
            return
        hit = self._hits.get(key) if key is not None else None
        if hit is not None:
            self.post_message(NavigateTo(EntityRef(hit.entity_type, hit.id, hit.title)))

    def _open_song(self, key: str | None) -> None:
        row = self._rows.get(key) if key is not None else None
        if row is None:
            return
        if row.provider and row.provider_id:
            # A search hit is a provider-snapshot preview, not a canonical entity;
            # resolve `{provider}:track:{id}` into the canonical id the track page
            # loads (the raw snapshot id 404s at GET /tracks/{id}).
            self._open(f"{row.provider}:track:{row.provider_id}")
        else:
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
        row = self._rows.get(row_key.value) if row_key.value is not None else None
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
            self._render_result(None)
            return
        assert result.data is not None
        self._remember(query)
        self.post_message(DegradedChanged(result.data.degraded))
        self._set_degraded_banner(result.data.degraded_sources)
        self._render_result(result.data)

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

    def _remember(self, query: str) -> None:
        if query in self._recent:
            self._recent.remove(query)
        self._recent.insert(0, query)
        del self._recent[_RECENT_LIMIT:]

    # -- rendering ------------------------------------------------------------
    def _render_result(self, result: SearchResult | None) -> None:
        self._last = result
        self._rows.clear()
        self._hits.clear()
        for key, _title, table_id, _title_id, _columns in _SECTIONS:
            if key == "songs":
                self._fill_songs(result.rows if result is not None else ())
            else:
                hits = getattr(result, key) if result is not None else ()
                self._fill_hits(table_id, hits)
        self._refresh_chips()
        self._apply_filter()

    def _fill_songs(self, rows: tuple[TrackRow, ...]) -> None:
        table = self.query_one("#search-results", DataTable)
        table.clear()
        for index, row in enumerate(rows, start=1):
            key = str(row.id)
            self._rows[key] = row
            table.add_row(
                str(index), row.title, row.artists, row.duration, row.provider or "—", key=key
            )

    def _fill_hits(self, table_id: str, hits: tuple[SearchHit, ...]) -> None:
        table = self.query_one(f"#{table_id}", DataTable)
        table.clear()
        for hit in hits:
            key = str(hit.id)
            self._hits[key] = hit
            table.add_row(hit.title, hit.subtitle, hit.detail, key=key)

    def _apply_filter(self) -> None:
        """Show sections matching the active filter that have rows; else the empty note."""
        any_shown = False
        first_table: DataTable[str] | None = None
        for key, title, table_id, title_id, _columns in _SECTIONS:
            table = self.query_one(f"#{table_id}", DataTable)
            visible = self._filter in ("all", key) and table.row_count > 0
            table.set_class(not visible, "hidden")
            title_widget = self.query_one(f"#{title_id}", Static)
            title_widget.set_class(not visible, "hidden")
            if visible:
                title_widget.update(f"{title} · {table.row_count}")
                any_shown = True
                if first_table is None:
                    first_table = table
        self._refresh_empty(has_rows=any_shown)
        if first_table is not None:
            first_table.focus()

    # -- chips + empty state + banners ----------------------------------------
    def _refresh_chips(self) -> None:
        counts = self._counts()
        parts: list[str] = []
        for key in _FILTERS:
            marker = "●" if key == self._filter else "○"
            label = "All" if key == "all" else key.capitalize()
            count = sum(counts.values()) if key == "all" else counts.get(key, 0)
            suffix = f" {count}" if self._last is not None and count else ""
            parts.append(f"{marker} {label}{suffix}")
        self.query_one("#filter-chips", Static).update("   ".join(parts))

    def _counts(self) -> dict[str, int]:
        if self._last is None:
            return {}
        return {
            "artists": len(self._last.artists),
            "albums": len(self._last.albums),
            "songs": len(self._last.rows),
            "playlists": len(self._last.playlists),
        }

    def _refresh_empty(self, *, has_rows: bool | None = None) -> None:
        empty = self.query_one("#results-empty", Static)
        if has_rows is None:
            has_rows = self._last is not None and self._last.total > 0
        empty.set_class(has_rows, "hidden")
        self.query_one("#results-scroll", VerticalScroll).set_class(not has_rows, "hidden")
        if not has_rows:
            empty.update(self._empty_text())

    def _empty_text(self) -> str:
        if self._last is not None:
            return _NO_HITS
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
