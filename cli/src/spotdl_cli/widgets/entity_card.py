"""EntityCard — Search result card widget with cover art and platform badges."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static
from textual_image.widget import Image

from spotdl_cli.core.image_service import get_image_service
from spotdl_cli.theme import Theme, PLATFORM_COLORS

logger = logging.getLogger(__name__)

# Type icons for entity display
ENTITY_TYPE_ICONS = {
    "track": Theme.ICON_MUSIC,
    "artist": Theme.ICON_ARTIST,
    "album": Theme.ICON_ALBUM,
    "playlist": Theme.ICON_PLAYLIST,
}

# Human-readable platform labels
PLATFORM_LABELS: dict[str, str] = {
    "spotify": "spotify",
    "youtube": "youtube",
    "youtube_music": "youtube music",
    "deezer": "deezer",
    "soundcloud": "soundcloud",
    "bandcamp": "bandcamp",
    "apple_music": "apple music",
    "tidal": "tidal",
    "amazon": "amazon",
}


def _build_platform_badges(platforms: list[str]) -> str:
    """Build Rich markup string for platform colored dots + labels."""
    parts = []
    for p in platforms[:3]:
        color = PLATFORM_COLORS.get(p, Theme.TEXT_MUTED)
        label = PLATFORM_LABELS.get(p, p)
        parts.append(f"[{color}]{Theme.ICON_DOT}[/] {label}")
    return "  ".join(parts)


class EntityCard(Widget, can_focus=True):
    """Search result card: cover art thumbnail, name, subtitle, platform badges, arrow."""

    DEFAULT_CSS = """
    EntityCard {
        height: 5;
        width: 100%;
        padding: 0 1;
        background: #242628;
        margin-bottom: 0;
    }
    EntityCard:hover {
        background: #2c2e32;
    }
    EntityCard:focus {
        border-left: thick #e8764b;
        background: #2c2e32;
    }
    EntityCard .ec-row {
        height: 100%;
        width: 100%;
    }
    EntityCard .ec-cover {
        width: 10;
        height: 5;
        background: #0c0c0e;
        content-align: center middle;
    }
    EntityCard .ec-cover-placeholder {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #6b6b76;
    }
    EntityCard .ec-cover-image {
        width: 100%;
        height: 100%;
    }
    EntityCard .ec-body {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    EntityCard .ec-name {
        color: #fafafa;
        text-style: bold;
        height: 1;
    }
    EntityCard .ec-subtitle {
        color: #a8a8b3;
        height: 1;
    }
    EntityCard .ec-platforms {
        color: #6b6b76;
        height: 1;
    }
    EntityCard .ec-arrow {
        width: 3;
        height: 100%;
        content-align: center middle;
        color: #6b6b76;
    }
    EntityCard .ec-arrow:hover {
        color: #a8a8b3;
    }
    """

    class Selected(Message):
        """Posted when entity card is selected."""

        def __init__(self, entity_data: dict) -> None:
            super().__init__()
            self.entity_data = entity_data

    def __init__(
        self,
        entity_type: str,
        name: str,
        subtitle: str = "",
        platform: str = "",
        entity_data: dict | None = None,
        image_url: str | None = None,
        platforms: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._entity_type = entity_type
        self._name = name
        self._subtitle = subtitle
        self._platform = platform
        self.entity_data = entity_data or {}
        self._image_url = image_url
        self._platforms = platforms or []

    def compose(self) -> ComposeResult:
        icon = ENTITY_TYPE_ICONS.get(self._entity_type, Theme.ICON_DOT)
        with Horizontal(classes="ec-row"):
            # Cover art container
            with Vertical(classes="ec-cover"):
                yield Static(icon, classes="ec-cover-placeholder")
                yield Image(classes="ec-cover-image")
            # Body
            with Vertical(classes="ec-body"):
                yield Static(self._name[:60], classes="ec-name")
                if self._subtitle:
                    yield Static(self._subtitle[:50], classes="ec-subtitle")
                if self._platforms:
                    yield Static(
                        _build_platform_badges(self._platforms),
                        classes="ec-platforms",
                    )
            # Arrow
            yield Static(Theme.ICON_ARROW_RIGHT, classes="ec-arrow")

    def on_mount(self) -> None:
        # Hide image initially, show placeholder
        try:
            self.query_one(".ec-cover-image", Image).display = False
        except Exception:
            pass
        if self._image_url:
            self.run_worker(self._load_image(self._image_url), exclusive=True)

    async def _load_image(self, url: str) -> None:
        service = get_image_service()
        img = await service.get_image(url)
        if img is None:
            return
        try:
            image_widget = self.query_one(".ec-cover-image", Image)
            image_widget.image = img
            image_widget.display = True
            self.query_one(".ec-cover-placeholder", Static).display = False
        except Exception as e:
            logger.debug(f"Failed to render card cover art: {e}")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.entity_data))
