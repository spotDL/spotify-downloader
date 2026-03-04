"""Main SpotDL CLI Textual application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

import textual_image.renderable  # noqa: F401 — must import before App starts for terminal detection

from textual.app import App, ComposeResult
from textual.binding import Binding

from spotdl_cli import __version__
from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIClient,
    DownloadManager,
    DownloadQueue,
    get_api_client,
    get_image_service,
)
from spotdl_cli.core.backend import BackendState, get_backend_manager
from spotdl_cli.screens.account import AccountScreen
from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.onboarding import OnboardingScreen, should_show_onboarding
from spotdl_cli.screens.queue import QueueScreen
from spotdl_cli.screens.settings import SettingsScreen
from spotdl_cli.providers import SpotDLCommandProvider
from spotdl_cli.widgets import NavRail, StatusBar

if TYPE_CHECKING:
    from textual.screen import Screen

logger = logging.getLogger(__name__)


class SpotDLApp(App[None]):
    """SpotDL CLI - Interactive music downloader."""

    TITLE = "SpotDL"
    SUB_TITLE = f"v{__version__}"
    CSS_PATH = "app.tcss"

    COMMANDS = App.COMMANDS | {SpotDLCommandProvider}

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("s", "push_screen('search')", "Search", show=False),
        Binding("d", "push_screen('queue')", "Downloads", show=False),
        Binding("comma", "push_screen('settings')", "Settings", show=False),
        Binding("a", "push_screen('account')", "Account", show=False),
        Binding("ctrl+k", "command_palette", "Commands"),
        Binding("?", "toggle_help", "Help"),
        Binding("left_square_bracket", "toggle_nav", "Toggle Nav", show=False),
    ]

    SCREENS: ClassVar[dict[str, type[Screen[object]]]] = {
        "search": MainScreen,
        "queue": QueueScreen,
        "settings": SettingsScreen,
        "account": AccountScreen,
        "onboarding": OnboardingScreen,
    }

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._api_client: APIClient | None = None
        self._download_queue: DownloadQueue | None = None
        self._download_manager: DownloadManager | None = None
        self._is_online = False

    @property
    def api_client(self) -> APIClient:
        """Get the API client."""
        if self._api_client is None:
            self._api_client = get_api_client()
        return self._api_client

    @property
    def download_queue(self) -> DownloadQueue:
        """Get the download queue."""
        if self._download_queue is None:
            self._download_queue = DownloadQueue(
                max_concurrent=self._settings.threads,
            )
        return self._download_queue

    @property
    def download_manager(self) -> DownloadManager:
        """Get the download manager."""
        if self._download_manager is None:
            self._download_manager = DownloadManager(
                settings=self._settings,
                max_concurrent=self._settings.threads,
            )
        return self._download_manager

    @property
    def is_online(self) -> bool:
        """Check if connected to backend."""
        return self._is_online

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield NavRail(id="app-nav-rail")
        yield StatusBar(id="app-status-bar")

    async def on_mount(self) -> None:
        """Handle application mount."""
        status_bar = self.query_one("#app-status-bar", StatusBar)

        # Start local backend if configured
        manager = get_backend_manager()

        # Wire backend state changes to status bar
        def _on_backend_state(state: BackendState) -> None:
            try:
                status_bar.backend_state = state.value
            except Exception:
                pass

        manager.on_state_change(_on_backend_state)
        status_bar.backend_state = manager.state.value

        if not self._settings.offline_mode:
            try:
                await manager.start()
            except Exception as e:
                logger.warning(f"Failed to start local backend: {e}")

        # Check backend connectivity
        await self._check_connectivity()

        # Check if onboarding should be shown
        if should_show_onboarding():
            # Show onboarding first, then main screen
            await self.push_screen(OnboardingScreen(), self._on_onboarding_complete)
        else:
            # Push the main search screen directly
            await self.push_screen("search")

    async def _on_onboarding_complete(self, completed: bool) -> None:
        """Handle onboarding completion."""
        if completed:
            self.notify("Setup complete! Ready to download music.")
        # Push the main search screen
        await self.push_screen("search")

    async def _check_connectivity(self) -> None:
        """Check if backend is available."""
        status_bar = self.query_one("#app-status-bar", StatusBar)

        if self._settings.offline_mode:
            self._is_online = False
            status_bar.is_connected = False
            return

        try:
            self._is_online = await self.api_client.is_online()
            status_bar.is_connected = self._is_online
        except Exception as e:
            logger.warning(f"Failed to check connectivity: {e}")
            self._is_online = False
            status_bar.is_connected = False

    def on_screen_resume(self) -> None:
        """Update NavRail active state on screen changes."""
        try:
            nav = self.query_one("#app-nav-rail", NavRail)
            screen_name = self.screen.__class__.__name__
            name_map = {
                "MainScreen": "search",
                "QueueScreen": "queue",
                "SettingsScreen": "settings",
                "AccountScreen": "account",
            }
            if screen_name in name_map:
                nav.active_screen = name_map[screen_name]
        except Exception:
            pass

    def action_toggle_nav(self) -> None:
        """Toggle NavRail collapse."""
        try:
            nav = self.query_one("#app-nav-rail", NavRail)
            nav.toggle()
        except Exception:
            pass

    async def action_quit(self) -> None:
        """Quit the application."""
        # Cleanup
        if self._api_client:
            await self._api_client.close()
        if self._download_manager:
            await self._download_manager.close()

        # Close image service HTTP client
        image_service = get_image_service()
        await image_service.close()

        # Stop local backend
        manager = get_backend_manager()
        await manager.stop()

        self.exit()

    def action_toggle_help(self) -> None:
        """Toggle help display."""
        self.notify(
            "S: Search  D: Downloads  ,: Settings  A: Account  Ctrl+K: Commands  Q: Quit"
        )


def run() -> None:
    """Run the SpotDL CLI application."""
    app = SpotDLApp()
    app.run()


if __name__ == "__main__":
    run()
