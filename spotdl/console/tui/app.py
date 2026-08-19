import os
import signal
from typing import List, Optional

from textual.app import App
from textual.screen import Screen

from spotdl._version import __version__
from spotdl.console.tui import i18n
from spotdl.console.tui.constants import SPOTDL_THEME
from spotdl.console.tui.css import CSS
from spotdl.console.tui.screens import MainMenuScreen, QueryScreen
from spotdl.console.tui.state import AppState

__all__ = ["SpotdlApp", "run_interactive"]


def _needs_first_run_setup() -> bool:
    if os.environ.get("SPOTDL_SKIP_AUTO_SETUP"):
        return False

    from spotdl.utils.config import get_configured_data_dir
    from spotdl.utils.deno import is_deno_installed
    from spotdl.utils.ffmpeg import is_ffmpeg_installed

    if get_configured_data_dir() is not None:
        return False

    return not is_ffmpeg_installed() or not is_deno_installed()


def _maybe_run_first_run_setup() -> None:
    if not _needs_first_run_setup():
        return

    from spotdl.console.tui.setup_app import run_setup_ui
    from spotdl.utils.config import get_configured_data_dir

    run_setup_ui(get_configured_data_dir())


class SpotdlApp(App):
    TITLE = f"spotDL {__version__}"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False
    HORIZONTAL_BREAKPOINTS = [(0, "-normal"), (80, "-wide"), (120, "-very-wide")]

    def __init__(self, query: Optional[List[str]] = None) -> None:
        super().__init__()
        self.initial_query = query or []
        self.state = AppState()
        self.register_theme(SPOTDL_THEME)
        self.theme = "spotdl"

    def get_default_screen(self) -> Screen:
        if self.initial_query:
            return QueryScreen("download", prefill=self.initial_query[0])
        return MainMenuScreen()


def run_interactive(query: Optional[List[str]] = None) -> None:
    i18n.init()
    _maybe_run_first_run_setup()
    app = SpotdlApp(query=query)

    def _handle_signal(_signum, _frame) -> None:
        app.exit()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app.run()
