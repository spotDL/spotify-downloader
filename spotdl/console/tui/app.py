"""
Main Textual application of the interactive interface.
"""

import os
import signal
from typing import List, Optional

from textual.app import App
from textual.screen import Screen

from spotdl._version import __version__
from spotdl.console.tui import i18n
from spotdl.console.tui.constants import SPOTDL_THEME
from spotdl.console.tui.css import CSS
from spotdl.console.tui.navigation import MenuPopover
from spotdl.console.tui.screens import HelpScreen, MainMenuScreen, QueryScreen
from spotdl.console.tui.setup_app import open_setup_screen, run_setup_ui
from spotdl.console.tui.state import AppState
from spotdl.utils.config import get_configured_data_dir
from spotdl.utils.deno import is_deno_installed
from spotdl.utils.ffmpeg import is_ffmpeg_installed

__all__ = ["SpotdlApp", "run_interactive"]


def _needs_first_run_setup() -> bool:
    if os.environ.get("SPOTDL_SKIP_AUTO_SETUP"):
        return False

    if get_configured_data_dir() is not None:
        return False

    return not is_ffmpeg_installed() or not is_deno_installed()


class SpotdlApp(App):
    """
    Interactive interface for spotDL.

    ### Attributes
    - initial_query: Query passed on the command line, opened on start.
    - state: Shared state with the Spotify client and the downloader.
    """

    TITLE = f"spotDL {__version__}"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False
    HORIZONTAL_BREAKPOINTS = [(0, "-normal"), (80, "-wide"), (120, "-very-wide")]

    def __init__(self, query: Optional[List[str]] = None) -> None:
        """
        Create the application.

        ### Arguments
        - query: Query to open directly in the download screen.
        """

        super().__init__()
        self.initial_query = query or []
        self.state = AppState()
        self.register_theme(SPOTDL_THEME)
        self.theme = "spotdl"

    def get_default_screen(self) -> Screen:
        """
        Open the download screen when a query was given, the main menu otherwise.
        """

        if self.initial_query:
            return QueryScreen("download", prefill=self.initial_query[0])
        return MainMenuScreen()

    def action_open_menu(self) -> None:
        """
        Open the application menu.
        """

        self.push_screen(MenuPopover())

    def action_open_help(self, tab: str = "help-reference") -> None:
        """
        Open the help screen.

        ### Arguments
        - tab: Id of the tab shown first.
        """

        self.push_screen(HelpScreen(initial_tab=tab))

    def action_open_setup(self) -> None:
        """
        Open the dependency setup wizard.
        """

        open_setup_screen(self)


def run_interactive(query: Optional[List[str]] = None) -> None:
    """
    Start the interactive interface, running the setup first when needed.

    ### Arguments
    - query: Query to open directly in the download screen.
    """

    i18n.init()
    if _needs_first_run_setup():
        run_setup_ui(get_configured_data_dir())

    app = SpotdlApp(query=query)

    def _handle_signal(_signum, _frame) -> None:
        app.exit()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app.run()
