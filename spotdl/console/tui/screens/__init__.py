"""
Screens of the interactive interface.
"""

from spotdl.console.tui.screens.download import (
    CommandBuilder,
    ConfirmScreen,
    DownloadScreen,
    DownloadsScreen,
    HistoryScreen,
    QueryScreen,
    SimpleOpScreen,
    TrackListScreen,
)
from spotdl.console.tui.screens.help import HelpScreen, LanguageScreen
from spotdl.console.tui.screens.home import MainMenuScreen
from spotdl.console.tui.screens.settings import SettingsScreen
from spotdl.console.tui.screens.web import WebScreen

__all__ = [
    "CommandBuilder",
    "ConfirmScreen",
    "DownloadScreen",
    "DownloadsScreen",
    "HelpScreen",
    "HistoryScreen",
    "LanguageScreen",
    "MainMenuScreen",
    "QueryScreen",
    "SettingsScreen",
    "SimpleOpScreen",
    "TrackListScreen",
    "WebScreen",
]
