"""LRC (synced lyrics) file generation."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_synced(lyrics: str) -> bool:
    """Check if lyrics text contains LRC sync timestamps."""
    return "[" in lyrics and "]" in lyrics and any(
        line.strip().startswith("[") and ":" in line.split("]")[0]
        for line in lyrics.splitlines()
        if line.strip()
    )


def generate_lrc(
    song_name: str,
    song_artists: list[str],
    output_file: Path,
    lyrics: str | None = None,
) -> bool:
    """Generate an LRC file for a song.

    If synced lyrics are already provided, writes them directly.
    Otherwise uses the syncedlyrics library to search for synced lyrics.

    Args:
        song_name: Name of the song.
        song_artists: List of artist names.
        output_file: Path to the audio file (LRC will use same stem).
        lyrics: Optional pre-fetched lyrics text.

    Returns:
        True if LRC file was created successfully.
    """
    lrc_path = output_file.with_suffix(".lrc")

    # If we already have synced lyrics, write them directly
    if lyrics and is_synced(lyrics):
        try:
            lrc_path.write_text(lyrics, encoding="utf-8")
            logger.debug("Wrote synced lyrics to %s", lrc_path)
            return True
        except OSError as e:
            logger.warning("Failed to write LRC file %s: %s", lrc_path, e)
            return False

    # Search for synced lyrics using syncedlyrics
    try:
        from syncedlyrics import search as syncedlyrics_search

        display_name = f"{', '.join(song_artists)} - {song_name}"
        synced = syncedlyrics_search(display_name)

        if synced:
            lrc_path.write_text(synced, encoding="utf-8")
            logger.debug("Found and wrote synced lyrics for %s", display_name)
            return True

        logger.debug("No synced lyrics found for %s", display_name)
        return False

    except ImportError:
        logger.warning("syncedlyrics package not installed, skipping LRC generation")
        return False
    except Exception as e:
        logger.warning("Failed to search for synced lyrics: %s", e)
        return False
