"""CoverArt widget — renders cover art images in the terminal."""

from __future__ import annotations

import logging

from rich.text import Text
from rich_pixels import Pixels
from textual.reactive import reactive
from textual.widgets import Static

from spotdl_cli.core.image_service import get_image_service

logger = logging.getLogger(__name__)


class CoverArt(Static):
    """Displays a cover art image fetched from a URL.

    Set ``cover_url`` to trigger an async fetch + render.
    Falls back to ``[dim]No Cover[/]`` when no URL is provided or on failure.
    """

    cover_url: reactive[str | None] = reactive(None)

    def __init__(self, **kwargs: object) -> None:
        super().__init__("", **kwargs)

    def watch_cover_url(self, url: str | None) -> None:
        if url:
            self.run_worker(self._load_image(url), exclusive=True)
        else:
            self.update("[dim]No Cover[/]")

    async def _load_image(self, url: str) -> None:
        service = get_image_service()
        img = await service.get_image(url)

        if img is None:
            self.update("[dim]No Cover[/]")
            return

        # Compute resize dimensions from widget size.
        # Each terminal cell is ~2:1 (height:width in pixels), so we use
        # 2 image-pixels per cell row and 1 per cell column.
        width = self.size.width or 12
        height = (self.size.height or 6) * 2  # double for half-block chars

        try:
            pixels = Pixels.from_image(img, resize=(width, height))
            self.update(pixels)
        except Exception as e:
            logger.debug(f"Failed to render cover art: {e}")
            self.update("[dim]No Cover[/]")
