"""Login screen for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from spotdl_cli.core import APIError, get_api_client

logger = logging.getLogger(__name__)


class LoginScreen(Screen[bool]):
    """Login screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Login"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the login screen."""
        with Center(id="login-container"):
            with Vertical(id="login-form", classes="card"):
                yield Static("spotdl", classes="title-lg text-center")
                yield Static(
                    "Sign In",
                    classes="subtitle text-center mb-2",
                )

                yield Input(
                    placeholder="Username",
                    id="username-input",
                )
                yield Input(
                    placeholder="Password",
                    password=True,
                    id="password-input",
                )

                yield Static("", id="login-error", classes="error-alert hidden")
                yield Button("Sign In", id="login-btn", variant="primary", classes="w-full")
                yield Button("Register", id="register-btn", variant="default", classes="w-full")

                yield Static(
                    "Don't have an account? Click Register above",
                    classes="text-muted text-center mt-2 text-sm",
                )

    def on_mount(self) -> None:
        """Focus username input on mount."""
        self.query_one("#username-input").focus()

    async def _on_register_complete(self, success: bool) -> None:
        """Handle registration completion."""
        if success:
            self.notify("Account created! You are now logged in.")
            self.dismiss(True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "login-btn":
            await self._login()
        elif event.button.id == "register-btn":
            from spotdl_cli.screens.register import RegisterScreen
            await self.app.push_screen(RegisterScreen(), self._on_register_complete)

    async def action_submit(self) -> None:
        """Handle enter key."""
        await self._login()

    async def _login(self) -> None:
        """Perform login."""
        username = self.query_one("#username-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value.strip()
        error_widget = self.query_one("#login-error", Static)
        login_btn = self.query_one("#login-btn", Button)

        if not username or not password:
            error_widget.update("Please enter username and password")
            error_widget.remove_class("hidden")
            return

        # Loading state
        error_widget.add_class("hidden")
        login_btn.disabled = True
        login_btn.label = "Signing in..."

        try:
            api_client = get_api_client()
            await api_client.login(username, password)
            self.notify("Login successful")
            self.dismiss(True)
        except APIError as e:
            error_widget.update(str(e))
            error_widget.remove_class("hidden")
        finally:
            login_btn.disabled = False
            login_btn.label = "Sign In"
