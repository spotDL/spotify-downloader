"""
Module for creating m3u content and writing it to a file.
"""

from typing import List
from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name


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
