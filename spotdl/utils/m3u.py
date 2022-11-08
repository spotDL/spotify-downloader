"""
Module for creating m3u content and writing it to a file.
"""

from typing import List, Optional

from spotdl.types.song import Song
from spotdl.types.playlist import Playlist
from spotdl.types.album import Album
from spotdl.types.artist import Artist
from spotdl.types.saved import Saved
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


def gen_m3u_files(
    query: List[str],
    file_name: Optional[str],
    song_list: List[Song],
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
    - template: the template to use
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

    lists = []
    for request in query:
        if "open.spotify.com" in request and "playlist" in request:
            lists.append(Playlist.create_basic_list(request))
        elif "open.spotify.com" in request and "album" in request:
            lists.append(Album.create_basic_list(request))
        elif "open.spotify.com" in request and "artist" in request:
            lists.append(Artist.create_basic_list(request))
        elif request == "saved":
            lists.append(Saved.create_basic_list())

    if len(lists) == 0 and "{list" in template:
        raise ValueError(
            "You must provide a playlist/album/artist/saved to use {list} in the template."
        )

    # Create a songs list from the lists and the song_list
    songs_lists = []
    for list_obj in lists:
        songs = []
        for song in song_list:
            if song.url in list_obj.urls:
                songs.append(song)

        songs_lists.append((list_obj.name, songs))

    if "{list}" in file_name:
        for list_name, new_song_list in songs_lists:
            create_m3u_file(
                file_name.format(
                    list=list_name,
                ),
                new_song_list,
                template,
                file_extension,
                short,
            )
    elif "{list[" in file_name and "]}" in file_name:
        create_m3u_file(
            file_name.format(list=[list_name for list_name, _ in songs_lists]),
            song_list,
            template,
            file_extension,
            short,
        )
    else:
        create_m3u_file(
            file_name,
            song_list,
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

    print(f"Creating {file_name}...")

    m3u_content = create_m3u_content(song_list, template, file_extension, short)

    with open(file_name, "w", encoding="utf-8") as m3u_file:
        m3u_file.write(m3u_content)

    return m3u_content
