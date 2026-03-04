"""AudioMeter — Horizontal bar visualization widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


def _gradient_bar(value: float, width: int = 20) -> str:
    """Build a gradient bar using Unicode block elements."""
    clamped = max(0.0, min(1.0, value))
    filled = int(clamped * width)
    partial = clamped * width - filled

    bar = "█" * filled
    if partial > 0.75:
        bar += "▓"
    elif partial > 0.5:
        bar += "▒"
    elif partial > 0.25:
        bar += "░"

    bar = bar.ljust(width, " ")
    return bar[:width]


class AudioMeter(Widget):
    """Horizontal bar with gradient feel and value label."""

    DEFAULT_CSS = """
    AudioMeter {
        height: 1;
        width: 100%;
        margin: 0;
    }
    AudioMeter .am-label {
        width: 14;
        color: #a8a8b3;
    }
    AudioMeter .am-bar {
        width: 1fr;
        color: #e8764b;
    }
    AudioMeter .am-value {
        width: 6;
        color: #fafafa;
        text-style: bold;
        text-align: right;
    }
    """

    def __init__(
        self,
        label: str,
        value: float = 0.0,
        display_format: str = "percent",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._format = display_format

    def compose(self) -> ComposeResult:
        bar = _gradient_bar(self._value)
        if self._format == "percent":
            val_str = f"{self._value * 100:.0f}%"
        elif self._format == "bpm":
            val_str = f"{self._value:.0f}"
        else:
            val_str = f"{self._value:.2f}"

        with Horizontal():
            yield Static(self._label, classes="am-label")
            yield Static(bar, classes="am-bar")
            yield Static(val_str, classes="am-value")

    def update_value(self, value: float) -> None:
        self._value = value
        try:
            bar = _gradient_bar(value)
            self.query_one(".am-bar", Static).update(bar)
            if self._format == "percent":
                val_str = f"{value * 100:.0f}%"
            elif self._format == "bpm":
                val_str = f"{value:.0f}"
            else:
                val_str = f"{value:.2f}"
            self.query_one(".am-value", Static).update(val_str)
        except Exception:
            pass
