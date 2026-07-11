"""``MatchGauge`` — one audio match as a score bar + tallies (CONTRACT D, §4).

A dumb, focusable ``Static`` over a single :class:`MatchRow`: it renders a provider
icon, a colourised 0–100 score bar, a ``★`` verified marker, and the up/down/net
vote tallies as arrows. It owns no voting logic — when ``can_vote`` it exposes
``up``/``down``/``r`` bindings that post a :class:`MatchGauge.VoteRequested` for the
screen to service; when not, those bindings are disabled (``check_action``) so no
affordance shows. The focused (selected) gauge expands to reveal its source URL. The
screen applies fresh tallies via :meth:`update_row` and toggles voting availability
after a sign-in via :meth:`set_can_vote`.
"""

from __future__ import annotations

from uuid import UUID

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static

from spotdl_cli.tui.theme import (
    FAINT,
    METER_LIT,
    METER_UNLIT,
    SUCCESS,
    score_color,
    segmented_meter,
)
from spotdl_cli.viewmodels.types import MatchRow

_BAR_CELLS = 12

# provider → glyph; unknown providers fall back to a musical note.
_PROVIDER_ICONS = {
    "youtube": "▶",
    "youtube_music": "▶",
    "soundcloud": "☁",
    "bandcamp": "◆",
    "spotify": "♫",
}


class MatchGauge(Static, can_focus=True):
    class VoteRequested(Message):
        """Posted when a focused, votable gauge is voted on (``up``/``down``/``retract``)."""

        def __init__(self, match_id: UUID, value: str) -> None:
            self.match_id = match_id
            self.value = value
            super().__init__()

    BINDINGS = [
        Binding("up", "vote('up')", "Upvote"),
        Binding("down", "vote('down')", "Downvote"),
        Binding("r", "vote('retract')", "Retract", show=False),
    ]

    def __init__(self, row: MatchRow, *, can_vote: bool, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._row = row
        self._can_vote = can_vote
        self._focused = False
        self._repaint()

    @property
    def row(self) -> MatchRow:
        return self._row

    @property
    def can_vote(self) -> bool:
        return self._can_vote

    @property
    def summary(self) -> str:
        """The rendered gauge as plain text (for assertions / accessibility)."""
        return self._summary

    def update_row(self, row: MatchRow) -> None:
        """Re-render with a fresh row (the screen merges vote tallies before calling)."""
        self._row = row
        self._repaint()

    def set_can_vote(self, can_vote: bool) -> None:
        """Flip voting availability (e.g. after a community sign-in) and repaint."""
        if can_vote != self._can_vote:
            self._can_vote = can_vote
            self._repaint()

    def action_vote(self, value: str) -> None:
        if self._can_vote:
            self.post_message(self.VoteRequested(self._row.id, value))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide + disable the vote bindings on a read-only (non-voting) server."""
        return self._can_vote or action != "vote"

    def on_focus(self) -> None:
        self._focused = True
        self._repaint()

    def on_blur(self) -> None:
        self._focused = False
        self._repaint()

    def _repaint(self) -> None:
        plain, markup = _gauge(self._row, can_vote=self._can_vote, focused=self._focused)
        self._summary = plain
        self.update(markup)


def _gauge(row: MatchRow, *, can_vote: bool, focused: bool) -> tuple[str, str]:
    """Return ``(plain, markup)`` — plain for assertions, markup for the display.

    The score renders as the signature segmented LED meter (``▰▱``), lit in the
    match-quality colour (``score_color``): green ≥75, amber ≥45, else red.
    """
    filled = max(0, min(_BAR_CELLS, round(row.score / 100 * _BAR_CELLS)))
    plain_bar = METER_LIT * filled + METER_UNLIT * (_BAR_CELLS - filled)
    colour = score_color(row.score)
    meter = segmented_meter(row.score / 100, _BAR_CELLS, lit_color=colour)
    icon = _PROVIDER_ICONS.get(row.provider, "♪")
    verified = "  ★ verified" if row.verified else ""
    tallies = f"▲{row.upvotes} ▼{row.downvotes} ({row.net_score:+d})"
    head = f"{icon} {row.provider:<12}"
    score = f"{row.score:>3}%"
    plain = f"{head} {plain_bar} {score}  {row.status}  {tallies}{verified}"
    markup_verified = f"  [{SUCCESS}]★ verified[/]" if row.verified else ""
    markup = (
        f"{head} {meter} [{colour}]{score}[/]  {row.status}  [{FAINT}]{tallies}[/]{markup_verified}"
    )
    if focused and row.url:
        plain += f"\n    {row.url}"
        markup += f"\n    [{FAINT}]{row.url}[/]"
    if can_vote:
        plain += "   ↑ up · ↓ down"
        markup += f"   [{FAINT}]↑ up · ↓ down[/]"
    return plain, markup
