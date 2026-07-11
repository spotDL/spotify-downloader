"""``SpotdlApp`` — the Textual shell: nav rail, sections, connection, toasts (§1/§3).

Boot sequence: ``on_mount`` awaits ``AppStateViewModel.load`` for the one
:class:`SessionSnapshot`, hands it to the ``ViewModelFactory``, then installs a
Textual *mode* per reachable section (a section is hidden, never a per-request
error — CONTRACT F) and switches to Search (or Connect on first run). Each mode owns
its own screen stack, so drilling into an entity and ``escape``-ing back is scoped per
section. Every screen mounts a :class:`NavRail` (sections + connection dot) and reads
the client only through ``vm_factory``; the app is their only channel to toasts
(``show_error``), routing (``NavigateTo``), and connection switching (``rebuild_client``).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen

from spotdl_cli.tui.messages import (
    AuthChanged,
    ConnectionChanged,
    DegradedChanged,
    NavigateTo,
    NavSelected,
)
from spotdl_cli.tui.router import open_entity
from spotdl_cli.tui.screens.admin import AdminScreen
from spotdl_cli.tui.screens.auth import AuthScreen
from spotdl_cli.tui.screens.base import PlaceholderScreen, SpotdlScreen
from spotdl_cli.tui.screens.connect import ConnectScreen
from spotdl_cli.tui.screens.help import HelpScreen
from spotdl_cli.tui.screens.home import HomeSearchScreen
from spotdl_cli.tui.screens.library import LibraryScreen
from spotdl_cli.tui.screens.queue import QueueScreen
from spotdl_cli.tui.screens.settings import SettingsScreen
from spotdl_cli.tui.theme import SPOTDL_CONTROL_ROOM
from spotdl_cli.tui.widgets.nav_rail import NavRail
from spotdl_cli.tui.widgets.patterns import LoadingPane
from spotdl_cli.tui.widgets.status_bar import StatusBar
from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, LoadState
from spotdl_cli.viewmodels.factory import ViewModelFactory

# The app calls this to swap connection targets: (api_url, offline) -> a fresh
# factory over a rebuilt client. Lives in ``commands/tui.py`` (the sole client
# construction site); ``None`` in shell-only tests where switching is a no-op.
RebuildClient = Callable[[str, bool], Awaitable[ViewModelFactory]]


@dataclass(frozen=True, slots=True)
class Section:
    """A top-level, key-switchable area of the app (a nav-rail entry).

    ``flag`` names the :class:`SessionSnapshot` boolean that gates it (``None`` for
    always-on Connect/Search/Settings); ``icon`` + ``key`` render in the rail.
    """

    key: str
    name: str
    title: str
    flag: str | None
    icon: str


_SECTIONS: tuple[Section, ...] = (
    Section("0", "connect", "Connect", None, "◈"),
    Section("1", "home", "Search", None, "⌕"),
    Section("2", "queue", "Queue", "can_download", "▤"),
    Section("3", "library", "Library", "library", "▦"),
    Section("4", "settings", "Settings", None, "⚙"),
    Section("5", "auth", "Account", "can_auth", "◔"),
    Section("6", "admin", "Admin", "is_admin", "★"),
)

# section name -> screen class. All seven sections are registered.
SECTION_SCREENS: dict[str, type[SpotdlScreen]] = {
    "connect": ConnectScreen,
    "home": HomeSearchScreen,
    "queue": QueueScreen,
    "library": LibraryScreen,
    "settings": SettingsScreen,
    "auth": AuthScreen,
    "admin": AdminScreen,
}

# A permanent, hidden scratch mode: ``rebuild_client`` switches here so it can
# remove + re-add every *section* mode (you can't remove the active mode).
_RELOAD_MODE = "reloading"


class _ReloadingScreen(Screen[None]):
    """The transient screen shown while the client is rebuilt (no nav rail)."""

    def compose(self) -> ComposeResult:
        yield LoadingPane("Reconnecting…", id="reloading")


class SpotdlApp(App[None]):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("0", "switch_section('connect')", "Connect"),
        Binding("1", "switch_section('home')", "Search"),
        Binding("2", "switch_section('queue')", "Queue"),
        Binding("3", "switch_section('library')", "Library"),
        Binding("4", "switch_section('settings')", "Settings"),
        Binding("5", "switch_section('auth')", "Account"),
        Binding("6", "switch_section('admin')", "Admin"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    session: reactive[SessionSnapshot | None] = reactive(None)
    connection_state: reactive[str] = reactive("connecting")

    def __init__(
        self,
        vm_factory: ViewModelFactory,
        *,
        rebuild: RebuildClient | None = None,
        first_run: bool = False,
    ) -> None:
        super().__init__()
        self._vm_factory = vm_factory
        self._rebuild = rebuild
        self._first_run = first_run
        self._sections: dict[str, Section] = {}

    @property
    def vm_factory(self) -> ViewModelFactory:
        return self._vm_factory

    @property
    def fallback_active(self) -> bool:
        """True when a remote was requested but the embedded engine took over (§3).

        The seam the Search screen reads to render its remote-fallback banner.
        """
        return self.connection_state == "unreachable" and self.session is not None

    async def on_mount(self) -> None:
        # Recolour the whole app to the Control Room palette (spec: one palette,
        # two renderers). Registered + selected before any screen mounts so every
        # widget's semantic tokens resolve to the amber/blue-ink-black system.
        self.register_theme(SPOTDL_CONTROL_ROOM)
        self.theme = "spotdl-control-room"
        self.add_mode(_RELOAD_MODE, _ReloadingScreen)
        loaded = await self._vm_factory.app_state().load()
        self._adopt(loaded)
        target = "connect" if self._first_run else "home"
        await self.switch_mode(target if target in self._sections else "connect")

    def _adopt(self, loaded: Loadable[SessionSnapshot]) -> None:
        """Fold a fresh ``load`` result into session + connection state + sections."""
        if loaded.state is LoadState.ERROR:
            if loaded.error is not None:
                self.show_error(loaded.error)
            self.connection_state = "unreachable"
            self.session = None
            self._install_sections(None)
            return
        assert loaded.data is not None
        self._vm_factory.set_session(loaded.data)
        self.session = loaded.data
        self._install_sections(loaded.data)
        if "unreachable" in loaded.data.transport_label:
            self.connection_state = "unreachable"
            self.show_error(
                ErrorDisplay(
                    "Community server unreachable — using the offline embedded engine. "
                    "Press 0 to reconnect.",
                    code="remote_fallback",
                    severity="warning",
                )
            )
        else:
            self.connection_state = "ok"

    def available_sections(self) -> list[Section]:
        """The reachable sections in nav order (the rail iterates this)."""
        return [section for section in _SECTIONS if section.name in self._sections]

    def _install_sections(self, session: SessionSnapshot | None) -> None:
        for section in _SECTIONS:
            if not _available(section, session):
                continue
            self._sections[section.name] = section
            self.add_mode(section.name, self._section_screen_factory(section))

    def _section_screen_factory(self, section: Section) -> Callable[[], SpotdlScreen]:
        cls = SECTION_SCREENS.get(section.name)
        if cls is not None:
            return cls
        return lambda: PlaceholderScreen(section.name, section.title)

    def watch_session(self, session: SessionSnapshot | None) -> None:
        """Repaint the current screen's status bar + nav dot on any session change."""
        if not self.is_running:
            return
        for bar in self.screen.query(StatusBar):
            bar.update_session(session)
        for rail in self.screen.query(NavRail):
            rail.paint_connection()

    def watch_connection_state(self, state: str) -> None:
        if not self.is_running:
            return
        for rail in self.screen.query(NavRail):
            rail.paint_connection()

    async def action_switch_section(self, name: str) -> None:
        """Switch to a section, or do nothing if it is gated off (CONTRACT F)."""
        if name in self._sections:
            await self.switch_mode(name)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide a gated section's key from the footer entirely (CONTRACT F)."""
        if action == "switch_section":
            return not (parameters and parameters[0] not in self._sections)
        return True

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def show_error(self, error: ErrorDisplay) -> None:
        """Raise a toast carrying a view-model ``ErrorDisplay`` (CONTRACT G)."""
        self.notify(error.message, severity=error.severity)

    def on_nav_selected(self, message: NavSelected) -> None:
        self.call_later(self.action_switch_section, message.section)

    def on_navigate_to(self, message: NavigateTo) -> None:
        open_entity(self, message.ref)

    def on_degraded_changed(self, message: DegradedChanged) -> None:
        """Fold the latest search/resolve degraded state into the session badge."""
        session = self.session
        if session is None or session.degraded == message.degraded:
            return
        updated = replace(session, degraded=message.degraded)
        self._vm_factory.set_session(updated)
        self.session = updated

    async def on_auth_changed(self, message: AuthChanged) -> None:
        """Re-evaluate identity + reveal/hide feature sections after login/logout."""
        refreshed = await self._vm_factory.app_state().refresh_auth()
        if refreshed.state is LoadState.ERROR:
            if refreshed.error is not None:
                self.show_error(refreshed.error)
            return
        assert refreshed.data is not None
        self._vm_factory.set_session(refreshed.data)
        self.session = refreshed.data
        await self._sync_sections(refreshed.data)

    async def on_connection_changed(self, message: ConnectionChanged) -> None:
        await self.rebuild_client(message.api_url, message.offline)

    async def rebuild_client(self, api_url: str, offline: bool) -> None:
        """Swap the client for a new connection target and refresh every screen (§3)."""
        if self._rebuild is None:
            self.show_error(
                ErrorDisplay(
                    "connection switching is unavailable here", code=None, severity="warning"
                )
            )
            return
        self._vm_factory = await self._rebuild(api_url, offline)
        loaded = await self._vm_factory.app_state().load()
        await self.switch_mode(_RELOAD_MODE)
        for name in list(self._sections):
            self.remove_mode(name)
        self._sections.clear()
        self._adopt(loaded)
        await self.switch_mode("home" if "home" in self._sections else "connect")

    async def _sync_sections(self, session: SessionSnapshot) -> None:
        """Add newly-reachable sections + drop now-unreachable ones (login/logout)."""
        for name in list(self._sections):
            if not _available(self._sections[name], session) and name != self.current_mode:
                self.remove_mode(name)
                del self._sections[name]
        for section in _SECTIONS:
            if _available(section, session) and section.name not in self._sections:
                self._sections[section.name] = section
                self.add_mode(section.name, self._section_screen_factory(section))
        for rail in self.screen.query(NavRail):
            await rail.refresh_rail()


def _available(section: Section, session: SessionSnapshot | None) -> bool:
    if section.flag is None:
        return True
    return session is not None and bool(getattr(session, section.flag))
