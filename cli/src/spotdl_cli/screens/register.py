"""Registration screen for SpotDL CLI."""

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


class RegisterScreen(Screen[bool]):
    """Registration screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Register"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the registration screen."""
        with Center(id="register-container"):
            with Vertical(id="register-form", classes="card"):
                yield Static("spotdl", classes="title-lg text-center")
                yield Static(
                    "Create Account",
                    classes="subtitle text-center mb-2",
                )

                yield Input(
                    placeholder="Username",
                    id="reg-username-input",
                )
                yield Input(
                    placeholder="Email",
                    id="reg-email-input",
                )
                yield Input(
                    placeholder="Password",
                    password=True,
                    id="reg-password-input",
                )
                yield Input(
                    placeholder="Confirm Password",
                    password=True,
                    id="reg-confirm-input",
                )

                yield Static("", id="register-error", classes="error-alert hidden")
                yield Button("Register", id="register-btn", variant="primary", classes="w-full")

                yield Static(
                    "Already have an account? Sign In",
                    id="register-login-link",
                    classes="text-muted text-center mt-2 text-sm",
                )

    def on_mount(self) -> None:
        """Focus username input on mount."""
        self.query_one("#reg-username-input").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "register-btn":
            await self._register()

    async def action_submit(self) -> None:
        """Handle enter key."""
        await self._register()

    async def _register(self) -> None:
        """Perform registration."""
        username = self.query_one("#reg-username-input", Input).value.strip()
        email = self.query_one("#reg-email-input", Input).value.strip()
        password = self.query_one("#reg-password-input", Input).value.strip()
        confirm = self.query_one("#reg-confirm-input", Input).value.strip()
        error_widget = self.query_one("#register-error", Static)
        register_btn = self.query_one("#register-btn", Button)

        # Validation
        if not username or not email or not password or not confirm:
            error_widget.update("All fields are required")
            error_widget.remove_class("hidden")
            return

        if password != confirm:
            error_widget.update("Passwords do not match")
            error_widget.remove_class("hidden")
            return

        # Loading state
        error_widget.add_class("hidden")
        register_btn.disabled = True
        register_btn.label = "Creating account..."

        try:
            api_client = get_api_client()
            await api_client.register(username, email, password)
            self.notify("Registration successful")
            self.dismiss(True)
        except APIError as e:
            error_widget.update(str(e))
            error_widget.remove_class("hidden")
        finally:
            register_btn.disabled = False
            register_btn.label = "Register"
