"""``AuthScreen`` — PAT sign-in / register / logout over ``AuthViewModel`` (CONTRACT C/F).

Shows the current identity (guest or signed-in email) and a login form; each action
delegates to ``AuthViewModel`` (which runs the ``login/register → create_pat → store``
flow) and, on success, posts :class:`AuthChanged` so ``SpotdlApp`` re-runs
``AppStateViewModel.refresh_auth`` — repainting the status bar and re-evaluating which
feature sections are reachable. When ``session.can_auth`` is False the screen renders
the copy-locked ``OFFLINE_AUTH_MESSAGE`` and no form at all (spec §4).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from spotdl_cli.tui.messages import AuthChanged
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.auth import OFFLINE_AUTH_MESSAGE, AuthViewModel
from spotdl_cli.viewmodels.base import Loadable, LoadState
from spotdl_cli.viewmodels.types import AuthSnapshot


class AuthScreen(SpotdlScreen):
    """Identity + login form; all auth logic lives in ``AuthViewModel``."""

    def compose_content(self) -> ComposeResult:
        self._vm: AuthViewModel = self.vm_factory.auth()
        session = self.spotdl_app.session
        if session is None or not session.can_auth:
            yield Static(OFFLINE_AUTH_MESSAGE, id="auth-offline", classes="auth-offline")
            return
        yield Static(_identity_line(session.user_email), id="auth-status")
        yield Input(placeholder="email", id="auth-email")
        yield Input(placeholder="password", password=True, id="auth-password")
        yield Horizontal(
            Button("Login", id="auth-login"),
            Button("Register", id="auth-register"),
            Button("Logout", id="auth-logout"),
            id="auth-buttons",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-login":
            await self._authenticate(self._vm.login)
        elif event.button.id == "auth-register":
            await self._authenticate(self._vm.register)
        elif event.button.id == "auth-logout":
            self._apply(await self._vm.logout())

    async def _authenticate(
        self, method: Callable[[str, str], Awaitable[Loadable[AuthSnapshot]]]
    ) -> None:
        email = self.query_one("#auth-email", Input).value
        password = self.query_one("#auth-password", Input).value
        self._apply(await method(email, password))

    def _apply(self, result: Loadable[AuthSnapshot]) -> None:
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self.query_one("#auth-status", Static).update(_identity_line(result.data.email))
        self.post_message(AuthChanged())


def _identity_line(email: str | None) -> str:
    return f"Signed in as {email}" if email else "Guest"
