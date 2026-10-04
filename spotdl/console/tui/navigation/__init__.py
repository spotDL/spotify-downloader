"""
Navigation widgets shared by the TUI screens.
"""

from spotdl.console.tui.navigation.appbar import AppBar, refresh_all_screens
from spotdl.console.tui.navigation.footer import VersionFooter, format_version_line
from spotdl.console.tui.navigation.menupopover import MenuPopover

__all__ = [
    "AppBar",
    "MenuPopover",
    "VersionFooter",
    "format_version_line",
    "refresh_all_screens",
]
