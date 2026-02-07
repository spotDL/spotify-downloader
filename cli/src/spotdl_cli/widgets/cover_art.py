"""CoverArt widget — renders cover art images in the terminal.

Uses textual-image for high-quality rendering via Sixel/TGP protocols
when the terminal supports it, with automatic Unicode fallback.
"""

from __future__ import annotations

import logging

from textual.containers import Container
from textual.reactive import reactive
from textual_image.widget import Image

from spotdl_cli.core.image_service import get_image_service

logger = logging.getLogger(__name__)


class CoverArt(Container):
    """Displays a cover art image fetched from a URL.

    Set ``cover_url`` to trigger an async fetch + render.
    Uses Sixel/TGP for high-quality rendering when supported,
    falls back to Unicode otherwise.
    """

    cover_url: reactive[str | None] = reactive(None, init=False)

    def compose(self):  # type: ignore[override]
        yield Image(id="cover-image")

    def on_mount(self) -> None:
        if self.cover_url:
            self.run_worker(self._load_image(self.cover_url), exclusive=True)

    def watch_cover_url(self, url: str | None) -> None:
        if not self.is_mounted:
            return
        if url:
            self.run_worker(self._load_image(url), exclusive=True)
        else:
            self._image_widget.image = None

    @property
    def _image_widget(self) -> Image:
        return self.query_one("#cover-image", Image)

    async def _load_image(self, url: str) -> None:
        service = get_image_service()
        img = await service.get_image(url)

        if img is None:
            self._image_widget.image = None
            return

        try:
            self._image_widget.image = img
        except Exception as e:
            logger.debug(f"Failed to render cover art: {e}")
            self._image_widget.image = None
