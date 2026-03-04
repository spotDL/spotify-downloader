"""Theme constants aligned with frontend design system.

Colors are extracted from frontend/src/index.css to ensure visual consistency
between the web frontend and CLI TUI.
"""

from __future__ import annotations


class Theme:
    """Frontend-aligned color theme for SpotDL CLI."""

    # ==================== ACCENT COLORS ====================
    # Primary actions, highlights
    PRIMARY = "#e8764b"  # muted terracotta (Midnight Vinyl)
    # Focus glow — separate identity from primary
    FOCUS = "#c4a35a"  # warm gold
    # Secondary actions
    SECONDARY = "#4ecdc4"  # --accent-secondary (teal)
    # Success states
    SUCCESS = "#00d084"  # --accent-success (green)
    # Errors, destructive actions
    ERROR = "#ff3333"  # --accent-error (red)
    # Premium highlights, warnings
    WARNING = "#ffd93d"  # --accent-gold (gold/amber)

    # ==================== ADDITIONAL TOKENS ====================
    BG_INSET = "#0c0c0e"  # Recessed panels for depth
    TEXT_ACCENT = "#e8e0d0"  # Warm white for titles

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

    # ==================== UNICODE ICONS ====================
    ICON_SEARCH = "⌕"
    ICON_DOWNLOAD = "↓"
    ICON_SETTINGS = "⚙"
    ICON_ACCOUNT = "⚇"
    ICON_MUSIC = "♪"
    ICON_ARTIST = "♫"
    ICON_ALBUM = "◉"
    ICON_PLAYLIST = "≡"
    ICON_CHECK = "✓"
    ICON_CROSS = "✕"
    ICON_ARROW_RIGHT = "→"
    ICON_DOT = "●"


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


# Rich markup icons for platforms (used in TUI widgets)
PLATFORM_ICONS: dict[str, str] = {
    "spotify": "[green]●[/]",
    "youtube": "[red]●[/]",
    "youtube_music": "[red]●[/]",
    "deezer": "[magenta]●[/]",
    "soundcloud": "[#ff5500]●[/]",
    "bandcamp": "[cyan]●[/]",
    "apple_music": "[white]●[/]",
    "tidal": "[white]●[/]",
    "amazon": "[#ff9900]●[/]",
}


def get_platform_icon(platform: str) -> str:
    """Get Rich markup icon for a platform."""
    return PLATFORM_ICONS.get(platform.lower(), "●")


def format_number(num: int) -> str:
    """Format large numbers with K/M suffixes."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def format_duration(seconds: int) -> str:
    """Format seconds as m:ss or Xh Ym."""
    if seconds >= 3600:
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours}h {minutes}m"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


__all__ = [
    "DOWNLOAD_STATUS_COLORS",
    "PLATFORM_COLORS",
    "PLATFORM_ICONS",
    "STATUS_COLORS",
    "Theme",
    "format_duration",
    "format_number",
    "get_download_status_color",
    "get_platform_color",
    "get_platform_icon",
    "get_status_color",
    "truncate",
]

# Convenience aliases for icon access
ICONS = {
    "search": Theme.ICON_SEARCH,
    "download": Theme.ICON_DOWNLOAD,
    "settings": Theme.ICON_SETTINGS,
    "account": Theme.ICON_ACCOUNT,
    "music": Theme.ICON_MUSIC,
    "artist": Theme.ICON_ARTIST,
    "album": Theme.ICON_ALBUM,
    "playlist": Theme.ICON_PLAYLIST,
    "check": Theme.ICON_CHECK,
    "cross": Theme.ICON_CROSS,
    "arrow_right": Theme.ICON_ARROW_RIGHT,
    "dot": Theme.ICON_DOT,
}
