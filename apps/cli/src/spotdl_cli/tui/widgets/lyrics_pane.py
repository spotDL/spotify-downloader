"""``LyricsPane`` — the lyrics viewer with source cycling + synced follow (Task 6).

A dumb, focusable ``Static`` over the track's ordered :class:`LyricsChoice`\\s.
``[``/``]`` cycle the visible source; ``space`` toggles *follow*, which — for a
synced variant — highlights the line the player is on. The active line is the pure
``TrackViewModel.active_synced_line`` of the current position; the pane holds no
timing logic of its own and never fetches. The owner feeds playback position via
:meth:`set_position`.
"""

from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Static

from spotdl_cli.viewmodels.track import TrackViewModel
from spotdl_cli.viewmodels.types import LyricsChoice


class LyricsPane(Static, can_focus=True):
    BINDINGS = [
        Binding("left_square_bracket", "prev_source", "Prev lyrics"),
        Binding("right_square_bracket", "next_source", "Next lyrics"),
        Binding("space", "toggle_follow", "Follow"),
    ]

    def __init__(self, choices: tuple[LyricsChoice, ...], *, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._choices = choices
        self._index = 0
        self._follow = False
        self._position_ms = 0
        self._active: int | None = None
        self._repaint()

    @property
    def choice(self) -> LyricsChoice | None:
        return self._choices[self._index] if self._choices else None

    @property
    def active_line(self) -> int | None:
        """Index of the highlighted synced line, or ``None`` when not following."""
        return self._active

    def set_position(self, position_ms: int) -> None:
        """Feed the player position; recomputes the active line when following."""
        self._position_ms = position_ms
        self._recompute_active()
        self._repaint()

    def action_prev_source(self) -> None:
        self._cycle(-1)

    def action_next_source(self) -> None:
        self._cycle(1)

    def action_toggle_follow(self) -> None:
        self._follow = not self._follow
        self._recompute_active()
        self._repaint()

    def _cycle(self, step: int) -> None:
        if not self._choices:
            return
        self._index = (self._index + step) % len(self._choices)
        self._recompute_active()
        self._repaint()

    def _recompute_active(self) -> None:
        choice = self.choice
        if self._follow and choice is not None and choice.synced:
            self._active = TrackViewModel.active_synced_line(choice, self._position_ms)
        else:
            self._active = None

    def _repaint(self) -> None:
        self.update(_render(self.choice, active=self._active, follow=self._follow))


def _render(choice: LyricsChoice | None, *, active: int | None, follow: bool) -> str:
    if choice is None:
        return "no lyrics available"
    follow_flag = "  ⟳ follow" if follow else ""
    header = f"{choice.source} · {choice.kind}{follow_flag}"
    body = [
        f"{'▶ ' if index == active else '  '}{line.text}"
        for index, line in enumerate(choice.lines)
    ]
    return "\n".join([header, "", *body])
