"""``SourcesPanel`` — the per-provider metadata provenance list (Task 2).

The terminal equivalent of the web ``SourcesPanel``: a dumb ``Static`` that renders a
tuple of :class:`~spotdl_cli.viewmodels.types.SourceRow` — one provider per block, a
bold provider name over its ``(label · value)`` metric chips (followers/popularity for
artists, label/year for albums, isrc for tracks). The owning screen fetches the rows
from :meth:`CollectionViewModel.load_sources`; the panel never fetches. ``summary``
exposes the rendered text so pilot tests can assert on it without scraping the tree.
"""

from __future__ import annotations

from textual.widgets import Static

from spotdl_cli.viewmodels.types import SourceRow

_EMPTY = "[dim]no per-provider sources[/dim]"


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


def _render(sources: tuple[SourceRow, ...]) -> str:
    if not sources:
        return _EMPTY
    blocks: list[str] = []
    for source in sources:
        head = f"[b]{source.provider}[/b]"
        if source.name:
            head += f"  {source.name}"
        lines = [head]
        if source.metrics:
            chips = "  ·  ".join(f"[dim]{label}[/dim] {value}" for label, value in source.metrics)
            lines.append(f"  {chips}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
