"""Reusable pane patterns the screens compose on (CONTRACT §2).

Four dumb widgets that give every screen the same empty / loading / error /
metric vocabulary, so a pane is never a bare blank box: :class:`EmptyState`
(centred glyph + hint + the key to act), :class:`LoadingPane` (an inline
``LoadingIndicator``), :class:`ErrorPane` (message + retry hint), and
:class:`StatCard` (a bordered label/value tile). Styling lives entirely in
``app.tcss`` under the matching classes — these hold copy and structure only.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, LoadingIndicator, Static


class EmptyState(Static):
    """A centred glyph + one-line hint + the key that acts on it (§2).

    e.g. ``EmptyState("🔍", "No downloads yet", key_hint="press / to search")``.
    """

    def __init__(
        self,
        glyph: str,
        message: str,
        *,
        key_hint: str | None = None,
        id: str | None = None,
    ) -> None:
        self._glyph = glyph
        self._message = message
        self._key_hint = key_hint
        super().__init__(self._body(), id=id, classes="empty-state")

    def _body(self) -> str:
        parts = [self._glyph, self._message]
        if self._key_hint:
            parts.append(self._key_hint)
        return "\n\n".join(parts)

    def update_hint(self, message: str, *, key_hint: str | None = None) -> None:
        self._message = message
        self._key_hint = key_hint
        self.update(self._body())


class LoadingPane(Container):
    """An inline ``LoadingIndicator`` + label — no pane is ever left blank (§2)."""

    def __init__(self, label: str = "Loading…", *, id: str | None = None) -> None:
        self._label = label
        super().__init__(id=id, classes="loading-pane")

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        yield Label(self._label, classes="loading-label")


class ErrorPane(Static):
    """An in-pane error (message + retry-key hint) — not a bare toast (§2)."""

    def __init__(
        self,
        message: str,
        *,
        retry_key: str | None = None,
        id: str | None = None,
    ) -> None:
        self._message = message
        self._retry_key = retry_key
        super().__init__(self._body(), id=id, classes="error-pane")

    def _body(self) -> str:
        body = f"⚠  {self._message}"
        if self._retry_key:
            body += f"\n\npress {self._retry_key} to retry"
        return body

    def set_message(self, message: str, *, retry_key: str | None = None) -> None:
        self._message = message
        self._retry_key = retry_key
        self.update(self._body())


class StatCard(Static):
    """A bordered metric tile: value in the body, label in the border title (§2)."""

    def __init__(self, label: str, value: object, *, id: str | None = None) -> None:
        super().__init__(str(value), id=id, classes="stat-card")
        self.border_title = label

    def set_value(self, value: object) -> None:
        self.update(str(value))
