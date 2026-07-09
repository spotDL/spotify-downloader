"""``HelpScreen`` — an overlay modal key map, per-screen aware (CONTRACT §4).

Opened with ``?`` from anywhere and dismissed with ``escape``/``?``. Unlike a section
screen it is a :class:`ModalScreen` (it floats over the current screen, no nav rail):
the left column is the reachable section keys, the right column is the focused
screen's own ``BINDINGS`` — so the map always reflects where you actually are.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

if TYPE_CHECKING:
    from spotdl_cli.tui.app import SpotdlApp


class HelpScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-panel"):
            yield Static(id="help-map", classes="help-body")

    def on_mount(self) -> None:
        panel = self.query_one("#help-panel")
        panel.border_title = "Keys"
        self.query_one("#help-map", Static).update(self._key_map())

    def _key_map(self) -> str:
        app = cast("SpotdlApp", self.app)
        left = [f"{section.key}   {section.title}" for section in app.available_sections()]
        left += ["?   Help", "q   Quit", "esc Back / close"]
        under = app.screen_stack[-2] if len(app.screen_stack) >= 2 else None
        right = [f"{b.key:<7}{b.description}" for b in _screen_bindings(under)]
        header = "  Sections                Here"
        body = "\n".join(_pair(left, right))
        note = (
            "\n\n  Sections you can't reach on this server are hidden; the footer only "
            "lists\n  the keys that work here."
        )
        return f"{header}\n{body}{note}"


def _pair(left: list[str], right: list[str]) -> list[str]:
    rows: list[str] = []
    for index in range(max(len(left), len(right))):
        lhs = left[index] if index < len(left) else ""
        rhs = right[index] if index < len(right) else ""
        rows.append(f"  {lhs:<22}{rhs}")
    return rows


def _screen_bindings(screen: Screen[object] | None) -> list[Binding]:
    """The focused screen's own visible, described key bindings (§4)."""
    if screen is None:
        return []
    out: list[Binding] = []
    for entry in type(screen).BINDINGS:
        binding = entry if isinstance(entry, Binding) else _from_tuple(entry)
        if binding is not None and binding.description and binding.show is not False:
            out.append(binding)
    return out


def _from_tuple(entry: object) -> Binding | None:
    if not isinstance(entry, tuple) or not entry:
        return None
    key = str(entry[0])
    action = str(entry[1]) if len(entry) > 1 else ""
    description = str(entry[2]) if len(entry) > 2 else ""
    return Binding(key, action, description)
