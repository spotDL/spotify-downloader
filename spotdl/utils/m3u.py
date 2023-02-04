"""
Module for creating m3u content and writing it to a file.
"""

from typing import List, Optional

from spotdl.types.song import Song, SongList
from spotdl.utils.formatter import create_file_name

__all__ = [
    "create_m3u_content",
    "gen_m3u_files",
    "create_m3u_file",
]


def create_m3u_content(
    song_list: List[Song], template: str, file_extension: str, short: bool = False
) -> str:
    """
    Create m3u content and return it as a string.

    ### Arguments
    - song_list: the list of songs
    - template: the template to use
    - file_extension: the file extension to use
    - short: whether to use the short version of the template

    ### Returns
    - the m3u content as a string
    """

    text = ""
    for song in song_list:
        text += str(create_file_name(song, template, file_extension, short)) + "\n"

    return text


def gen_m3u_files(
    songs: List[Song],
    file_name: Optional[str],
    template: str,
    file_extension: str,
    short: bool = False,
):
    """
    Create an m3u filename from the query.

    ### Arguments
    - query: the query
    - file_name: the file name to use
    - song_list: the list of songs
    - template: the output file template to use
    - file_extension: the file extension to use
    - short: whether to use the short version of the template
    """

    # If no file name is provided, use the first list's name
    if not file_name:
        file_name = "{list[0]}.m3u"

    # If file_name ends with a slash. Does not have a m3u name with extension
    # at the end of the template, append `{list[0]}`` to it
    if (
        file_name.endswith("/")
        or file_name.endswith(r"\\")
        or file_name.endswith("\\\\")
    ):
        file_name += "/{list[0]}.m3u"

    # Check if the file name ends with .m3u
    if not file_name.endswith(".m3u"):
        file_name += ".m3u"

    # Get song lists from song objects
    dup_lists = [result.song_list for result in songs]

    # Remove duplicates
    list_of_lists: List[SongList] = []
    for song_list in dup_lists:
        if song_list is None:
            continue

        if song_list.url not in [list.url for list in list_of_lists]:
            list_of_lists.append(song_list)

    if "{list}" in file_name:
        # Create multiple m3u files if there are multiple lists
        for song_list in list_of_lists:
            create_m3u_file(
                file_name.format(
                    list=song_list.name,
                ),
                song_list.songs,
                template,
                file_extension,
                short,
            )
    elif "{list[" in file_name and "]}" in file_name:
        # Create a single m3u file for specified song list name
        create_m3u_file(
            file_name.format(list=[song_list.name for song_list in list_of_lists]),
            songs,
            template,
            file_extension,
            short,
        )
    else:
        # Use the provided file name
        create_m3u_file(
            file_name,
            songs,
            template,
            file_extension,
            short,
        )


def create_m3u_file(
    file_name: str,
    song_list: List[Song],
    template: str,
    file_extension: str,
    short: bool = False,
) -> str:
    """
    Create the m3u file.

    ### Arguments
    - file_name: the file name to use
    - song_list: the list of songs
    - template: the template to use
    - file_extension: the file extension to use
    - short: whether to use the short version of the template

    ### Returns
    - the m3u content as a string
    """

    m3u_content = create_m3u_content(song_list, template, file_extension, short)

    with open(file_name, "w", encoding="utf-8") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
