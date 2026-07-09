"""``MatchGauge`` — one audio match as a score bar + tallies (CONTRACT D, Task 6).

A dumb, focusable ``Static`` over a single :class:`MatchRow`: it renders the
provider, a 0–100 score bar, the status, and the up/down/net tallies. It owns no
voting logic — when ``can_vote`` it exposes ``u``/``d``/``r`` bindings that post a
:class:`MatchGauge.VoteRequested` for the screen to service; when not, those
bindings are disabled (``check_action``) so no affordance shows. The screen applies
the fresh tallies via :meth:`update_row`.
"""

from __future__ import annotations

from uuid import UUID

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static

from spotdl_cli.viewmodels.types import MatchRow

_BAR_CELLS = 10


class MatchGauge(Static, can_focus=True):
    class VoteRequested(Message):
        """Posted when a focused, votable gauge is voted on (``up``/``down``/``retract``)."""

        def __init__(self, match_id: UUID, value: str) -> None:
            self.match_id = match_id
            self.value = value
            super().__init__()

    BINDINGS = [
        Binding("u", "vote('up')", "Upvote"),
        Binding("d", "vote('down')", "Downvote"),
        Binding("r", "vote('retract')", "Retract", show=False),
    ]

    def __init__(self, row: MatchRow, *, can_vote: bool, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._row = row
        self._can_vote = can_vote
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

    def action_vote(self, value: str) -> None:
        if self._can_vote:
            self.post_message(self.VoteRequested(self._row.id, value))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide + disable the vote bindings on a read-only (non-voting) server."""
        return self._can_vote or action != "vote"

    def _repaint(self) -> None:
        self._summary = _gauge(self._row, can_vote=self._can_vote)
        self.update(self._summary)


def _gauge(row: MatchRow, *, can_vote: bool) -> str:
    filled = max(0, min(_BAR_CELLS, round(row.score / 100 * _BAR_CELLS)))
    bar = "█" * filled + "░" * (_BAR_CELLS - filled)
    verified = "  ✓ verified" if row.verified else ""
    tallies = f"▲{row.upvotes} ▼{row.downvotes} ({row.net_score:+d})"
    line = f"{row.provider:<12} {bar} {row.score:>3}%  {row.status}  {tallies}{verified}"
    if can_vote:
        line += "   [u]p [d]own"
    return line
