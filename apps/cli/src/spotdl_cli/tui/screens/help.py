"""``HelpScreen`` — a pushed cheat-sheet of the global key map (CONTRACT C).

Opened with ``?`` from anywhere and dismissed with ``escape`` (the base back
binding). Static content only; it lists the section keys and per-screen actions so
the key map lives in one visible place.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from spotdl_cli.tui.screens.base import SpotdlScreen

_HELP = """\
spotDL — keys

  1   Search            5   Admin
  2   Queue             6   Library
  3   Settings          ?   this help
  4   Account           esc back / close
                        q   quit

  Sections you can't reach on this server are hidden; the footer only lists the
  keys that work here. Within a screen, the footer shows that screen's own actions.
"""


class HelpScreen(SpotdlScreen):
    def compose_content(self) -> ComposeResult:
        yield Static(_HELP, classes="help-body")
