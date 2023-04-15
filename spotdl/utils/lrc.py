"""
LRC related functions
"""

import logging
from pathlib import Path

from syncedlyrics import search as syncedlyrics_search
from syncedlyrics.utils import is_lrc_valid, save_lrc_file

from spotdl.types.song import Song

logger = logging.getLogger(__name__)

__all__ = ["generate_lrc"]


def generate_lrc(song: Song, output_file: Path):
    """
    Generates an LRC file for the current song

    ### Arguments
    - song: Song object
    - output_file: Path to the output file
    """

    if song.lyrics and is_lrc_valid(song.lyrics):
        lrc_data = song.lyrics
    else:
        try:
            lrc_data = syncedlyrics_search(song.display_name)
        except Exception:
            lrc_data = None

    if lrc_data:
        save_lrc_file(str(output_file.with_suffix(".lrc")), lrc_data)
        logger.debug("Saved lrc file for %s", song.display_name)
    else:
        logger.debug("No lrc file found for %s", song.display_name)
