"""``SourcesPanel`` — the per-provider metadata provenance list (Task 2).

The terminal equivalent of the web ``SourcesPanel``: a dumb ``Static`` that renders a
tuple of :class:`~spotdl_cli.viewmodels.types.SourceRow` as **one dense row per
provider** — a brand-coloured dot, the provider name, and its ``(label value)`` metric
chips (followers/popularity for artists, label/year for albums, isrc for tracks) — so a
handful of providers reads as a compact list, not a stack of blocks. The owning screen
fetches the rows from :meth:`CollectionViewModel.load_sources`; the panel never fetches.
``summary`` exposes the rendered text so pilot tests can assert on it without scraping.
"""

from __future__ import annotations

from textual.widgets import Static

from spotdl_cli.tui.theme import (
    APPLE,
    DEEZER,
    FAINT,
    MUSICBRAINZ,
    MUTED,
    SOUNDCLOUD,
    SPOTIFY,
    YOUTUBE,
)
from spotdl_cli.viewmodels.types import SourceRow

_EMPTY = "[dim]no per-provider sources[/dim]"

# Provider → brand dot colour (the same identity dots the web SourcesPanel uses).
_DOTS = {
    "spotify": SPOTIFY,
    "apple": APPLE,
    "apple_music": APPLE,
    "deezer": DEEZER,
    "youtube": YOUTUBE,
    "youtube_music": YOUTUBE,
    "soundcloud": SOUNDCLOUD,
    "musicbrainz": MUSICBRAINZ,
}


class SourcesPanel(Static):
    def __init__(self, sources: tuple[SourceRow, ...] = (), *, id: str | None = None) -> None:
        super().__init__("", id=id, classes="sources-panel")
        self._summary = ""
        self.set_sources(sources)

    @property
    def summary(self) -> str:
        """The rendered panel as plain text (for assertions / accessibility)."""
        return self._summary

    def set_sources(self, sources: tuple[SourceRow, ...]) -> None:
        self._summary = _render(sources)
        self.update(self._summary)


def _dot(provider: str) -> str:
    return _DOTS.get(provider.lower(), FAINT)


def _render(sources: tuple[SourceRow, ...]) -> str:
    if not sources:
        return _EMPTY
    lines: list[str] = []
    for source in sources:
        row = f"[{_dot(source.provider)}]●[/] [b]{source.provider}[/b]"
        if source.name:
            row += f"  [{MUTED}]{source.name}[/]"
        if source.metrics:
            chips = "  ·  ".join(f"[{FAINT}]{label}[/] {value}" for label, value in source.metrics)
            row += f"   {chips}"
        lines.append(row)
    return "\n".join(lines)
