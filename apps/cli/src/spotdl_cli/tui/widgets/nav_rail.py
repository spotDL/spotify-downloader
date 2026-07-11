"""``NavRail`` — the fixed left sidebar: sections + connection block (CONTRACT §1).

The persistent 22-column rail every screen mounts. It lists the reachable sections
(icon + key + name, the active one accent-barred), and pins a connection block to
the bottom: the transport label with a colour-coded dot (green ok / yellow degraded
/ red unreachable). It is presentation-only — it reads the app's session and
connection state and posts :class:`NavSelected` when an entry is clicked; the app
owns all routing and gating (a gated-off section is simply absent, never greyed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.widgets import Static

from spotdl_cli.tui.messages import NavSelected
from spotdl_cli.tui.theme import ERROR, FAINT, SUCCESS, WARNING

if TYPE_CHECKING:
    from spotdl_cli.tui.app import Section, SpotdlApp
    from spotdl_cli.viewmodels.app_state import SessionSnapshot

# transport-reachability → dot class + palette colour (degraded is folded in from
# the session on top of an "ok" transport, so it is not one of these).
_DOT: dict[str, tuple[str, str]] = {
    "ok": ("nav-dot--ok", SUCCESS),
    "degraded": ("nav-dot--degraded", WARNING),
    "unreachable": ("nav-dot--unreachable", ERROR),
    "connecting": ("nav-dot--connecting", FAINT),
}


class _NavEntry(Static):
    """One clickable section row (``key  name``); the active one is accent-barred."""

    def __init__(self, section: Section, *, active: bool) -> None:
        super().__init__(f"{section.icon}  {section.key}  {section.name}", classes="nav-entry")
        self._section_name = section.name
        if active:
            self.add_class("nav-entry--active")

    def on_click(self) -> None:
        self.post_message(NavSelected(self._section_name))


class _ConnectionBlock(Static):
    """The pinned bottom block: a colour-coded dot + the transport label (§1)."""

    def render_state(self, state: str, label: str) -> None:
        dot_class, colour = _DOT.get(state, _DOT["connecting"])
        for name, _ in _DOT.values():
            self.remove_class(name)
        self.add_class(dot_class)
        self._summary = f"● {label}"
        self.update(f"[{colour}]●[/]  {label}")

    @property
    def summary(self) -> str:
        return getattr(self, "_summary", "")


class NavRail(Static):
    """The left navigation rail; refreshed by the app on session/connection change."""

    def compose(self) -> ComposeResult:
        yield Static("spotDL", classes="nav-title")
        for section in self._app.available_sections():
            yield _NavEntry(section, active=section.name == self._active_name())
        yield Static(classes="nav-spacer")
        yield _ConnectionBlock(classes="nav-conn")

    def on_mount(self) -> None:
        self._paint_connection()

    async def refresh_rail(self) -> None:
        """Rebuild entries (availability/active changed) and repaint the dot."""
        await self.remove_children()
        await self.mount(Static("spotDL", classes="nav-title"))
        for section in self._app.available_sections():
            await self.mount(_NavEntry(section, active=section.name == self._active_name()))
        await self.mount(Static(classes="nav-spacer"), _ConnectionBlock(classes="nav-conn"))
        self._paint_connection()

    def paint_connection(self) -> None:
        """Repaint only the connection dot/label (session or reachability changed)."""
        self._paint_connection()

    # -- internals --

    @property
    def _app(self) -> SpotdlApp:
        return cast("SpotdlApp", self.app)

    def _active_name(self) -> str:
        return self._app.current_mode

    def _paint_connection(self) -> None:
        blocks = list(self.query(_ConnectionBlock))
        if not blocks:
            return
        state, label = _connection_view(self._app.session, self._app.connection_state)
        blocks[0].render_state(state, label)

    @property
    def connection_summary(self) -> str:
        blocks = list(self.query(_ConnectionBlock))
        return blocks[0].summary if blocks else ""

    @property
    def dot_state(self) -> str:
        """The current connection dot: ok / degraded / unreachable / connecting."""
        state, _ = _connection_view(self._app.session, self._app.connection_state)
        return state


def _connection_view(session: SessionSnapshot | None, transport_state: str) -> tuple[str, str]:
    """Fold session-degraded over transport reachability into (dot state, label)."""
    if session is None:
        return "unreachable" if transport_state == "unreachable" else "connecting", "connecting…"
    if transport_state == "unreachable":
        return "unreachable", session.transport_label
    if session.degraded or transport_state == "degraded":
        return "degraded", session.transport_label
    return "ok", session.transport_label
