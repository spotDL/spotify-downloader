"""StatusBar — Minimal bottom bar widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from spotdl_cli.theme import Theme


class StatusBar(Widget):
    """Minimal 1-line bottom bar replacing Header + Footer."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        width: 100%;
        background: #161819;
        color: #a8a8b3;
    }
    StatusBar #status-hints {
        width: 1fr;
        padding: 0 1;
    }
    StatusBar #status-backend {
        width: auto;
        padding: 0 2;
    }
    StatusBar #status-connection {
        width: auto;
        padding: 0 1;
    }
    """

    is_connected: reactive[bool] = reactive(False)
    hints: reactive[str] = reactive("S Search  D Downloads  , Settings  Q Quit")
    backend_state: reactive[str] = reactive("stopped")

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(self.hints, id="status-hints")
            yield Static("", id="status-backend")
            yield Static("", id="status-connection")

    def watch_is_connected(self, value: bool) -> None:
        conn = self.query_one("#status-connection", Static)
        if value:
            conn.update(f"[{Theme.SUCCESS}]{Theme.ICON_DOT}[/] Connected")
        else:
            conn.update(f"[{Theme.TEXT_MUTED}]{Theme.ICON_DOT}[/] Offline")

    def watch_hints(self, value: str) -> None:
        try:
            self.query_one("#status-hints", Static).update(value)
        except Exception:
            pass

    def watch_backend_state(self, value: str) -> None:
        try:
            backend = self.query_one("#status-backend", Static)
        except Exception:
            return

        state_display = {
            "stopped": (Theme.TEXT_MUTED, "Server stopped"),
            "starting": (Theme.WARNING, "Starting..."),
            "running": (Theme.SUCCESS, "Server running"),
            "stopping": (Theme.WARNING, "Stopping..."),
            "error": (Theme.ERROR, "Server error"),
        }
        color, label = state_display.get(value, (Theme.TEXT_MUTED, f"Server {value}"))
        backend.update(f"[{color}]{Theme.ICON_DOT}[/] {label}")
