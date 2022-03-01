from typing import List
from spotdl.types.song import Song

from spotdl.utils.formatter import create_file_name


def create_m3u_content(
    songs: List[Song], template: str, file_extension: str, short: bool = False
) -> str:
    """
    Create m3u content and return it as a string.
    """
    text = ""
    for song in songs:
        text += (
            str(
                create_file_name(song, template, file_extension, short, song_list=songs)
            )
            + "\n"
        )

    return text


def create_m3u_file(
    file_name: str,
    songs: List[Song],
    template: str,
    file_extension: str,
    short: bool = False,
) -> str:
    """
    Create the m3u file.
    """

    m3u_content = create_m3u_content(songs, template, file_extension, short)

    with open(file_name, "w") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
