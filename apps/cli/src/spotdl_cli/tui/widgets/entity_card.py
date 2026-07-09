"""``EntityCard`` — the header block for an entity screen (CONTRACT D, Task 6).

A dumb ``Static``: it renders an :class:`EntityHeader` (title, subtitle, kind, and
``key: value`` stats) and nothing else. The owning screen builds the header from a
view-model and hands it over; the card never fetches. ``summary`` exposes the
rendered text so pilot tests can assert on it without scraping the render tree.
"""

from __future__ import annotations

from textual.widgets import Static

from spotdl_cli.viewmodels.types import EntityHeader


class EntityCard(Static):
    def __init__(self, header: EntityHeader, *, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._summary = _card(header)
        self.update(self._summary)

    @property
    def summary(self) -> str:
        """The rendered card as plain text (for assertions / accessibility)."""
        return self._summary


def _card(header: EntityHeader) -> str:
    lines = [f"{header.title}  ({header.kind})"]
    if header.subtitle:
        lines.append(header.subtitle)
    if header.stats:
        lines.append("  ·  ".join(f"{label}: {value}" for label, value in header.stats))
    return "\n".join(lines)
