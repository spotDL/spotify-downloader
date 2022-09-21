"""
Sync Lyrics module for the console
"""

import os
from pathlib import Path
from typing import List, Union, Optional
from mutagen.easyid3 import ID3, EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import USLT
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from rich.console import Console

from spotdl.providers.lyrics import Genius, AzLyrics, MusixMatch
from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.metadata import M4A_TAG_PRESET, TAG_PRESET, embed_metadata
from spotdl.types.song import Song

providers: List[LyricsProvider] = [
    Genius(),
    AzLyrics(),
    MusixMatch(),
]


def set_lyrics(query: List[str], *args, **kwargs) -> None:
    """
    This function runs when the Lyrics operation is ran on the console.
    It sets the lyrics for the specified song or the songs in the specified path.
    """

    # TODO: Fix issue where if the specified path in console ends with \,
    # path.resolve() adds in a quotation at the end. Raising an error.

    console = Console()

    ok_songs = 0
    error_songs = 0

    for location in query:
        path = Path(location)

        if path.is_file():
            song_name, song_artists = get_song_metadata(path)

            if song_name is None:
                console.print(
                    f"[bold red]Could not find metadata for {path.name}. Applying metadata..."
                )
                apply_metadata(path=path, console=console)
                continue

            lyrics = search_lyrics(
                console=console,
                song_name=song_name,
                song_artists=song_artists,
            )

            if lyrics is None:
                error_songs += 1
                console.print(
                    f"[bold red]Could not find lyrics for [bold bright_yellow]{song_name}."
                )
                continue

            apply_lyrics(path=path, console=console, lyrics=lyrics)
            ok_songs += 1
            continue

        # * Path is a directory

        # Search for music files
        console.print(f"[bold yellow]Looking for songs in {str(path.resolve())}")

        for filename in os.listdir(str(path.resolve())):
            song_path = Path(os.path.join(str(path.resolve()), filename))

            song_name, song_artists = get_song_metadata(song_path)

            if song_name is None:
                console.print(
                    f"[bold red]Could not find metadata for {path.name}. Applying metadata..."
                )
                apply_metadata(path, lyrics)
                continue

            lyrics = search_lyrics(
                console=console, song_name=song_name, song_artists=song_artists
            )

            if lyrics is None:
                error_songs += 1
                console.print(
                    f"[bold red]Could not find lyrics for [bold bright_yellow]{song_name}."
                )
                continue

            apply_lyrics(path=song_path, console=console, lyrics=lyrics)
            ok_songs += 1

        # * Runs at the end of all files in the dir. Show a summary of what was done.
        console.print(
            f"Applied lyrics for [bold green]{ok_songs}[/bold green] songs. Couldn't find lyrics for [bold red]{error_songs}[/bold red] songs.\n[bold bright_blue]Total Songs:[/bold bright_blue] {ok_songs + error_songs}"
        )
        return None


def parse_artists(artists: str) -> List[str]:
    """
    Parses the artists from a string into a List.
    """
    artist_list = [artist.strip() for artist in artists.strip().split("/")]
    return artist_list


def search_lyrics(
    console: Console, song_name: str, song_artists: List[str]
) -> Optional[str]:
    """Searches the lyrics for a song with the specified name and artists.

    Parameters
    ----------
    path: Path
        The Path object of the song you want to find the lyrics for.

    console: Console
        The current instance of the console.

    song_name: str
        The name of the song.

    song_artists: List[str]
        A list containing all artists of a song.

    Returns
    -------

    The lyrics of the song or `None` if they could not be found.

    """

    with console.status(
        f"[bold]Getting lyrics for [bold green]{song_name}[/bold green][/bold] by [bold green]{song_artists[0]}[/bold green]"
    ):

        lyrics = None
        for provider in providers:
            lyrics = provider.get_lyrics(name=song_name, artists=song_artists)

            if not lyrics:
                continue

            break

        if lyrics:
            return lyrics

        return None


