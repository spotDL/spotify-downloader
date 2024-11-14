"""
Module for creating m3u content and writing it to a file.
"""

from pathlib import Path
from typing import Dict, List, Optional

from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name, sanitize_string

__all__ = [
    "create_m3u_content",
    "gen_m3u_files",
    "create_m3u_file",
]


def create_m3u_content(
    song_list: List[Song],
    template: str,
    file_extension: str,
    restrict: Optional[str] = None,
    short: bool = False,
    detect_formats: Optional[List[str]] = None,
) -> str:
    """
    Create m3u content and return it as a string.

    ### Arguments
    - song_list: the list of songs
    - template: the template to use
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template

    ### Returns
    - the m3u content as a string
    """

    text = ""
    for song in song_list:
        if not detect_formats:
            file_name = create_file_name(
                song, template, file_extension, restrict, short
            )

            text += str(file_name) + "\n"
        else:
            for file_ext in detect_formats:
                file_name = create_file_name(song, template, file_ext, restrict, short)
                if file_name.exists():
                    text += str(file_name) + "\n"
                    break
            else:
                file_name = create_file_name(
                    song, template, file_extension, restrict, short
                )

                text += str(file_name) + "\n"

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
    - query: the query
    - file_name: the file name to use
    - song_list: the list of songs
    - template: the output file template to use
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template
    - detect_formats: the formats to detect
    """

    # If no file name is provided, use the first list's name
    if not file_name:
        file_name = "{list[0]}.m3u8"

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

    if "{list}" in file_name:
        # Create multiple m3u files if there are multiple lists
        for list_name, song_list in lists_object.items():
            create_m3u_file(
                file_name.format(
                    list=list_name,
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
            file_name.format(list=list(lists_object.keys())),
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
    )

    file_path = Path(
        *(sanitize_string(part) for part in Path(file_name).parts)
    ).absolute()

    with open(file_path, "w", encoding="utf-8") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
