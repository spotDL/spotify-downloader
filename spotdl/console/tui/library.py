"""
Checks which songs of a query already exist on disk.
"""

from typing import Any, Dict, List

from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name


def song_file_exists(song: Song, settings: Dict[str, Any]) -> bool:
    """
    Check if the file of a song already exists with the given settings.

    ### Arguments
    - song: Song to look for.
    - settings: Downloader settings, as returned by `build_downloader_settings`.

    ### Returns
    - True when a file for the song exists, False otherwise.
    """

    template = settings.get("output")
    if not template:
        return False

    file_extension = settings.get("format") or "mp3"
    restrict = settings.get("restrict")
    length = settings.get("max_filename_length")
    detect_formats = settings.get("detect_formats") or [file_extension]

    for extension in detect_formats:
        path = create_file_name(song, template, extension, restrict, False, length)
        if path.exists():
            return True

    return False


def missing_songs(songs: List[Song], settings: Dict[str, Any]) -> List[Song]:
    """
    Return the songs that have no file on disk.

    ### Arguments
    - songs: Songs of the query.
    - settings: Downloader settings used for the check.

    ### Returns
    - The songs that are missing.
    """

    return [song for song in songs if not song_file_exists(song, settings)]


def present_songs(songs: List[Song], settings: Dict[str, Any]) -> List[Song]:
    """
    Return the songs that already have a file on disk.

    ### Arguments
    - songs: Songs of the query.
    - settings: Downloader settings used for the check.

    ### Returns
    - The songs that are present.
    """

    return [song for song in songs if song_file_exists(song, settings)]
