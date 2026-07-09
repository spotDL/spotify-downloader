"""``AuthScreen`` — the Account card: sign-in / register / PAT management (§4).

A single centred card (≤70 cols) whose contents follow the identity resolved by
``AuthViewModel.status``: signed-out shows email + password with [Sign in] [Register],
a community blurb, and a note that OAuth lives in the web app (deliberate non-goal
§6); signed-in shows the profile (email + admin badge), the masked PAT with [Rotate
token] [Revoke token], and [Sign out]. When ``session.can_auth`` is False the card is
the copy-locked ``OFFLINE_AUTH_MESSAGE``. Each action delegates to ``AuthViewModel``
and, on an identity change, posts :class:`AuthChanged` so ``SpotdlApp`` re-runs
``AppStateViewModel.refresh_auth`` — repainting the status bar and re-gating sections.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Static

from spotdl_cli.tui.messages import AuthChanged
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.auth import OFFLINE_AUTH_MESSAGE, AuthViewModel
from spotdl_cli.viewmodels.base import Loadable, LoadState
from spotdl_cli.viewmodels.types import AuthSnapshot

_BLURB = (
    "Sign in to vote on matches and lyrics. New here? Register a free account — "
    "anonymous search and local downloads work without one."
)
_OAUTH_NOTE = (
    "OAuth sign-in (Google, GitHub) lives in the web app; this terminal uses email + password."
)


class AuthScreen(SpotdlScreen):
    """Identity + PAT management card; all auth logic lives in ``AuthViewModel``."""

    def compose_content(self) -> ComposeResult:
        self._vm: AuthViewModel = self.vm_factory.auth()
        yield Vertical(id="auth-slot")

    def on_mount(self) -> None:
        super().on_mount()
        self.run_worker(self._build(), exclusive=True)

    async def _build(self) -> None:
        """(Re)build the card from the current identity — the one source of truth."""
        slot = self.query_one("#auth-slot", Vertical)
        await slot.remove_children()
        session = self.spotdl_app.session
        if session is None or not session.can_auth:
            await slot.mount(
                Static(OFFLINE_AUTH_MESSAGE, id="auth-offline", classes="auth-offline")
            )
            return
        result = await self._vm.status()
        snapshot = result.data
        # A transport failure reading identity still lets you attempt a sign-in.
        if result.state is LoadState.ERROR and result.error is not None:
            self.show_error(result.error)
        if snapshot is not None and snapshot.logged_in:
            card = self._signed_in_card(snapshot)
        else:
            card = self._signed_out_card()
        card.border_title = "Account"
        await slot.mount(card)

    def _signed_out_card(self) -> Widget:
        return Vertical(
            Static(_BLURB, classes="auth-blurb"),
            Input(placeholder="email", id="auth-email"),
            Input(placeholder="password", password=True, id="auth-password"),
            Horizontal(
                Button("Sign in", id="auth-login", variant="primary"),
                Button("Register", id="auth-register"),
                id="auth-buttons",
            ),
            Static(_OAUTH_NOTE, classes="auth-note"),
            id="auth-card",
            classes="panel auth-card",
        )

    def _signed_in_card(self, snapshot: AuthSnapshot) -> Widget:
        badge = "   ★ admin" if snapshot.is_admin else ""
        return Vertical(
            Static(f"Signed in as {snapshot.email}{badge}", id="auth-status"),
            Static(
                f"Access token   {snapshot.masked_token or '—'}",
                id="auth-pat",
                classes="auth-pat",
            ),
            Horizontal(
                Button("Rotate token", id="auth-rotate", variant="primary"),
                Button("Revoke token", id="auth-revoke", variant="error"),
                id="auth-pat-actions",
            ),
            Button("Sign out", id="auth-logout", variant="error"),
            id="auth-card",
            classes="panel auth-card",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-login":
            await self._authenticate(self._vm.login)
        elif event.button.id == "auth-register":
            await self._authenticate(self._vm.register)
        elif event.button.id == "auth-logout":
            await self._act(self._vm.logout(), identity_changed=True)
        elif event.button.id == "auth-revoke":
            await self._act(self._vm.revoke(), identity_changed=True)
        elif event.button.id == "auth-rotate":
            await self._act(self._vm.rotate(), identity_changed=False)

    async def _authenticate(
        self, method: Callable[[str, str], Awaitable[Loadable[AuthSnapshot]]]
    ) -> None:
        email = self.query_one("#auth-email", Input).value
        password = self.query_one("#auth-password", Input).value
        await self._act(method(email, password), identity_changed=True)

    async def _act(
        self, coro: Awaitable[Loadable[AuthSnapshot]], *, identity_changed: bool
    ) -> None:
        result = await coro
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        if identity_changed:
            self.post_message(AuthChanged())
        await self._build()
