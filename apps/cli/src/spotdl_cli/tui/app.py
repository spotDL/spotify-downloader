"""``SpotdlApp`` — the Textual shell: sections, theming, status bar, toasts (CONTRACT C/F/G).

Boot sequence: ``on_mount`` awaits ``AppStateViewModel.load`` for the one
:class:`SessionSnapshot`, hands it to the ``ViewModelFactory``, then installs a
Textual *mode* per reachable section (a section is hidden, never a per-request
error — CONTRACT F) and switches to Search. Each mode owns its own screen stack, so
drilling into an entity and ``escape``-ing back is scoped per section. Screens reach
the client only through ``vm_factory``; the app is their only channel to toasts
(``show_error``) and routing (``NavigateTo`` → :func:`router.open_entity`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive

from spotdl_cli.tui.messages import AuthChanged, NavigateTo
from spotdl_cli.tui.router import open_entity
from spotdl_cli.tui.screens.admin import AdminScreen
from spotdl_cli.tui.screens.auth import AuthScreen
from spotdl_cli.tui.screens.base import PlaceholderScreen, SpotdlScreen
from spotdl_cli.tui.screens.help import HelpScreen
from spotdl_cli.tui.screens.home import HomeSearchScreen
from spotdl_cli.tui.screens.settings import SettingsScreen
from spotdl_cli.tui.widgets.status_bar import StatusBar
from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, LoadState
from spotdl_cli.viewmodels.factory import ViewModelFactory


@dataclass(frozen=True, slots=True)
class Section:
    """A top-level, key-switchable area of the app.

    ``flag`` names the :class:`SessionSnapshot` boolean that gates it (``None`` for
    always-on Search/Settings); ``screen`` is the class shown, defaulting to a
    placeholder until the owning task registers the real one in ``SECTION_SCREENS``.
    """

    key: str
    name: str
    title: str
    flag: str | None


_SECTIONS: tuple[Section, ...] = (
    Section("1", "home", "Search", None),
    Section("2", "queue", "Queue", "can_download"),
    Section("3", "settings", "Settings", None),
    Section("4", "auth", "Account", "can_auth"),
    Section("5", "admin", "Admin", "is_admin"),
)

# section name -> screen class. Task 8 registers the queue screen; the rest are real.
SECTION_SCREENS: dict[str, type[SpotdlScreen]] = {
    "home": HomeSearchScreen,
    "settings": SettingsScreen,
    "auth": AuthScreen,
    "admin": AdminScreen,
}


class SpotdlApp(App[None]):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("1", "switch_section('home')", "Search"),
        Binding("2", "switch_section('queue')", "Queue"),
        Binding("3", "switch_section('settings')", "Settings"),
        Binding("4", "switch_section('auth')", "Account"),
        Binding("5", "switch_section('admin')", "Admin"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    session: reactive[SessionSnapshot | None] = reactive(None)

    def __init__(self, vm_factory: ViewModelFactory) -> None:
        super().__init__()
        self._vm_factory = vm_factory
        self._sections: dict[str, Section] = {}

    @property
    def vm_factory(self) -> ViewModelFactory:
        return self._vm_factory

    async def on_mount(self) -> None:
        loaded = await self._vm_factory.app_state().load()
        if loaded.state is LoadState.ERROR:
            # Boot degraded: still expose the always-on sections; toast the reason.
            if loaded.error is not None:
                self.show_error(loaded.error)
            self._install_sections(None)
        else:
            assert loaded.data is not None
            self._vm_factory.set_session(loaded.data)
            self.session = loaded.data
            self._install_sections(loaded.data)
        await self.switch_mode("home")

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
        """Repaint the current screen's status bar whenever the session changes."""
        if not self.is_running:
            return
        for bar in self.screen.query(StatusBar):
            bar.update_session(session)

    async def action_switch_section(self, name: str) -> None:
        """Switch to a section, or do nothing if it is gated off (CONTRACT F)."""
        if name in self._sections:
            await self.switch_mode(name)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def show_error(self, error: ErrorDisplay) -> None:
        """Raise a toast carrying a view-model ``ErrorDisplay`` (CONTRACT G)."""
        self.notify(error.message, severity=error.severity)

    def on_navigate_to(self, message: NavigateTo) -> None:
        open_entity(self, message.ref)

    async def on_auth_changed(self, message: AuthChanged) -> None:
        """Re-evaluate identity + section availability after a login/logout."""
        refreshed = await self._vm_factory.app_state().refresh_auth()
        if refreshed.state is LoadState.ERROR:
            if refreshed.error is not None:
                self.show_error(refreshed.error)
            return
        assert refreshed.data is not None
        self._vm_factory.set_session(refreshed.data)
        self.session = refreshed.data


def _available(section: Section, session: SessionSnapshot | None) -> bool:
    if section.flag is None:
        return True
    return session is not None and bool(getattr(session, section.flag))
