from typing import List
from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name


def create_m3u_content(
    song_list: List[Song], template: str, file_extension: str, short: bool = False
) -> str:
    """
    Create m3u content and return it as a string.
    """
    text = ""
    for song in song_list:
        text += (
            str(create_file_name(song, template, file_extension, song.song_list, short))
            + "\n"
        )

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
    """

    m3u_content = create_m3u_content(song_list, template, file_extension, short)

    with open(file_name, "w") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
