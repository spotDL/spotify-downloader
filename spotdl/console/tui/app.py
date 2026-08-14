import signal
from typing import List, Optional

from textual.app import App
from textual.screen import Screen
from textual.theme import Theme

from spotdl._version import __version__
from spotdl.console.tui import i18n
from spotdl.console.tui.css import CSS
from spotdl.console.tui.screens import MainMenuScreen, QueryScreen
from spotdl.console.tui.state import AppState

__all__ = ["SpotdlApp", "run_interactive"]

SPOTDL_THEME = Theme(
    name="spotdl",
    dark=True,
    primary="#1DB954",
    secondary="#1ED760",
    accent="#1ED760",
    foreground="#FFFFFF",
    background="#121212",
    surface="#181818",
    panel="#282828",
    warning="#FFB020",
    error="#F15E5E",
    success="#1DB954",
)


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
    app = SpotdlApp(query=query)

    def _handle_signal(_signum, _frame) -> None:
        app.exit()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app.run()
