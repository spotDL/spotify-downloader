"""``AdminScreen`` — the admin console: Stats / Reports / Users tabs (§4).

Three tabs over ``AdminViewModel``: **Stats** is a grid of :class:`StatCard`s,
**Reports** is the pending-review queue (``a``/``x`` approve/reject the focused row,
each via an optional-note prompt modal), and **Users** is a read-only paginated roster
(web parity). The section is only reachable when ``session.is_admin`` — the shell hides
it otherwise (CONTRACT F) — and every ``AdminViewModel`` method refuses defensively
even so, so a stray call can never hit an admin endpoint as a non-admin.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static, TabbedContent, TabPane
from textual.widgets.data_table import ColumnKey

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.patterns import LoadingPane, StatCard
from spotdl_cli.viewmodels.admin import AdminViewModel
from spotdl_cli.viewmodels.base import Loadable, LoadState
from spotdl_cli.viewmodels.types import ReportRow, StatsRow, UsersPage

_PAGE_SIZE = 20


class NotePromptModal(ModalScreen[str | None]):
    """Prompt for an optional review note; dismiss ``None`` to cancel the action."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, action: str) -> None:
        super().__init__()
        self._action = action

    def compose(self) -> ComposeResult:
        with Vertical(id="note-panel"):
            yield Static(f"{self._action} report — add a note (optional):", classes="note-prompt")
            yield Input(placeholder="note", id="note-input")
            with Horizontal(id="note-actions"):
                yield Button(self._action, id="note-submit", variant="primary")
                yield Button("Cancel", id="note-cancel")

    def on_mount(self) -> None:
        self.query_one("#note-panel").border_title = f"{self._action} report"
        self.query_one("#note-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "note-submit":
            self.dismiss(self.query_one("#note-input", Input).value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AdminScreen(SpotdlScreen):
    """Stats / Reports / Users tabs; report review runs through the note modal."""

    BINDINGS = [
        Binding("a", "approve", "Approve"),
        Binding("x", "reject", "Reject"),
    ]

    def __init__(self) -> None:
        super().__init__(name="admin")
        self._users_offset = 0

    def compose_content(self) -> ComposeResult:
        self._vm: AdminViewModel = self.vm_factory.admin()
        with TabbedContent(id="admin-tabs"):
            with TabPane("Stats", id="tab-stats"):
                with Horizontal(id="admin-stats-grid"):
                    yield LoadingPane("Loading stats…")
            with TabPane("Reports", id="tab-reports"):
                yield DataTable(id="admin-reports", cursor_type="row", zebra_stripes=True)
            with TabPane("Users", id="tab-users"):
                yield DataTable(id="admin-users", cursor_type="row", zebra_stripes=True)
                with Horizontal(id="admin-users-nav"):
                    yield Button("‹ Prev", id="users-prev")
                    yield Static("", id="users-count", classes="users-count")
                    yield Button("Next ›", id="users-next")

    def on_mount(self) -> None:
        super().on_mount()
        reports = self.query_one("#admin-reports", DataTable)
        self._status_col: ColumnKey = reports.add_columns("subject", "reason", "status")[2]
        self.query_one("#admin-users", DataTable).add_columns("user", "email", "role", "status")
        self._load_stats()
        self._load_reports()
        self._load_users()

    # -- Stats ----------------------------------------------------------------

    @work(group="admin-stats")
    async def _load_stats(self) -> None:
        result = await self._vm.stats()
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        grid = self.query_one("#admin-stats-grid", Horizontal)
        await grid.remove_children()
        await grid.mount(*_stat_cards(result.data))

    # -- Reports --------------------------------------------------------------

    @work(group="admin-reports")
    async def _load_reports(self) -> None:
        result = await self._vm.load_reports()
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        table = self.query_one("#admin-reports", DataTable)
        table.clear()
        for report in result.data or ():
            table.add_row(
                report.subject_type, report.reason or "", report.status, key=str(report.id)
            )

    def action_approve(self) -> None:
        self._review("Approve", self._vm.approve)

    def action_reject(self) -> None:
        self._review("Reject", self._vm.reject)

    @work(group="admin-review")
    async def _review(
        self, label: str, method: Callable[[UUID, str | None], Awaitable[Loadable[ReportRow]]]
    ) -> None:
        if self.query_one("#admin-tabs", TabbedContent).active != "tab-reports":
            return
        row_key = self._cursor_row()
        if row_key is None:
            return
        note = await self.app.push_screen_wait(NotePromptModal(label))
        if note is None:
            return  # cancelled — no client call
        result = await method(UUID(row_key), note or None)
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

    # -- Users ----------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "users-prev" and self._users_offset > 0:
            self._users_offset = max(0, self._users_offset - _PAGE_SIZE)
            self._load_users()
        elif event.button.id == "users-next":
            self._users_offset += _PAGE_SIZE
            self._load_users()

    @work(group="admin-users")
    async def _load_users(self) -> None:
        result = await self._vm.list_users(limit=_PAGE_SIZE, offset=self._users_offset)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self._render_users(result.data)

    def _render_users(self, page: UsersPage) -> None:
        table = self.query_one("#admin-users", DataTable)
        table.clear()
        for user in page.rows:
            role = "admin" if user.is_admin else "user"
            status = "active" if user.is_active else "inactive"
            table.add_row(user.name, user.email, role, status, key=str(user.id))
        start = page.offset + 1 if page.total else 0
        end = page.offset + len(page.rows)
        self.query_one("#users-count", Static).update(f"{start}–{end} of {page.total}")
        self.query_one("#users-prev", Button).disabled = page.offset == 0
        self.query_one("#users-next", Button).disabled = end >= page.total


def _stat_cards(stats: StatsRow) -> tuple[StatCard, ...]:
    return (
        StatCard("Users", stats.users),
        StatCard("Matches", stats.matches),
        StatCard("Pending reports", stats.pending_reports),
        StatCard("Matcher", stats.matcher_version),
    )
