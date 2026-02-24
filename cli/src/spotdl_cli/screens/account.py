"""Account/Profile screen for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from spotdl_cli.config import get_settings
from spotdl_cli.core import APIError, get_api_client

logger = logging.getLogger(__name__)


class AccountScreen(Screen[None]):
    """Account and profile management screen."""

    TITLE = "Account"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._user_data: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the account screen."""
        with ScrollableContainer(id="account-scroll"):
            # Not logged in state
            with Vertical(id="not-logged-in", classes="card settings-group"):
                yield Static("Account", classes="settings-group-title")
                yield Static(
                    "You are not logged in. Sign in to view your profile, vote on matches, and submit contributions.",
                    classes="text-muted",
                )
                yield Button("Sign In", id="sign-in-btn", variant="primary")

            # Profile card
            with Vertical(id="profile-card", classes="card settings-group hidden"):
                yield Static("Profile", classes="settings-group-title")
                yield Static("", id="profile-username", classes="account-field")
                yield Static("", id="profile-email", classes="account-field")
                yield Static("", id="profile-role", classes="account-field")
                yield Static("", id="profile-member-since", classes="account-field")
                yield Static("", id="profile-status", classes="account-field")
                yield Button("Admin Dashboard", id="admin-dashboard-btn", variant="success", classes="hidden")

            # Reputation card
            with Vertical(id="reputation-card", classes="card settings-group hidden"):
                yield Static("Reputation", classes="settings-group-title")
                yield Static("0", id="reputation-score", classes="reputation-score")
                yield Static("Reputation Points", classes="text-muted text-center")
                yield Static(
                    "Earn points by submitting matches, voting, and contributing.",
                    classes="text-muted text-center text-sm",
                )

            # Security card
            with Vertical(id="security-card", classes="card settings-group hidden"):
                yield Static("Security", classes="settings-group-title")
                yield Input(
                    placeholder="Current Password",
                    password=True,
                    id="current-password",
                )
                yield Input(
                    placeholder="New Password",
                    password=True,
                    id="new-password",
                )
                yield Input(
                    placeholder="Confirm New Password",
                    password=True,
                    id="confirm-password",
                )
                yield Static("", id="password-error", classes="error-message hidden")
                yield Button(
                    "Update Password",
                    id="change-password-btn",
                    variant="primary",
                )

            # Session card
            with Vertical(id="session-card", classes="card settings-group hidden"):
                yield Static("Session", classes="settings-group-title")
                yield Static("", id="session-info", classes="account-field")
                yield Button("Log Out", id="logout-btn", variant="warning")

            # Danger zone card
            with Vertical(id="danger-zone-card", classes="card settings-group danger-zone hidden"):
                yield Static("Danger Zone", classes="settings-group-title")
                yield Static(
                    "Permanently delete your account and all associated data.",
                    classes="text-muted",
                )
                with Horizontal(id="delete-actions"):
                    yield Button(
                        "Delete Account",
                        id="delete-account-btn",
                        variant="error",
                    )
                    yield Button(
                        "Confirm Delete",
                        id="confirm-delete-btn",
                        variant="error",
                        classes="hidden",
                    )
                    yield Button(
                        "Cancel",
                        id="cancel-delete-btn",
                        classes="hidden",
                    )

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the parent SpotDL app."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    async def on_mount(self) -> None:
        """Load user data on mount."""
        try:
            is_online = self.spotdl_app.is_online
        except (AssertionError, AttributeError):
            is_online = True  # default to online behavior in test context
        if not is_online:
            self._show_offline()
            return
        settings = get_settings()
        if settings.auth_token:
            await self._load_profile()
        else:
            # Show not-logged-in state, hide authenticated cards
            self._show_unauthenticated()

    def _show_offline(self) -> None:
        """Show offline mode state - hide login prompt."""
        not_logged_in = self.query_one("#not-logged-in")
        not_logged_in.remove_class("hidden")
        # Update the description text (second Static, with text-muted class)
        desc = not_logged_in.query(".text-muted").first(Static)
        desc.update(
            "Account features are available when connected to a server. "
            "Switch to online mode in Settings to access your profile."
        )
        sign_in_btn = not_logged_in.query_one("#sign-in-btn", Button)
        sign_in_btn.add_class("hidden")
        for card_id in ["profile-card", "reputation-card", "security-card", "session-card", "danger-zone-card"]:
            self.query_one(f"#{card_id}").add_class("hidden")

    def _show_unauthenticated(self) -> None:
        """Show the not-logged-in state."""
        self.query_one("#not-logged-in").remove_class("hidden")
        for card_id in ["profile-card", "reputation-card", "security-card", "session-card", "danger-zone-card"]:
            self.query_one(f"#{card_id}").add_class("hidden")

    def _show_authenticated(self) -> None:
        """Show the authenticated state."""
        self.query_one("#not-logged-in").add_class("hidden")
        for card_id in ["profile-card", "reputation-card", "security-card", "session-card", "danger-zone-card"]:
            self.query_one(f"#{card_id}").remove_class("hidden")

    async def _load_profile(self) -> None:
        """Load user profile from API."""
        try:
            api_client = get_api_client()
            self._user_data = await api_client.get_me()
            self._show_authenticated()
            self._update_display()
        except (APIError, ConnectionError) as e:
            self.notify(f"Failed to load profile: {e}", severity="error")
            self._show_unauthenticated()

    def _update_display(self) -> None:
        """Update display with user data."""
        data = self._user_data
        if not data:
            return

        username = data.get("username", "Unknown")
        email = data.get("email", "")
        is_admin = data.get("is_admin", False)
        created_at = data.get("created_at", "")
        is_active = data.get("is_active", True)
        reputation = data.get("reputation", 0)

        self.query_one("#profile-username", Static).update(
            f"Username: {username}"
        )
        self.query_one("#profile-email", Static).update(
            f"Email: {email}" if email else "Email: Not set"
        )
        role_text = "Admin" if is_admin else "User"
        self.query_one("#profile-role", Static).update(f"Role: {role_text}")
        
        admin_btn = self.query_one("#admin-dashboard-btn", Button)
        if is_admin:
            admin_btn.remove_class("hidden")
        else:
            admin_btn.add_class("hidden")

        if created_at:
            date_str = created_at[:10] if len(created_at) >= 10 else created_at
            self.query_one("#profile-member-since", Static).update(
                f"Member since: {date_str}"
            )

        status_icon = "\u25cf" if is_active else "\u25cb"
        status_text = "Active" if is_active else "Inactive"
        self.query_one("#profile-status", Static).update(
            f"Status: {status_icon} {status_text}"
        )

        self.query_one("#reputation-score", Static).update(str(reputation))
        self.query_one("#session-info", Static).update(
            f"Signed in as {username}"
        )

    async def _on_login_complete(self, success: bool) -> None:
        """Handle login completion."""
        if success:
            await self._load_profile()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "sign-in-btn":
            from spotdl_cli.screens.login import LoginScreen
            await self.app.push_screen(LoginScreen(), self._on_login_complete)
        elif button_id == "admin-dashboard-btn":
            from spotdl_cli.screens.admin import AdminScreen
            await self.app.push_screen(AdminScreen())
        elif button_id == "change-password-btn":
            await self._change_password()
        elif button_id == "logout-btn":
            await self._logout()
        elif button_id == "delete-account-btn":
            self._show_delete_confirmation()
        elif button_id == "confirm-delete-btn":
            await self._delete_account()
        elif button_id == "cancel-delete-btn":
            self._hide_delete_confirmation()

    async def _change_password(self) -> None:
        """Change user password."""
        current = self.query_one("#current-password", Input).value.strip()
        new = self.query_one("#new-password", Input).value.strip()
        confirm = self.query_one("#confirm-password", Input).value.strip()
        error_widget = self.query_one("#password-error", Static)

        if not current or not new or not confirm:
            error_widget.update("All password fields are required")
            error_widget.remove_class("hidden")
            return

        if new != confirm:
            error_widget.update("New passwords do not match")
            error_widget.remove_class("hidden")
            return

        if len(new) < 8:
            error_widget.update("Password must be at least 8 characters")
            error_widget.remove_class("hidden")
            return

        error_widget.add_class("hidden")

        try:
            api_client = get_api_client()
            await api_client.change_password(current, new)
            self.notify("Password updated successfully")
            self.query_one("#current-password", Input).value = ""
            self.query_one("#new-password", Input).value = ""
            self.query_one("#confirm-password", Input).value = ""
        except APIError as e:
            error_widget.update(str(e))
            error_widget.remove_class("hidden")

    async def _logout(self) -> None:
        """Log out the user."""
        try:
            api_client = get_api_client()
            await api_client.logout()
            self.notify("Logged out successfully")
        except Exception as e:
            logger.warning(f"Logout error: {e}")
            self.notify("Logged out")
        self._user_data = {}
        self._show_unauthenticated()

    def _show_delete_confirmation(self) -> None:
        """Show the delete confirmation buttons."""
        self.query_one("#delete-account-btn").add_class("hidden")
        self.query_one("#confirm-delete-btn").remove_class("hidden")
        self.query_one("#cancel-delete-btn").remove_class("hidden")
        self.notify(
            "Are you sure? Click 'Confirm Delete' to permanently delete your account.",
            severity="warning",
        )

    def _hide_delete_confirmation(self) -> None:
        """Hide the delete confirmation buttons."""
        self.query_one("#delete-account-btn").remove_class("hidden")
        self.query_one("#confirm-delete-btn").add_class("hidden")
        self.query_one("#cancel-delete-btn").add_class("hidden")

    async def _delete_account(self) -> None:
        """Delete the user account."""
        try:
            api_client = get_api_client()
            await api_client.delete_account()
            self.notify("Account deleted")
            self._user_data = {}
            self._show_unauthenticated()
        except APIError as e:
            self.notify(f"Failed to delete account: {e}", severity="error")
            self._hide_delete_confirmation()
