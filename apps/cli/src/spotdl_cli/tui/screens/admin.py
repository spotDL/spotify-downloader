"""``AdminScreen`` — the admin-lite reports queue + stats panel (CONTRACT C/F).

Lists pending reports from ``AdminViewModel.load_reports`` in a focusable table and
shows a ``StatsRow`` summary; ``a``/``x`` approve/reject the report under the cursor
(delegating to ``AdminViewModel``) and update its status cell in place. The section is
only reachable when ``session.is_admin`` — the shell hides it otherwise (CONTRACT F,
Task 4) — and the view-model refuses defensively even so, so a stray call can never
hit an admin endpoint as a non-admin.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Static
from textual.widgets.data_table import ColumnKey

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.admin import AdminViewModel
from spotdl_cli.viewmodels.base import Loadable, LoadState
from spotdl_cli.viewmodels.types import ReportRow, StatsRow


class AdminScreen(SpotdlScreen):
    """Reports queue + stats; approve/reject the focused row via the view-model."""

    BINDINGS = [
        Binding("a", "approve", "Approve"),
        Binding("x", "reject", "Reject"),
    ]

    def compose_content(self) -> ComposeResult:
        self._vm: AdminViewModel = self.vm_factory.admin()
        yield Static("", id="admin-stats", classes="admin-stats")
        yield DataTable(id="admin-reports", cursor_type="row")

    def on_mount(self) -> None:
        super().on_mount()
        table = self.query_one("#admin-reports", DataTable)
        self._status_col: ColumnKey = table.add_columns("subject", "reason", "status")[2]
        self.run_worker(self._refresh())

    async def _refresh(self) -> None:
        stats = await self._vm.stats()
        if stats.state is LoadState.ERROR:
            if stats.error is not None:
                self.show_error(stats.error)
        elif stats.data is not None:
            self.query_one("#admin-stats", Static).update(_stats_line(stats.data))

        reports = await self._vm.load_reports()
        if reports.state is LoadState.ERROR:
            if reports.error is not None:
                self.show_error(reports.error)
            return
        table = self.query_one("#admin-reports", DataTable)
        table.clear()
        for report in reports.data or ():
            table.add_row(
                report.subject_type, report.reason or "", report.status, key=str(report.id)
            )
        if table.row_count:
            table.focus()

    async def action_approve(self) -> None:
        await self._review(self._vm.approve)

    async def action_reject(self) -> None:
        await self._review(self._vm.reject)

    async def _review(
        self, method: Callable[[UUID, str | None], Awaitable[Loadable[ReportRow]]]
    ) -> None:
        row_key = self._cursor_row()
        if row_key is None:
            return
        result = await method(UUID(row_key), None)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self.query_one("#admin-reports", DataTable).update_cell(
            row_key, self._status_col, result.data.status
        )

    def _cursor_row(self) -> str | None:
        table = self.query_one("#admin-reports", DataTable)
        if not table.row_count:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value


def _stats_line(stats: StatsRow) -> str:
    return (
        f"users {stats.users}  ·  matches {stats.matches}  ·  "
        f"pending {stats.pending_reports}  ·  matcher {stats.matcher_version}"
    )
