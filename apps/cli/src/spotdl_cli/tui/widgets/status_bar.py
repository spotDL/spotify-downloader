"""``StatusBar`` — the always-visible identity/transport/mode strip (CONTRACT C).

A dumb ``Static``: it renders a :class:`SessionSnapshot` and nothing else. The app
owns the snapshot and calls :meth:`update_session` on login/logout or after the
initial load; the bar never fetches. ``summary`` exposes the rendered line as plain
text so pilot tests can assert on it without scraping the render tree.
"""

from __future__ import annotations

from textual.widgets import Static

from spotdl_cli.viewmodels.app_state import SessionSnapshot


class StatusBar(Static):
    """Renders ``guest/email · transport · mode · matcher`` (+ a degraded flag)."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._summary = ""

    @property
    def summary(self) -> str:
        """The current line as plain text (for assertions / accessibility)."""
        return self._summary

    def update_session(self, session: SessionSnapshot | None) -> None:
        self._summary = _line(session)
        self.update(self._summary)


def _line(session: SessionSnapshot | None) -> str:
    if session is None:
        return "connecting…"
    identity = session.user_email or "guest"
    parts = [identity, session.transport_label, session.mode, f"matcher {session.matcher_version}"]
    if session.degraded:
        parts.append("degraded")
    return "  ·  ".join(parts)
