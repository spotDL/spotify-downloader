"""``QueueScreen`` — the live download queue (CONTRACT C/E, redesign §3/§4).

The CONTRACT E shape: a single background worker owns the WS code path. It seeds from
``list_downloads``, then folds every frame the ``QueueViewModel.stream`` yields into a
reactive ``snapshot``; ``watch_snapshot`` repaints the :class:`QueueTable` (jobs grouped
by batch) and the summary strip (overall bar + chips). Nothing else touches the socket.
``x`` cancels the focused job, and the enqueue ``Input`` submits a pasted URL/query.

Mode matrix (§3): the summary panel titles itself "Downloads (local)" for the community
/ embedded engine and "Server queue" for a self-hosted server, where jobs run server-side
and paths are server paths; there ``f`` fetches the focused batch's ``.spotdl`` save file.
Unmounting the screen cancels the worker (Textual ties node workers to the DOM).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.widgets import Input, Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.theme import segmented_meter
from spotdl_cli.tui.widgets.patterns import EmptyState
from spotdl_cli.tui.widgets.queue_table import QueueTable
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import JobRow, QueueSnapshot

_EMPTY = QueueSnapshot(
    jobs=(), overall_percent=0, active=0, completed=0, failed=0, skipped=0, cancelled=0
)
_BAR_WIDTH = 16


class QueueScreen(SpotdlScreen):
    """Live queue: enqueue input + summary strip + a WS-driven, batch-grouped table."""

    BINDINGS = [
        Binding("x", "cancel", "Cancel job"),
        Binding("f", "fetch_save_file", "Fetch save file"),
    ]

    snapshot: reactive[QueueSnapshot] = reactive(_EMPTY)

    def compose_content(self) -> ComposeResult:
        yield Input(placeholder="paste a Spotify URL or search query…", id="enqueue-input")
        yield Static(_counts_line(_EMPTY), id="queue-summary", classes="panel")
        yield EmptyState(
            "♪",
            "No downloads yet",
            key_hint="press 1 to search, then d to download",
            id="queue-empty",
        )
        yield QueueTable(id="queue-table", classes="hidden")
        yield Static("", id="queue-actions")

    def on_mount(self) -> None:
        super().on_mount()
        self._vm = self.vm_factory.queue()
        summary = self.query_one("#queue-summary", Static)
        summary.border_title = "Server queue" if self._vm.is_server_queue else "Downloads (local)"
        self.query_one("#queue-actions", Static).update(self._actions_line())
        # Focus the table so job bindings (``x``) reach the screen; the enqueue
        # input takes focus only when the user tabs/clicks into it.
        self.query_one(QueueTable).focus()
        # One worker owns the whole WS lifecycle; it is cancelled on unmount.
        self._worker = self.run_worker(self._run(), exclusive=True, group="queue-ws")

    async def _run(self) -> None:
        seeded = await self._vm.load()
        if seeded.state is LoadState.ERROR:
            assert seeded.error is not None
            self.show_error(seeded.error)
        elif seeded.data is not None:
            self.snapshot = seeded.data
        async for update in self._vm.stream():
            if update.state is LoadState.ERROR:
                assert update.error is not None
                self.show_error(update.error)
                return  # protocol mismatch / exhausted reconnects → stop the worker
            assert update.data is not None
            self.snapshot = update.data

    def watch_snapshot(self, snapshot: QueueSnapshot) -> None:
        if not self.is_mounted:
            return
        has_jobs = bool(snapshot.jobs)
        self.query_one("#queue-empty", EmptyState).set_class(has_jobs, "hidden")
        self.query_one(QueueTable).set_class(not has_jobs, "hidden")
        self.query_one(QueueTable).update_snapshot(snapshot)
        self.query_one("#queue-summary", Static).update(_counts_line(snapshot))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide the save-file fetch unless this is a self-hosted server queue (§3)."""
        if action == "fetch_save_file" and not self._vm.is_server_queue:
            return None
        return True

    async def action_cancel(self) -> None:
        job = self._focused_job()
        if job is None:
            return
        result = await self._vm.cancel(job.job_id)
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        self.snapshot = self._vm.apply_job(self.snapshot, result.data)

    def action_fetch_save_file(self) -> None:
        """Surface the focused job's batch ``.spotdl`` server URL (self-hosted, §3)."""
        job = self._focused_job()
        if job is None:
            return
        self.notify(f"save file: {self._vm.save_file_url(job.batch_id)}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        event.input.value = ""
        result = await self._vm.enqueue(query)
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        self.notify(f"queued {result.data.job_count}")

    def _focused_job(self) -> JobRow | None:
        table = self.query_one(QueueTable)
        index = table.cursor_row
        if not 0 <= index < table.row_count:
            return None
        key = table.coordinate_to_cell_key(Coordinate(index, 0)).row_key.value
        if key is None or key.startswith("batch:"):
            return None  # a group-header row is focused, not a job
        return next((job for job in self.snapshot.jobs if str(job.job_id) == key), None)

    def _actions_line(self) -> str:
        actions = ["[x] cancel job"]
        if self._vm.is_server_queue:
            actions.append("[f] fetch save file")
        return "   ·   ".join(actions)


def _counts_line(snapshot: QueueSnapshot) -> str:
    queued = sum(1 for job in snapshot.jobs if job.status == "queued")
    chips = "  ·  ".join(
        (
            f"active {snapshot.active}",
            f"queued {queued}",
            f"completed {snapshot.completed}",
            f"failed {snapshot.failed}",
            f"skipped {snapshot.skipped}",
            f"cancelled {snapshot.cancelled}",
        )
    )
    return f"{_overall_bar(snapshot.overall_percent)}  {chips}"


def _overall_bar(percent: int) -> str:
    return f"{segmented_meter(percent / 100, _BAR_WIDTH)} {percent:3d}%"
