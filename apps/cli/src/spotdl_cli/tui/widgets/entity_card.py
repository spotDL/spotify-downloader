"""``EntityCard`` — the header block for an entity screen (CONTRACT D, Task 6).

A dumb ``Static``: it renders an :class:`EntityHeader` (title, subtitle, kind, and
``key: value`` stats) and nothing else. The owning screen builds the header from a
view-model and hands it over; the card never fetches. The title reads bold, the kind
and stat labels stay faint, and stat values light up in the emerald secondary (the
"counts are positive facts" voice). ``summary`` exposes the *plain* text so pilot tests
can assert on it without scraping the render tree.
"""

from __future__ import annotations

from textual.widgets import Static

from spotdl_cli.tui.theme import FAINT, INFO, MUTED
from spotdl_cli.viewmodels.types import EntityHeader


class EntityCard(Static):
    def __init__(self, header: EntityHeader, *, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._summary = _plain(header)
        self.update(_markup(header))

    @property
    def summary(self) -> str:
        """The rendered card as plain text (for assertions / accessibility)."""
        return self._summary


def _plain(header: EntityHeader) -> str:
    lines = [f"{header.title}  ({header.kind})"]
    if header.subtitle:
        lines.append(header.subtitle)
    if header.stats:
        lines.append("  ·  ".join(f"{label}: {value}" for label, value in header.stats))
    return "\n".join(lines)


def _markup(header: EntityHeader) -> str:
    lines = [f"[b]{header.title}[/b]  [{FAINT}]({header.kind})[/]"]
    if header.subtitle:
        lines.append(f"[{MUTED}]{header.subtitle}[/]")
    if header.stats:
        lines.append(
            "  ·  ".join(f"[{FAINT}]{label}[/] [{INFO}]{value}[/]" for label, value in header.stats)
        )
    return "\n".join(lines)