def apply_lyrics(path: Path, console: Console, lyrics: str):
    """Applies the specified lyrics to the specified file.

    Parameters
    ----------

    path: Path
        The path object of the song to apply the lyrics.

    console: Console
        The current console instance.

    lyrics: str
        The string containing the song lyrics.
    """
    with console.status(
        f"[bold bright_yellow] Setting lyrics to [bold blue]{path.name}[/bold blue]..."
    ):

        #! Function could be refactored to cleaner code tbh

        song_name, song_artists = get_song_metadata(path)

        if path.name.endswith(".mp3"):
            song_file = ID3(str(path.resolve()))

            song_file["USLT::'eng'"] = USLT(
                encoding=3, lang="eng", desc="desc", text=lyrics
            )
            song_file.save(v2_version=3)

        if path.name.endswith(".m4a"):
            song_file = MP4(str(path.resolve()))

            song_file[M4A_TAG_PRESET["lyrics"]] = lyrics

        if path.name.endswith(".flac"):
            song_file = FLAC(str(path.resolve()))

            song_file[TAG_PRESET["lyrics"]] = lyrics

        if path.name.endswith(".opus"):
            song_file = OggOpus(str(path.resolve()))

            song_file[TAG_PRESET["lyrics"]] = lyrics

        if path.name.endswith(".ogg"):
            song_file = OggVorbis(str(path.resolve()))

            song_file[TAG_PRESET["lyrics"]] = lyrics

        # * Show success message
        console.print(
            f"[bold green]Succesfully applied lyrics to [/ bold green][bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
        )


def get_song_metadata(path: Path) -> Union[Optional[str], List[str]]:
    """
    Gets the metadata for the specified song.

    Parameters
    ----------
    path: Path
        The path of the song.

    Returns
    -------
    Union[str, List[str]]
        The name of the song and a list containing the artist names

    Union[None, []]
        None when no song title could be found and an empty list.
    """
    song_name = None
    song_artists = []

    try:
        if path.name.endswith(".mp3"):
            song_file = EasyID3(str(path.resolve()))
            song_name = song_file.get("title")[0]
            song_artists = parse_artists(song_file.get("artist")[0])

            song_file.save()

        if path.name.endswith(".m4a"):
            song_file = MP4(str(path.resolve()))
            song_name = song_file[M4A_TAG_PRESET["title"]][0]
            song_artists = song_file[M4A_TAG_PRESET["artist"]]

            song_file.save()

        if path.name.endswith(".flac"):
            song_file = FLAC(str(path.resolve()))

            song_name = song_file[TAG_PRESET["title"]][0]
            song_artists = song_file[TAG_PRESET["artist"]]

        if path.name.endswith(".opus"):
            song_file = OggOpus(str(path.resolve()))

            song_name = song_file[TAG_PRESET["title"]][0]
            song_artists = song_file[TAG_PRESET["artist"]]

        if path.name.endswith(".ogg"):
            song_file = OggVorbis(str(path.resolve()))

            song_name = song_file[TAG_PRESET["title"]][0]
            song_artists = song_file[TAG_PRESET["artist"]]

        return song_name, song_artists

    except Exception:
        return None, None


def apply_metadata(path: Path, console: Console):
    """Applies the metadata (including lyrics) to the specified song based on filename."""

    # Search for song object
    filename_data = os.path.splitext(str(path.resolve()))
    song_filename = filename_data[0]

    # Remove the dot from the extension
    song_ext = filename_data[1].replace(".", "")

    song_obj = None
    with console.status(
        f"[bold yellow]Searching for song called: [bold bright_blue]{song_filename}[/bold bright_blue]..."
    ):
        #! Might or might not match the actual song
        song_obj = Song.from_search_term(song_filename)

    with console.status(
        f"[bold yellow]Embedding data from [bold bright_blue]{song_obj.name}[/bold bright_blue] by [bold bright_blue]{song_obj.artist}[/bold bright_blue] into [bold bright_blue]{path.name}[/ bold bright_blue] "
    ):
        embed_metadata(output_file=path, song=song_obj, file_format=song_ext)

    console.print(
        f"[bold green]Succesfully applied metadata to [bold bright_blue]{path.name}!"
    )
