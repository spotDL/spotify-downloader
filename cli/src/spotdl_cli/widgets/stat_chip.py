"""StatChip — Inline stat display widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StatChip(Widget):
    """Renders: Label  Value with muted label and bright value."""

    DEFAULT_CSS = """
    StatChip {
        height: 1;
        width: auto;
        margin-right: 3;
    }
    StatChip .stat-chip-label {
        color: #6b6b76;
        width: auto;
    }
    StatChip .stat-chip-value {
        color: #fafafa;
        text-style: bold;
        width: auto;
        margin-left: 1;
    }
    """

    def __init__(self, label: str, value: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        yield Static(self._label, classes="stat-chip-label")
        yield Static(self._value, classes="stat-chip-value", id="chip-value")

    def update_value(self, value: str) -> None:
        try:
            self.query_one("#chip-value", Static).update(value)
        except Exception:
            pass
