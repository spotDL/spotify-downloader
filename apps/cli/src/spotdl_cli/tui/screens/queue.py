"""``QueueScreen`` — the live download queue (CONTRACT C/E).

The CONTRACT E shape: a single background worker owns the WS code path. It seeds
from ``list_downloads``, then folds every frame the ``QueueViewModel.stream`` yields
into a reactive ``snapshot``; ``watch_snapshot`` repaints the :class:`QueueTable` and
the counts line. Nothing else touches the socket. ``x`` cancels the focused job (its
outcome is folded back through the same snapshot), and the enqueue ``Input`` submits
a pasted URL/query. Unmounting the screen cancels the worker (Textual ties node
workers to the DOM), so there is no leaked task.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Input, Static

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.queue_table import QueueTable
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.types import QueueSnapshot

_EMPTY = QueueSnapshot(
    jobs=(), overall_percent=0, active=0, completed=0, failed=0, skipped=0, cancelled=0
)


class QueueScreen(SpotdlScreen):
    """Live queue: enqueue input + a WS-driven job table + counts."""

    BINDINGS = [
        Binding("x", "cancel", "Cancel job"),
    ]

    snapshot: reactive[QueueSnapshot] = reactive(_EMPTY)

    def compose_content(self) -> ComposeResult:
        yield Input(placeholder="paste a Spotify URL or search query…", id="enqueue-input")
        yield Static(_counts_line(_EMPTY), id="queue-summary")
        yield QueueTable(id="queue-table")

    def on_mount(self) -> None:
        super().on_mount()
        # Focus the table so job bindings (``x``) reach the screen; the enqueue
        # input takes focus only when the user tabs/clicks into it.
        self.query_one(QueueTable).focus()
        self._vm = self.vm_factory.queue()
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
        self.query_one(QueueTable).update_snapshot(snapshot)
        self.query_one("#queue-summary", Static).update(_counts_line(snapshot))

    async def action_cancel(self) -> None:
        table = self.query_one(QueueTable)
        index = table.cursor_row
        if not 0 <= index < len(self.snapshot.jobs):
            return
        job = self.snapshot.jobs[index]
        result = await self._vm.cancel(job.job_id)
        if result.state is LoadState.ERROR:
            assert result.error is not None
            self.show_error(result.error)
            return
        assert result.data is not None
        self.snapshot = self._vm.apply_job(self.snapshot, result.data)

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


def _counts_line(snapshot: QueueSnapshot) -> str:
    return "  ·  ".join(
        (
            f"{snapshot.overall_percent}%",
            f"active {snapshot.active}",
            f"completed {snapshot.completed}",
            f"failed {snapshot.failed}",
            f"skipped {snapshot.skipped}",
            f"cancelled {snapshot.cancelled}",
        )
    )
