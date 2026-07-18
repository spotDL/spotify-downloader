"""
LRC related functions
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

from syncedlyrics import search as syncedlyrics_search
from syncedlyrics.utils import Lyrics, TargetType, has_translation

from spotdl.types.song import Song
from spotdl.utils.formatter import to_ms

logger = logging.getLogger(__name__)

__all__ = ["generate_lrc", "remove_lrc", "parse_lrc_timestamps"]


def generate_lrc(song: Song, output_file: Path):
    """
    Generates an LRC file for the current song

    ### Arguments
    - song: Song object
    - output_file: Path to the output file
    """

    if song.lyrics and has_translation(song.lyrics):
        lrc_data = song.lyrics
    else:
        try:
            lrc_data = syncedlyrics_search(song.display_name)
        except Exception:
            lrc_data = None

    if lrc_data:
        Lyrics(lrc_data).save_lrc_file(
            str(output_file.with_suffix(".lrc")), TargetType.PREFER_SYNCED
        )
        logger.debug("Saved lrc file for %s", song.display_name)
    else:
        logger.debug("No lrc file found for %s", song.display_name)


def remove_lrc(lyrics: str) -> str:
    """
    Removes lrc tags from lyrics

    ### Arguments
    - lyrics: Lyrics string

    ### Returns
    - Lyrics string without lrc tags
    """

    return re.sub(r"\[.*?\]", "", lyrics)


def parse_lrc_timestamps(lyrics: str) -> List[Tuple[str, float]]:
    """
    Parses LRC lyrics and extracts text with timestamps in milliseconds

    ### Arguments
    - lyrics: LRC formatted lyrics string

    ### Returns
    - List of tuples containing (text, timestamp_ms)
    """

    lrc_data = []
    for line in lyrics.splitlines():
        if not line or "]" not in line:
            continue

        time_tag = line.split("]", 1)[0] + "]"
        text = line.replace(time_tag, "")

        time_tag = time_tag.replace("[", "")
        time_tag = time_tag.replace("]", "")
        time_tag = time_tag.replace(".", ":")
        time_tag_vals = time_tag.split(":")

        if len(time_tag_vals) != 3:
            continue

        try:
            minute, sec, millisecond = time_tag_vals
            time = to_ms(min=minute, sec=sec, ms=millisecond)
            lrc_data.append((text, time))
        except (ValueError, TypeError):
            continue

    return lrc_data
