"""``EntityCard`` — a dumb header card for an album/artist/playlist/track (CONTRACT D).

Renders an :class:`~spotdl_cli.viewmodels.types.EntityHeader` and nothing else: the
title, the subtitle (artist/owner/genres), a ``kind`` badge, and the header's
``(label, value)`` stats. Like :class:`StatusBar` it exposes a plain-text
``summary`` so pilot tests can assert on the rendered line without scraping Rich.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from spotdl_cli.viewmodels.types import EntityHeader


class EntityCard(Static):
    """A framework-dumb card bound to a single ``EntityHeader``."""

    def __init__(self, header: EntityHeader, *, id: str | None = None) -> None:
        super().__init__(_render(header), id=id)
        self._header = header

    @property
    def header(self) -> EntityHeader:
        return self._header

    @property
    def summary(self) -> str:
        """The rendered card as plain text (for assertions / accessibility)."""
        return _summary(self._header)


def _summary(header: EntityHeader) -> str:
    parts = [header.title]
    if header.subtitle:
        parts.append(header.subtitle)
    parts.extend(f"{label}: {value}" for label, value in header.stats)
    return "  ·  ".join(parts)


def _render(header: EntityHeader) -> Text:
    text = Text()
    text.append(header.title, style="bold")
    text.append(f"  {header.kind}", style="dim")
    if header.subtitle:
        text.append(f"\n{header.subtitle}")
    if header.stats:
        stats = "   ".join(f"{label}: {value}" for label, value in header.stats)
        text.append(f"\n{stats}", style="dim")
    return text
