"""
Interactive terminal interface for spotDL, built with Textual.
"""

from spotdl.console.tui.app import SpotdlApp, run_interactive
from spotdl.console.tui.lyrics import LyricsScreen
from spotdl.console.tui.navigation import AppBar, MenuPopover
from spotdl.console.tui.screens import (
    CommandBuilder,
    DownloadScreen,
    HelpScreen,
    LanguageScreen,
    MainMenuScreen,
    QueryScreen,
    SimpleOpScreen,
    TrackListScreen,
    WebScreen,
)
from spotdl.console.tui.settings import build_downloader_settings, format_duration

__all__ = [
    "AppBar",
    "CommandBuilder",
    "DownloadScreen",
    "HelpScreen",
    "LanguageScreen",
    "MainMenuScreen",
    "MenuPopover",
    "QueryScreen",
    "SimpleOpScreen",
    "SpotdlApp",
    "TrackListScreen",
    "WebScreen",
    "LyricsScreen",
    "build_downloader_settings",
    "format_duration",
    "run_interactive",
]
