"""CoverArt widget — renders cover art images in the terminal.

Uses textual-image for high-quality rendering via Sixel/TGP protocols
when the terminal supports it, with automatic Unicode fallback.
"""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static
from textual_image.widget import Image

from spotdl_cli.core.image_service import get_image_service
from spotdl_cli.theme import Theme

logger = logging.getLogger(__name__)

# Contextual fallback icons
FALLBACK_ICONS = {
    "track": Theme.ICON_MUSIC,
    "artist": Theme.ICON_ARTIST,
    "album": Theme.ICON_ALBUM,
    "playlist": Theme.ICON_PLAYLIST,
}


class CoverArt(Container):
    """Displays a cover art image fetched from a URL.

    Set ``cover_url`` to trigger an async fetch + render.
    Uses Sixel/TGP for high-quality rendering when supported,
    falls back to Unicode otherwise.
    """

    cover_url: reactive[str | None] = reactive(None, init=False)
    entity_type: reactive[str] = reactive("track", init=False)

    def __init__(self, entity_type: str = "track", **kwargs) -> None:
        super().__init__(**kwargs)
        self._entity_type = entity_type

    def compose(self) -> ComposeResult:  # type: ignore[override]
        fallback = FALLBACK_ICONS.get(self._entity_type, Theme.ICON_MUSIC)
        yield Static(
            f"[dim]{fallback}[/]",
            id="cover-placeholder",
            classes="cover-placeholder-icon",
        )
        yield Image(id="cover-image")

    def on_mount(self) -> None:
        # Show placeholder, hide image initially
        try:
            self.query_one("#cover-image", Image).display = False
        except Exception:
            pass
        if self.cover_url:
            self._show_loading()
            self.run_worker(self._load_image(self.cover_url), exclusive=True)

    def watch_cover_url(self, url: str | None) -> None:
        if not self.is_mounted:
            return
        if url:
            self._show_loading()
            self.run_worker(self._load_image(url), exclusive=True)
        else:
            self._show_placeholder()

    def _show_loading(self) -> None:
        """Show loading state with pulsing icon."""
        fallback = FALLBACK_ICONS.get(self._entity_type, Theme.ICON_MUSIC)
        try:
            placeholder = self.query_one("#cover-placeholder", Static)
            placeholder.update(f"[{Theme.PRIMARY}]{fallback}[/]")
            placeholder.display = True
            self.query_one("#cover-image", Image).display = False
        except Exception:
            pass

    def _show_placeholder(self) -> None:
        """Show contextual fallback icon."""
        fallback = FALLBACK_ICONS.get(self._entity_type, Theme.ICON_MUSIC)
        try:
            placeholder = self.query_one("#cover-placeholder", Static)
            placeholder.update(f"[dim]{fallback}[/]")
            placeholder.display = True
            self.query_one("#cover-image", Image).display = False
        except Exception:
            pass

    @property
    def _image_widget(self) -> Image:
        return self.query_one("#cover-image", Image)

    async def _load_image(self, url: str) -> None:
        service = get_image_service()
        img = await service.get_image(url)

        if img is None:
            self._show_placeholder()
            return

        try:
            self._image_widget.image = img
            self._image_widget.display = True
            self.query_one("#cover-placeholder", Static).display = False
        except Exception as e:
            logger.debug(f"Failed to render cover art: {e}")
            self._show_placeholder()
