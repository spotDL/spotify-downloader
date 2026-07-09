"""``CollectionScreen`` — the shared album/artist/playlist detail screen (CONTRACT C).

One base for the three collection kinds: it loads a :class:`CollectionDetail` through
:class:`CollectionViewModel`, renders an :class:`EntityCard` header plus a track
``DataTable``, and wires the enqueue/drill-in bindings. The three subclasses
(``album``/``artist``/``playlist``) differ only in their ``KIND`` — all logic lives
here and in the view-model, keeping each subclass a handful of lines (CONTRACT B).

Bindings (documented decision, since the brief's letter map is ambiguous):

* ``e`` — enqueue the **whole** collection (``enqueue_all``) → toast ``queued N``.
* ``d`` — enqueue the **focused** track (``enqueue_track``) → toast ``queued N``.
* ``Enter`` — drill into the focused track's ``TrackScreen`` (parity; via
  ``NavigateTo``), so single-track actions also live on the track screen.

The two enqueue bindings are hidden entirely when the session can't download
(CONTRACT F) via :meth:`check_action`; ``Enter`` stays so browsing always works.
"""

from __future__ import annotations

from uuid import UUID

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import DataTable

from spotdl_cli.tui.messages import NavigateTo
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import EntityRef, TrackRow

_ENQUEUE_ACTIONS = frozenset({"enqueue_all", "enqueue_track"})


class CollectionScreen(SpotdlScreen):
    """Album/artist/playlist detail: header card + track table + enqueue."""

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
        # Body is filled after the async load resolves in ``on_mount``.
        yield VerticalScroll(id="collection-body")

    def on_mount(self) -> None:
        # Keep the sync base signature (status-bar paint) and drive the async load
        # in a worker so the frame renders immediately, then fills in.
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
        detail = result.data
        self._tracks = detail.tracks
        body = self.query_one("#collection-body", VerticalScroll)
        await body.mount(EntityCard(detail.header, id="entity-card"))
        table: DataTable[str] = DataTable(id="track-table")
        table.cursor_type = "row"
        table.add_columns("#", "Title", "Artists", "Duration")
        for position, row in enumerate(detail.tracks, start=1):
            table.add_row(str(position), row.title, row.artists, row.duration, key=str(row.id))
        await body.mount(table)
        table.focus()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide the enqueue bindings when downloads are unavailable (CONTRACT F)."""
        if action in _ENQUEUE_ACTIONS and not self._can_download():
            return None
        return True

    async def action_enqueue_all(self) -> None:
        result = await self._vm.enqueue_all()
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        self.notify(f"queued {result.data.job_count}")

    async def action_enqueue_track(self) -> None:
        row = self._focused_track()
        if row is None:
            return
        result = await self._vm.enqueue_track(row.id)
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
            ref = EntityRef(entity_type="track", id=row.id, title=row.title)
            self.post_message(NavigateTo(ref))

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
