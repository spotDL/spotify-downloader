"""MatchBar — Match display widget for track screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from spotdl_cli.theme import Theme, get_platform_icon


def _score_bar(score: float, width: int = 20) -> str:
    """Build a Unicode block bar for a score (0-100)."""
    filled = int((score / 100) * width)
    blocks = "█" * filled + "░" * (width - filled)
    return blocks


class MatchBar(Widget, can_focus=True):
    """Single row: platform dot, title, score bar, vote count."""

    DEFAULT_CSS = """
    MatchBar {
        height: 1;
        width: 100%;
        padding: 0 1;
    }
    MatchBar:hover {
        background: #2c2e32;
    }
    MatchBar:focus {
        background: #2c2e32;
        border-left: thick #e8764b;
    }
    MatchBar .mb-platform {
        width: 3;
    }
    MatchBar .mb-title {
        width: 1fr;
        color: #fafafa;
    }
    MatchBar .mb-score {
        width: 24;
        color: #e8764b;
    }
    MatchBar .mb-votes {
        width: 8;
        color: #6b6b76;
        text-align: right;
    }
    """

    class Selected(Message):
        def __init__(self, match_data: dict) -> None:
            super().__init__()
            self.match_data = match_data

    def __init__(
        self,
        platform: str,
        title: str,
        score: float,
        votes: int = 0,
        match_data: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._platform = platform
        self._title = title
        self._score = score
        self._votes = votes
        self.match_data = match_data or {}

    def compose(self) -> ComposeResult:
        icon = get_platform_icon(self._platform)
        bar = _score_bar(self._score)
        with Horizontal():
            yield Static(icon, classes="mb-platform")
            yield Static(self._title[:35], classes="mb-title")
            yield Static(f"{bar} {self._score:.0f}%", classes="mb-score")
            yield Static(
                f"{'↑' if self._votes > 0 else ''}{self._votes}" if self._votes else "",
                classes="mb-votes",
            )

    def on_click(self) -> None:
        self.post_message(self.Selected(self.match_data))
