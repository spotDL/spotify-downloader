"""Admin dashboard screen for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from spotdl_cli.core import APIError, get_api_client

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class AdminScreen(Screen[None]):
    """Admin dashboard screen."""

    TITLE = "Admin Dashboard"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._stats: dict[str, Any] = {}
        self._matches: list[dict[str, Any]] = []
        self._reports: list[dict[str, Any]] = []
        self._users: list[dict[str, Any]] = []

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="admin-container"):
            yield Static("Admin Dashboard", classes="title")
            yield Static("Loading statistics...", id="admin-status", classes="status-muted mb-2")

            with TabbedContent(id="admin-tabs"):
                with TabPane("Dashboard", id="tab-dashboard"):
                    yield self._compose_dashboard()
                with TabPane("Matches", id="tab-matches"):
                    yield self._compose_matches()
                with TabPane("Reports", id="tab-reports"):
                    yield self._compose_reports()
                with TabPane("Users", id="tab-users"):
                    yield self._compose_users()

    def _compose_dashboard(self) -> Vertical:
        return Vertical(
            Horizontal(
                Vertical(
                    Static("Users", classes="stat-label"),
                    Static("0", id="stat-users-total", classes="stat-value"),
                    classes="stat-box card",
                ),
                Vertical(
                    Static("Admins", classes="stat-label"),
                    Static("0", id="stat-admins-total", classes="stat-value"),
                    classes="stat-box card",
                ),
                Vertical(
                    Static("Reports", classes="stat-label"),
                    Static("0", id="stat-reports-total", classes="stat-value"),
                    classes="stat-box card",
                ),
                Vertical(
                    Static("Pending Matches", classes="stat-label"),
                    Static("0", id="stat-matches-pending", classes="stat-value"),
                    classes="stat-box card",
                ),
                id="admin-stats-grid",
                classes="stats-grid mb-2",
            ),
            id="dashboard-content"
        )

    def _compose_matches(self) -> Vertical:
        return Vertical(
            Horizontal(
                Button("Refresh", id="btn-matches-refresh", variant="primary"),
                Button("Approve Selected", id="btn-matches-approve", variant="success"),
                Button("Reject Selected", id="btn-matches-reject", variant="error"),
                classes="admin-actions-row mb-2",
            ),
            DataTable(id="table-matches", cursor_type="row"),
            id="matches-content",
            classes="card"
        )

    def _compose_reports(self) -> Vertical:
        return Vertical(
            Horizontal(
                Button("Refresh", id="btn-reports-refresh", variant="primary"),
                Button("Resolve Selected", id="btn-reports-resolve", variant="success"),
                Button("Dismiss Selected", id="btn-reports-dismiss", variant="error"),
                classes="admin-actions-row mb-2",
            ),
            DataTable(id="table-reports", cursor_type="row"),
            id="reports-content",
            classes="card"
        )

    def _compose_users(self) -> Vertical:
        return Vertical(
            Horizontal(
                Button("Refresh", id="btn-users-refresh", variant="primary"),
                Button("Toggle Admin", id="btn-users-admin", variant="warning"),
                Button("Toggle Ban", id="btn-users-ban", variant="error"),
                classes="admin-actions-row mb-2",
            ),
            DataTable(id="table-users", cursor_type="row"),
            id="users-content",
            classes="card"
        )

    async def on_mount(self) -> None:
        """Handle screen mount."""
        self._setup_tables()
        self.run_worker(self._load_all_data())

    def _setup_tables(self) -> None:
        matches_table = self.query_one("#table-matches", DataTable)
        matches_table.add_columns("ID", "Type", "Source", "Target", "Status", "Score", "User")
        
        reports_table = self.query_one("#table-reports", DataTable)
        reports_table.add_columns("ID", "Type", "Entity", "Reason", "Status", "User")

        users_table = self.query_one("#table-users", DataTable)
        users_table.add_columns("ID", "Username", "Role", "Joined", "Status")

    async def _load_all_data(self, refresh: bool = False) -> None:
        """Load all admin data."""
        status = self.query_one("#admin-status", Static)
        status.update("[dim]Loading admin data...[/]")

        try:
            api_client = get_api_client()

            # Load stats
            self._stats = await api_client.get_admin_stats()
            self._update_dashboard()

            # Load lists
            matches_data = await api_client.get_admin_matches(status="pending", limit=100)
            self._matches = matches_data.get("matches", [])
            self._update_matches_table()

            reports_data = await api_client.get_admin_reports(status="open", limit=100)
            self._reports = reports_data.get("reports", [])
            self._update_reports_table()

            users_data = await api_client.get_admin_users(limit=100)
            self._users = users_data.get("users", [])
            self._update_users_table()

            status.update("[green]Data loaded successfully[/]")
            if refresh:
                self.notify("Admin data refreshed")
        except APIError as e:
            logger.error(f"Failed to load admin data: {e}")
            status.update(f"[red]Error loading data: {e}[/]")
            self.notify(str(e), severity="error")

    def _update_dashboard(self) -> None:
        """Update dashboard stats."""
        users_stat = self._stats.get("users", {})
        reports_stat = self._stats.get("reports", {})
        matches_stat = self._stats.get("matches", {})

        self.query_one("#stat-users-total", Static).update(str(users_stat.get("total", 0)))
        self.query_one("#stat-admins-total", Static).update(str(users_stat.get("admins", 0)))
        self.query_one("#stat-reports-total", Static).update(str(reports_stat.get("open", 0)))
        self.query_one("#stat-matches-pending", Static).update(str(matches_stat.get("pending", 0)))

    def _update_matches_table(self) -> None:
        table = self.query_one("#table-matches", DataTable)
        table.clear()
        for match in self._matches:
            match_id = str(match.get("id"))[:8]
            mtype = str(match.get("match_type", "system"))
            source = str(match.get("source_url", ""))[:30]
            target = str(match.get("target_url", ""))[:30]
            status = str(match.get("status", "pending"))
            score = f"{match.get('score', 0):.2f}"
            user_id = str(match.get("user_id", "system"))[:8]
            
            table.add_row(match_id, mtype, source, target, status, score, user_id)

    def _update_reports_table(self) -> None:
        table = self.query_one("#table-reports", DataTable)
        table.clear()
        for report in self._reports:
            report_id = str(report.get("id"))[:8]
            rtype = str(report.get("entity_type", ""))
            entity_id = str(report.get("entity_id", ""))[:8]
            reason = str(report.get("reason", "unknown"))
            status = str(report.get("status", "open"))
            user_id = str(report.get("user_id", "anonymous"))[:8]

            table.add_row(report_id, rtype, entity_id, reason, status, user_id)

    def _update_users_table(self) -> None:
        table = self.query_one("#table-users", DataTable)
        table.clear()
        for user in self._users:
            user_id = str(user.get("id"))[:8]
            username = str(user.get("username", ""))
            role = "Admin" if user.get("is_admin") else "User"
            joined = str(user.get("created_at", ""))[:10]
            status = "Banned" if user.get("is_banned") else "Active"

            table.add_row(user_id, username, role, joined, status)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id
        
        if btn_id == "btn-matches-refresh":
            self.run_worker(self._load_all_data(refresh=True))
        elif btn_id == "btn-matches-approve":
            self.run_worker(self._handle_match_action("approve"))
        elif btn_id == "btn-matches-reject":
            self.run_worker(self._handle_match_action("reject"))
            
        elif btn_id == "btn-reports-refresh":
            self.run_worker(self._load_all_data(refresh=True))
        elif btn_id == "btn-reports-resolve":
            self.run_worker(self._handle_report_action("resolved"))
        elif btn_id == "btn-reports-dismiss":
            self.run_worker(self._handle_report_action("dismissed"))
            
        elif btn_id == "btn-users-refresh":
            self.run_worker(self._load_all_data(refresh=True))
        elif btn_id == "btn-users-admin":
            self.run_worker(self._handle_user_admin_toggle())
        elif btn_id == "btn-users-ban":
            self.run_worker(self._handle_user_ban_toggle())

    async def _handle_match_action(self, action: str) -> None:
        table = self.query_one("#table-matches", DataTable)
        
        if table.cursor_row is None or table.cursor_row >= len(self._matches):
            self.notify("No match selected", severity="warning")
            return
            
        match = self._matches[table.cursor_row]
        match_id = match.get("id")
        
        try:
            api_client = get_api_client()
            if action == "approve":
                await api_client.approve_match(match_id)
            else:
                await api_client.reject_match(match_id)
                
            self.notify(f"Match {action}d successfully")
            await self._load_all_data() # Refresh lists
        except APIError as e:
            self.notify(f"Failed to {action} match: {e}", severity="error")

    async def _handle_report_action(self, action: str) -> None:
        table = self.query_one("#table-reports", DataTable)
        
        if table.cursor_row is None or table.cursor_row >= len(self._reports):
            self.notify("No report selected", severity="warning")
            return
            
        report = self._reports[table.cursor_row]
        report_id = report.get("id")
        
        try:
            api_client = get_api_client()
            await api_client.resolve_report(report_id, action)
            self.notify(f"Report marked as {action}")
            await self._load_all_data()
        except APIError as e:
            self.notify(f"Failed to update report: {e}", severity="error")

    async def _handle_user_admin_toggle(self) -> None:
        table = self.query_one("#table-users", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._users):
            self.notify("No user selected", severity="warning")
            return
            
        user = self._users[table.cursor_row]
        user_id = user.get("id")
        current_admin = user.get("is_admin", False)
        
        try:
            api_client = get_api_client()
            await api_client.update_user_role(user_id, not current_admin)
            self.notify(f"User role updated to {'Admin' if not current_admin else 'User'}")
            await self._load_all_data()
        except APIError as e:
            self.notify(f"Failed to update user role: {e}", severity="error")

    async def _handle_user_ban_toggle(self) -> None:
        table = self.query_one("#table-users", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._users):
            self.notify("No user selected", severity="warning")
            return
            
        user = self._users[table.cursor_row]
        user_id = user.get("id")
        is_banned = user.get("is_banned", False)
        
        try:
            api_client = get_api_client()
            await api_client.ban_user(user_id, "Toggled from CLI")
            self.notify("User ban toggled")
            await self._load_all_data()
        except APIError as e:
            self.notify(f"Failed to toggle ban: {e}", severity="error")

    def action_refresh_data(self) -> None:
        """Refresh data action."""
        self.run_worker(self._load_all_data(refresh=True))
