"""``ConnectScreen`` — onboarding + the connection switcher (section 0, CONTRACT §3).

The first-run landing (no config file) and the anytime server switcher. It shows the
current target with a live ``/config`` probe (latency, mode, matcher version), and
three cards — community / self-hosted / offline — plus a jump to Account. Applying a
switch persists the target through :class:`ConnectionViewModel` and posts
:class:`ConnectionChanged`; the app rebuilds the client and refreshes every screen.
"""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static

from spotdl_cli.tui.messages import ConnectionChanged
from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.viewmodels.connection import ConnectionViewModel, ProbeResult, validate_self_hosted


class ConnectScreen(SpotdlScreen):
    def __init__(self) -> None:
        super().__init__(name="connect")

    def compose_content(self) -> ComposeResult:
        yield Static("probing…", id="connect-status", classes="connect-status")
        with Horizontal(id="connect-cards"):
            with Vertical(classes="connect-card", id="card-community"):
                yield Static(
                    "Anonymous search and local downloads on api.spotdl.dev. Sign in to vote.",
                    classes="card-blurb",
                )
                yield Button("Use community server", id="use-community", variant="primary")
            with Vertical(classes="connect-card", id="card-selfhost"):
                yield Static("Point spotDL at your own server.", classes="card-blurb")
                yield Input(placeholder="https://spotdl.example.com", id="selfhost-url")
                yield Static("", id="selfhost-error", classes="card-error")
                yield Button("Connect", id="use-selfhost")
            with Vertical(classes="connect-card", id="card-offline"):
                yield Static(
                    "No network. Metadata from local providers only.", classes="card-blurb"
                )
                yield Button("Go offline", id="use-offline")
        with Horizontal(id="connect-actions"):
            yield Button("Sign in / Account", id="go-account")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#card-community").border_title = "Community server"
        self.query_one("#card-selfhost").border_title = "Self-hosted server"
        self.query_one("#card-offline").border_title = "Offline"
        self.query_one("#connect-status").border_title = "Connection"
        if not getattr(self.spotdl_app.session, "can_auth", False):
            self.query_one("#go-account", Button).display = False
        self._render_status(None)
        self._probe()

    @work(exclusive=True, group="connect-probe")
    async def _probe(self) -> None:
        result = await self.vm_factory.connection().probe()
        self._render_status(result)
        if not result.reachable:
            # A hard failure lights the red dot; never downgrade an active
            # embedded-fallback ("ok" would mask that the remote is still down).
            self.spotdl_app.connection_state = "unreachable"

    def _render_status(self, result: ProbeResult | None) -> None:
        current = self.vm_factory.connection().current()
        target = "offline (embedded engine)" if current.offline else current.api_url
        lines = [f"Target: {target}"]
        if result is None:
            lines.append("probing…")
        elif result.reachable:
            lines.append(
                f"reachable · {result.latency_ms} ms · mode {result.mode} · "
                f"matcher {result.matcher_version}"
            )
        else:
            lines.append(f"unreachable — {result.reason}")
        self.query_one("#connect-status", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        vm = self.vm_factory.connection()
        if event.button.id == "use-community":
            self._apply(vm.switch_community())
        elif event.button.id == "use-offline":
            self._apply(vm.go_offline())
        elif event.button.id == "use-selfhost":
            self._connect_selfhost(vm)
        elif event.button.id == "go-account":
            self.app.call_later(self.spotdl_app.action_switch_section, "auth")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "selfhost-url":
            self._connect_selfhost(self.vm_factory.connection())

    def _connect_selfhost(self, vm: ConnectionViewModel) -> None:
        url = self.query_one("#selfhost-url", Input).value
        error = validate_self_hosted(url)
        if error is not None:
            self.query_one("#selfhost-error", Static).update(error)
            return
        self.query_one("#selfhost-error", Static).update("")
        self._apply(vm.switch_self_hosted(url))

    def _apply(self, target: tuple[str, bool]) -> None:
        api_url, offline = target
        self.post_message(ConnectionChanged(api_url=api_url, offline=offline))
