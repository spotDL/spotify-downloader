"""Theme constants aligned with frontend design system.

Colors are extracted from frontend/src/index.css to ensure visual consistency
between the web frontend and CLI TUI.
"""

from __future__ import annotations


class Theme:
    """Frontend-aligned color theme for SpotDL CLI."""

    # ==================== ACCENT COLORS ====================
    # Primary actions, highlights
    PRIMARY = "#ff6b35"  # --accent-primary (orange)
    # Secondary actions
    SECONDARY = "#4ecdc4"  # --accent-secondary (teal)
    # Success states
    SUCCESS = "#00d084"  # --accent-success (green)
    # Errors, destructive actions
    ERROR = "#ff3333"  # --accent-error (red)
    # Premium highlights, warnings
    WARNING = "#ffd93d"  # --accent-gold (gold/amber)

    # ==================== BACKGROUND COLORS ====================
    # True black - deepest layer
    BG_VOID = "#08080a"  # --bg-void
    # Base background - slightly warmer
    BG_CHASSIS = "#0f1012"  # --bg-chassis
    # Panel surfaces
    BG_PANEL = "#161819"  # --bg-panel
    # Elevated surfaces
    BG_ELEVATED = "#1c1e20"  # --bg-elevated
    # Cards, modals
    BG_SURFACE = "#242628"  # --bg-surface
    # Hover states
    BG_HOVER = "#2c2e32"  # --bg-hover

    # ==================== TEXT COLORS ====================
    TEXT_PRIMARY = "#fafafa"  # --color-text-primary
    TEXT_SECONDARY = "#a8a8b3"  # --color-text-secondary
    TEXT_MUTED = "#6b6b76"  # --color-text-muted
    TEXT_DIM = "#454550"  # --color-text-dim

    # ==================== BORDER COLORS ====================
    BORDER = "#2f2f33"  # --color-border
    BORDER_SUBTLE = "#232326"  # --color-border-subtle

    # ==================== PLATFORM COLORS ====================
    SPOTIFY = "#1db954"  # --color-spotify
    YOUTUBE = "#ff0000"  # --color-youtube
    YOUTUBE_MUSIC = "#ff0000"  # --color-ytmusic
    DEEZER = "#a238ff"  # --color-deezer
    SOUNDCLOUD = "#ff5500"  # --color-soundcloud
    BANDCAMP = "#1da0c3"  # --color-bandcamp
    APPLE_MUSIC = "#fc3c44"  # --color-apple
    TIDAL = "#000000"  # --color-tidal
    AMAZON = "#ff9900"  # --color-amazon


# Platform color mapping for easy lookup
PLATFORM_COLORS: dict[str, str] = {
    "spotify": Theme.SPOTIFY,
    "youtube": Theme.YOUTUBE,
    "youtube_music": Theme.YOUTUBE_MUSIC,
    "deezer": Theme.DEEZER,
    "soundcloud": Theme.SOUNDCLOUD,
    "bandcamp": Theme.BANDCAMP,
    "apple_music": Theme.APPLE_MUSIC,
    "tidal": Theme.TIDAL,
    "amazon": Theme.AMAZON,
}

# Status color mapping
STATUS_COLORS: dict[str, str] = {
    "success": Theme.SUCCESS,
    "error": Theme.ERROR,
    "warning": Theme.WARNING,
    "info": Theme.SECONDARY,
    "pending": Theme.TEXT_MUTED,
}

# Download status colors
DOWNLOAD_STATUS_COLORS: dict[str, str] = {
    "pending": Theme.TEXT_MUTED,
    "searching": Theme.WARNING,
    "downloading": Theme.PRIMARY,
    "converting": Theme.SECONDARY,
    "embedding": Theme.SECONDARY,
    "completed": Theme.SUCCESS,
    "failed": Theme.ERROR,
    "cancelled": Theme.TEXT_MUTED,
}


def get_platform_color(platform: str) -> str:
    """Get the color for a platform.

    Args:
        platform: Platform name (e.g., 'spotify', 'youtube')

    Returns:
        Hex color string
    """
    return PLATFORM_COLORS.get(platform.lower(), Theme.TEXT_MUTED)


def get_status_color(status: str) -> str:
    """Get the color for a status.

    Args:
        status: Status name

    Returns:
        Hex color string
    """
    return STATUS_COLORS.get(status.lower(), Theme.TEXT_MUTED)


def get_download_status_color(status: str) -> str:
    """Get the color for a download status.

    Args:
        status: Download status name

    Returns:
        Hex color string
    """
    return DOWNLOAD_STATUS_COLORS.get(status.lower(), Theme.TEXT_MUTED)


__all__ = [
    "DOWNLOAD_STATUS_COLORS",
    "PLATFORM_COLORS",
    "STATUS_COLORS",
    "Theme",
    "get_download_status_color",
    "get_platform_color",
    "get_status_color",
]
