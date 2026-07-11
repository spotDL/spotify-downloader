"""The one TUI colour source — the "Control Room" palette, mirrored from the web.

``app.tcss`` styles entirely through Textual's semantic tokens (``$primary``,
``$accent``, ``$panel``, ``$surface`` …) rather than hardcoded hex, so recolouring
the whole terminal UI is a single registered :class:`~textual.theme.Theme`. The
values here are byte-for-byte the same as ``apps/web/src/index.css`` (spec Global
Constraints: "one palette, two renderers"): a broadcast-console identity — blue-ink
black surfaces, hairline borders, and a single phosphor-amber accent for
focus/active/meters, with cyan/green/yellow/red semantics. Dark-only, like the web.

Extra ``variables`` expose what Textual's base tokens don't — the hairline border
colours, the elevated/hover fill, the muted/faint text ramp, and the platform brand
colours — to ``.tcss`` as ``$border`` / ``$spotify`` / etc. so per-widget styling
never re-hardcodes a hex. The module also owns the signature :func:`segmented_meter`
(the ``▰▱`` LED bar) and :func:`score_color` so widgets share one meter vocabulary.
"""

from __future__ import annotations

from textual.theme import Theme

# ── Palette (byte-identical to apps/web/src/index.css "Control Room" dark) ──
BACKGROUND = "#0b0d12"  # --background — deepest chassis
SURFACE = "#12151c"  # --surface — sidebar / footer strips
PANEL = "#171b24"  # --card — cards, modals, inputs
ELEVATED = "#1e2430"  # --elevated — hover / focus fills
BORDER = "#262d3a"  # --border — hairline
BORDER_SOFT = "#1c222d"  # --border-soft — quietest hairline
TEXT = "#e8eaf0"  # --text
MUTED = "#8b93a7"  # --muted
FAINT = "#5a6274"  # --faint
TEXT_DIM = "#3a4150"  # below faint — unlit meter cells

PRIMARY = "#f5a623"  # --primary — phosphor amber (accent, focus, meters)
INFO = "#56c8d8"  # --info — cyan secondary signal
SUCCESS = "#4ade80"  # --success
WARNING = "#facc15"  # --warning
ERROR = "#f4506c"  # --error

# Platform brand colours (facts, unchanged across renderers).
SPOTIFY = "#1db954"
APPLE = "#fc3c44"
DEEZER = "#a238ff"
YOUTUBE = "#ff0000"
SOUNDCLOUD = "#ff5500"
MUSICBRAINZ = "#ba478f"

# Segmented LED meter glyphs — the signature progress/quality element.
METER_LIT = "▰"
METER_UNLIT = "▱"

SPOTDL_CONTROL_ROOM = Theme(
    name="spotdl-control-room",
    primary=PRIMARY,
    secondary=INFO,
    accent=PRIMARY,  # accent collapses into the single amber accent
    foreground=TEXT,
    background=BACKGROUND,
    surface=PANEL,  # $surface = the card tone (modals, inputs)
    panel=SURFACE,  # $panel = the sidebar/footer strip tone
    success=SUCCESS,
    warning=WARNING,
    error=ERROR,
    dark=True,
    variables={
        # elevated / hover fill (Textual's $boost overlay is retoned solid)
        "boost": ELEVATED,
        "elevated": ELEVATED,
        # text ramp — override the generated muted + expose the fainter stops
        "text-muted": MUTED,
        "text-secondary": MUTED,
        "text-disabled": FAINT,
        "faint": FAINT,
        "text-dim": TEXT_DIM,
        # hairline borders (amber cursor rows use CSS `color: auto` for dark ink)
        "border": BORDER,
        "border-soft": BORDER_SOFT,
        # platform brand colours (search/entity provider dots + badges)
        "spotify": SPOTIFY,
        "apple": APPLE,
        "deezer": DEEZER,
        "youtube": YOUTUBE,
        "soundcloud": SOUNDCLOUD,
        "musicbrainz": MUSICBRAINZ,
    },
)


def score_color(score: float) -> str:
    """Return the meter colour for a 0–100 match/quality score.

    ``>=75`` reads as success (green), ``>=45`` as warning (yellow), else error (red).
    Returns a palette hex so it works in both console markup and ``rich.Text`` styles.
    """
    if score >= 75:
        return SUCCESS
    if score >= 45:
        return WARNING
    return ERROR


def segmented_meter(
    value: float,
    width: int = 12,
    lit_color: str | None = None,
    unlit_color: str | None = None,
) -> str:
    """Build console markup for a segmented LED meter — the signature element.

    Renders ``width`` discrete cells: lit cells (``▰``) fill proportional to
    ``value`` (clamped to 0..1), remaining cells stay unlit (``▱``). This is the
    same LED-meter language the web UI uses for progress and match quality.

    Args:
        value: Fill fraction in the range 0..1.
        width: Total number of cells.
        lit_color: Hex for lit cells (defaults to the amber primary).
        unlit_color: Hex for unlit cells (defaults to the dim below-faint stop).

    Returns:
        Console markup string.
    """
    lit = lit_color or PRIMARY
    unlit = unlit_color or TEXT_DIM
    clamped = max(0.0, min(1.0, value))
    filled = max(0, min(width, round(clamped * width)))
    parts: list[str] = []
    if filled:
        parts.append(f"[{lit}]{METER_LIT * filled}[/]")
    if width - filled:
        parts.append(f"[{unlit}]{METER_UNLIT * (width - filled)}[/]")
    return "".join(parts)
