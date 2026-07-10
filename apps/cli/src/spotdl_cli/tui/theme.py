"""The one TUI colour source — the Emerald palette, mirrored from the web tokens.

``app.tcss`` styles entirely through Textual's semantic tokens (``$primary``,
``$accent``, ``$panel``, ``$surface`` …) rather than hardcoded hex, so recolouring
the whole terminal UI is a single registered :class:`~textual.theme.Theme`. The
values here are byte-for-byte the same as ``apps/web/src/index.css`` (spec Global
Constraints: "one palette, two renderers"): emerald primary over layered
near-black surfaces, teal/gold/red semantics. Dark-only, like the web surface.

Extra ``variables`` expose the platform brand colours and the two extra accents
(gold focus, teal secondary) to ``.tcss`` as ``$spotify`` / ``$gold`` / etc. so
per-widget styling never re-hardcodes a hex.
"""

from __future__ import annotations

from textual.theme import Theme

#: The canonical accent + surface values (kept identical to the web ``@theme``).
EMERALD = "#00d084"
TEAL = "#4ecdc4"
GOLD = "#ffd93d"
RED = "#ff3333"

SPOTDL_EMERALD = Theme(
    name="spotdl-emerald",
    primary=EMERALD,
    secondary=TEAL,
    accent=EMERALD,
    foreground="#fafafa",
    background="#0f1012",  # chassis
    surface="#242628",
    panel="#161819",
    success=EMERALD,
    warning=GOLD,
    error=RED,
    dark=True,
    variables={
        # extra accents
        "gold": GOLD,
        "teal": TEAL,
        # layered surfaces beyond Textual's background/surface/panel
        "void": "#08080a",
        "elevated": "#1c1e20",
        "hover": "#2c2e32",
        "line": "#2f2f33",
        "line-soft": "#232326",
        "text-secondary": "#a8a8b3",
        "text-dim": "#454550",
        # platform brand colours (search/entity provider dots + badges)
        "spotify": "#1db954",
        "apple": "#fc3c44",
        "deezer": "#a238ff",
        "youtube": "#ff0000",
        "soundcloud": "#ff5500",
        "musicbrainz": "#ba478f",
    },
)
