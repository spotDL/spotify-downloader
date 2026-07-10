"""``CollectionScreen`` — the shared album/artist/playlist detail screen (§4).

One base for the three collection kinds. Per the redesign contract §4 it renders a
full-width :class:`EntityCard` header, a tracks ``DataTable`` that fills (``1fr``:
``#`` · Title · Duration · Matched?), and a right side panel (32 cols) that carries
the metadata block plus the enqueue actions. Under 110 cols the two columns collapse
to one (``on_resize`` toggles a ``narrow`` class). The three subclasses
(:class:`AlbumScreen`/:class:`ArtistScreen`/:class:`PlaylistScreen`) differ only in
their ``KIND`` and live in this module so the screen-module count stays bounded.

Bindings:

* ``e`` — enqueue the **whole** collection (``enqueue_all``) → toast ``queued N``.
* ``d`` — enqueue the **focused** track (``enqueue_track``) → toast ``queued N``.
* ``Enter`` — drill into the focused track's ``TrackScreen`` (via ``NavigateTo``).

``enqueue_all`` is hidden when the session can't download **and** for the artist kind
(enqueuing a whole artist is unsupported — the side panel explains why); ``enqueue_track``
is hidden only when downloads are unavailable (CONTRACT F) via :meth:`check_action`.
"""

from __future__ import annotations

from uuid import UUID

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.widget import Widget
from textual.widgets import Button, DataTable, Static

from spotdl_cli.tui.messages import NavigateTo
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.tui.widgets.patterns import LoadingPane
from spotdl_cli.tui.widgets.sources_panel import SourcesPanel
from spotdl_cli.viewmodels.base import Loadable, LoadState
from spotdl_cli.viewmodels.types import BatchRef, CollectionDetail, EntityRef, TrackRow

_ENQUEUE_ACTIONS = frozenset({"enqueue_all", "enqueue_track"})
_NARROW_WIDTH = 110  # two columns collapse to one below this (contract §1)


