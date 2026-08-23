"""
Module for creating m3u content and writing it to a file.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name, sanitize_string

__all__ = [
    "create_m3u_content",
    "gen_m3u_files",
    "create_m3u_file",
]

logger = logging.getLogger(__name__)


def _m3u_entry(file_name: Path, m3u_dir: Optional[Path]) -> str:
    raw = str(file_name)
    if m3u_dir is not None:
        try:
            rel = os.path.relpath(raw, str(m3u_dir))
        except ValueError:
            rel = raw
        raw = rel
    return raw.replace("\\", "/")


def create_m3u_content(
    song_list: List[Song],
    template: str,
    file_extension: str,
    restrict: Optional[str] = None,
    short: bool = False,
    detect_formats: Optional[List[str]] = None,
    m3u_file: Optional[str] = None,
) -> str:
    """
    Create m3u content and return it as a string.

    ### Arguments
    - song_list: the list of songs
    - template: the template to use
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template
    - detect_formats: the formats to detect for existing files
    - m3u_file: the path of the m3u file being written. When provided,
        song entries are written relative to the m3u file's directory and
        use forward slashes, so the playlist stays portable across operating
        systems (e.g. plays correctly in Apple/Android players such as flacbox).

    ### Returns
    - the m3u content as a string
    """

    m3u_dir = Path(m3u_file).resolve().parent if m3u_file else None
    text = "#EXTM3U\n"

    for song in song_list:
        metadata = create_file_name(
            song, "#EXTINF:{duration},{album-artist} - {title}", ""
        )
        text += str(metadata) + "\n"

        if not detect_formats:
            file_name = create_file_name(
                song, template, file_extension, restrict, short
            )

            text += _m3u_entry(file_name, m3u_dir) + "\n"
        else:
            for file_ext in detect_formats:
                file_name = create_file_name(song, template, file_ext, restrict, short)

                if file_name.exists():
                    text += _m3u_entry(file_name, m3u_dir) + "\n"
                    break
            else:
                # Runs if no existing file was found (no break)
                file_name = create_file_name(
                    song, template, file_extension, restrict, short
                )
                text += _m3u_entry(file_name, m3u_dir) + "\n"

    return text


def gen_m3u_files(
    songs: List[Song],
    file_name: Optional[str],
    template: str,
    file_extension: str,
    restrict: Optional[str] = None,
    short: bool = False,
    detect_formats: Optional[List[str]] = None,
):
    """
    Create an m3u8 filename from the query.

    ### Arguments
    - songs: the list of songs
    - file_name: the file name to use
    - template: the output file template to use
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template
    - detect_formats: the formats to detect
    """

    # If no file name is provided or a generic playlist default is used, use the first list's name
    if not file_name:
        file_name = "{list[0]}.m3u8"
    elif file_name in ["playlist.m3u8", "playlist.m3u", "playlist"]:
        file_name = "{list[0]}.m3u8"
    elif file_name.replace("\\", "/").endswith("/playlist.m3u8"):
        file_name = file_name.replace("\\", "/")[:-len("playlist.m3u8")] + "{list[0]}.m3u8"
    elif file_name.replace("\\", "/").endswith("/playlist.m3u"):
        file_name = file_name.replace("\\", "/")[:-len("playlist.m3u")] + "{list[0]}.m3u8"

    # If file_name ends with a slash. Does not have a m3u8 name with extension
    # at the end of the template, append `{list[0]}`` to it
    if (
        file_name.endswith("/")
        or file_name.endswith(r"\\")
        or file_name.endswith("\\\\")
    ):
        file_name += "/{list[0]}.m3u8"

    # Check if the file name ends with .m3u or .m3u8
    if not file_name.endswith(".m3u") and not file_name.endswith(".m3u8"):
        file_name += ".m3u8"

    lists_object: Dict[str, List[Song]] = {}
    for song in songs:
        if song.list_name is None:
            continue

        if song.list_name not in lists_object:
            lists_object[song.list_name] = []

        lists_object[song.list_name].append(song)

    if not lists_object:
        # Fallback to album name or first song name if no list name is present
        fallback_name = (
            songs[0].album_name
            or songs[0].name
            or "playlist"
        ) if songs else "playlist"
        lists_object[fallback_name] = list(songs)

    if "{list}" in file_name:
        # Create multiple m3u files if there are multiple lists
        for list_name, song_list in lists_object.items():
            create_m3u_file(
                file_name.format(
                    list=sanitize_string(list_name),
                ),
                song_list,
                template,
                file_extension,
                restrict,
                short,
                detect_formats,
            )
    elif "{list[" in file_name and "]}" in file_name:
        # Create a single m3u file for specified song list name
        create_m3u_file(
            file_name.format(
                list=[sanitize_string(key) for key in lists_object.keys()]
            ),
            songs,
            template,
            file_extension,
            restrict,
            short,
            detect_formats,
        )
    else:
        # Use the provided file name
        create_m3u_file(
            file_name,
            songs,
            template,
            file_extension,
            restrict,
            short,
            detect_formats,
        )


def create_m3u_file(
    file_name: str,
    song_list: List[Song],
    template: str,
    file_extension: str,
    restrict: Optional[str] = None,
    short: bool = False,
    detect_formats: Optional[List[str]] = None,
) -> str:
    """
    Create the m3u file.

    ### Arguments
    - file_name: the file name to use
    - song_list: the list of songs
    - template: the template to use
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template
    - detect_formats: the formats to detect

    ### Returns
    - the m3u content as a string
    """

    m3u_content = create_m3u_content(
        song_list,
        template,
        file_extension,
        restrict,
        short,
        detect_formats,
        file_name,
    )

    raw_path = Path(file_name)
    if raw_path.is_absolute():
        parts = [sanitize_string(part) for part in raw_path.parts[1:]]
        file_path = Path(raw_path.anchor, *parts)
    else:
        file_path = Path(*(sanitize_string(part) for part in raw_path.parts)).absolute()

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