class CollectionScreen(SpotdlScreen):
    """Album/artist/playlist detail: header card + tracks table + enqueue panel."""

    KIND: str = ""

    BINDINGS = [
        Binding("e", "enqueue_all", "Download all"),
        Binding("d", "enqueue_track", "Download track"),
    ]

    def __init__(self, entity_id: UUID) -> None:
        super().__init__()
        self._entity_id = entity_id
        self._tracks: tuple[TrackRow, ...] = ()

    def compose_content(self) -> ComposeResult:
        # A loading pane fills the region until the async load resolves in ``on_mount``.
        yield Vertical(LoadingPane("Loading collection…"), id="collection-body")

    def on_mount(self) -> None:
        super().on_mount()
        self.run_worker(self._load(), exclusive=True)

    async def _load(self) -> None:
        self._vm = self.vm_factory.collection()
        result = await self._vm.load(self.KIND, self._entity_id)
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        await self._render_detail(result.data)

    async def _render_detail(self, detail: CollectionDetail) -> None:
        self._tracks = detail.tracks
        body = self.query_one("#collection-body", Vertical)
        await body.remove_children()
        card = EntityCard(detail.header, id="entity-card")
        card.border_title = detail.header.kind
        await body.mount(card)
        main = Horizontal(id="collection-main")
        await body.mount(main)
        await main.mount(self._build_table(detail))
        await main.mount(self._build_side(detail))
        self._apply_width(self.size.width)
        self.query_one("#track-table", DataTable).focus()
        # Provenance loads on its own worker so a slow/absent /sources endpoint
        # degrades to an empty panel rather than blocking the collection view.
        self.run_worker(self._load_sources(), exclusive=False, group="collection-sources")

    def _build_table(self, detail: CollectionDetail) -> DataTable[str]:
        table: DataTable[str] = DataTable(id="track-table", cursor_type="row", zebra_stripes=True)
        table.add_class("panel")
        table.border_title = "Tracks"
        table.add_columns("#", "Title", "Duration", "Matched?")
        for position, row in enumerate(detail.tracks, start=1):
            # Per-track match status is not in the collection payload (it would need
            # a lookup per track); the column renders "—" until a track is opened.
            table.add_row(str(position), row.title, row.duration, "—", key=str(row.id))
        return table

    def _build_side(self, detail: CollectionDetail) -> Vertical:
        rows: list[Widget] = [Static(_metadata(detail), classes="collection-meta")]
        if self._can_download() and self.KIND != "artist":
            rows.append(Button("↧ Enqueue all", id="enqueue-all", variant="primary"))
        if self._can_download():
            rows.append(Button("↧ Enqueue track", id="enqueue-track"))
        note = _side_note(detail.kind, can_download=self._can_download())
        if note:
            rows.append(Static(note, classes="collection-note"))
        sources = VerticalScroll(
            LoadingPane("Loading sources…"), id="collection-sources", classes="panel"
        )
        sources.border_title = "Sources"
        rows.append(sources)
        side = Vertical(*rows, id="collection-side", classes="panel")
        side.border_title = "Actions"
        return side

    async def _load_sources(self) -> None:
        result = await self._vm.load_sources(self.KIND, self._entity_id)
        panel = self.query_one("#collection-sources", VerticalScroll)
        await panel.remove_children()
        rows = result.data if result.state is LoadState.READY and result.data is not None else ()
        await panel.mount(SourcesPanel(rows))

    # -- gating ---------------------------------------------------------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide enqueue bindings when unavailable; enqueue-all also for artists (§4)."""
        if action in _ENQUEUE_ACTIONS and not self._can_download():
            return None
        if action == "enqueue_all" and self.KIND == "artist":
            return None
        return True

    # -- enqueue --------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enqueue-all":
            self.run_worker(self.action_enqueue_all(), exclusive=True)
        elif event.button.id == "enqueue-track":
            self.run_worker(self.action_enqueue_track(), exclusive=True)

    async def action_enqueue_all(self) -> None:
        self._toast_batch(await self._vm.enqueue_all())

    async def action_enqueue_track(self) -> None:
        row = self._focused_track()
        if row is None:
            return
        self._toast_batch(await self._vm.enqueue_track(row.id))

    def _toast_batch(self, result: Loadable[BatchRef]) -> None:
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        self.notify(f"queued {result.data.job_count}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on a row drills into that track's screen (CONTRACT C parity)."""
        row = self._track_for_key(event.row_key.value)
        if row is not None:
            self.post_message(
                NavigateTo(EntityRef(entity_type="track", id=row.id, title=row.title))
            )

    # -- responsive collapse --------------------------------------------------
    def on_resize(self, event: Resize) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        main = self.query("#collection-main")
        if not main:
            return
        main.first().set_class(width < _NARROW_WIDTH, "narrow")

    # -- helpers --------------------------------------------------------------
    def _focused_track(self) -> TrackRow | None:
        table = self.query_one("#track-table", DataTable)
        index = table.cursor_row
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None

    def _track_for_key(self, key: str | None) -> TrackRow | None:
        return next((row for row in self._tracks if str(row.id) == key), None)

    def _can_download(self) -> bool:
        session = self.spotdl_app.session
        return session is not None and session.can_download


def _metadata(detail: CollectionDetail) -> str:
    lines = [f"[b]{detail.header.title}[/b]"]
    if detail.header.subtitle:
        lines.append(detail.header.subtitle)
    lines.extend(f"{label}: {value}" for label, value in detail.header.stats)
    return "\n".join(lines)


def _side_note(kind: str, *, can_download: bool) -> str:
    if not can_download:
        return "Downloads are unavailable on this connection."
    if kind == "artist":
        return "Enqueue-all is unsupported for an artist — pick a track and press d."
    if kind == "playlist":
        return "Enqueuing a playlist writes an .spotdl save file you can re-download."
    return ""


class AlbumScreen(CollectionScreen):
    """The album variant of :class:`CollectionScreen` (§4)."""

    KIND = "album"


class ArtistScreen(CollectionScreen):
    """The artist variant of :class:`CollectionScreen` (§4)."""

    KIND = "artist"


class PlaylistScreen(CollectionScreen):
    """The playlist variant of :class:`CollectionScreen` (§4)."""

    KIND = "playlist"
