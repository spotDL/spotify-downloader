"""
Sync Lyrics module for the console
"""

import os
from pathlib import Path
from typing import List
from mutagen.easyid3 import ID3, EasyID3
from mutagen.mp4 import MP4
from mutagen.id3 import USLT
from rich.console import Console

from spotdl.providers.lyrics import Genius, AzLyrics, MusixMatch
from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.metadata import M4A_TAG_PRESET


providers: List[LyricsProvider] = [
    Genius(),
    AzLyrics(),
    MusixMatch(),
]


def set_lyrics(path: Path) -> None:
    """
    This function runs when the Lyrics operation is ran on the console.
    It sets the lyrics for the specified song or the songs in the specified path.
    """

    # TODO: Fix issue where if the specified path in console ends with \, path.resolve() adds in a quotation at the end. Raising an error.

    console = Console()
    if path.is_file():
        # Get song data with file metadata
        song_file = EasyID3(str(path.resolve()))
        song_name = song_file.get("title")[0]
        song_artists = parse_artists(song_file.get("artist")[0])
        song_file.save()

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
            with console.status("[bold bright_yellow] Setting lyrics..."):
                if path.name.endswith(".mp3"):
                    song_file = ID3(str(path.resolve()))
                    song_file["USLT::'eng'"] = USLT(
                        encoding=3, lang="eng", desc="desc", text=lyrics
                    )
                    song_file.save(v2_version=3)
                    console.print(
                        f"[bold green]sSuccesfully applied lyrics to [/ bold green] [bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
                    )
                    return None

        console.print(
            f"[bold red]Could not find lyrics for [bold bright_yellow]{song_name}."
        )

    # * Path is a directory

    # Search for music files
    console.print(f"[bold yellow]Looking for songs in {str(path.resolve())}")

    ok_songs = 0
    error_songs = 0
    for filename in os.listdir(str(path.resolve())):

        # * Look for MP3s
        if filename.endswith(".mp3"):
            # Get song data with file metadata

            song_path = os.path.join(str(path.resolve()), filename)

            song_file = EasyID3(song_path)
            song_name = song_file.get("title")[0]
            song_artists = parse_artists(song_file.get("artist")[0])

            song_file.save()

            lyrics = None

            with console.status(
                f"[bold]Getting lyrics for [bold green]{song_name}[/bold green][/bold] by [bold green]{song_artists[0]}[/bold green]"
            ):
                for provider in providers:
                    lyrics = provider.get_lyrics(name=song_name, artists=song_artists)

                    if lyrics is None:
                        continue

                    break

            if lyrics is not None:
                with console.status("[bold bright_yellow]Setting lyrics..."):
                    song_file = ID3(str(path.resolve()))
                    song_file["USLT::'eng'"] = USLT(
                        encoding=3, lang="eng", desc="desc", text=lyrics
                    )
                    song_file.save(v2_version=3)

                ok_songs += 1
                console.print(
                    f"[bold green]Succesfully applied lyrics to [/ bold green][bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
                )
                continue

            # * Could not find lyrics for that mp3
            error_songs += 1
            console.print(
                f"[bold red]Could not find lyrics for [bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
            )

        # * M4A files
        elif filename.endswith(".m4a"):

            song_file = MP4(os.path.join(str(path.resolve()), filename))
            song_name = song_file[M4A_TAG_PRESET["title"]][0]
            song_artists = song_file[M4A_TAG_PRESET["artist"]]

            song_file.save()

            lyrics = None
            with console.status(
                f"[bold]Getting lyrics for [bold green]{song_name}[/bold green][/bold] by [bold green]{song_artists[0]}[/bold green]"
            ):
                for provider in providers:
                    lyrics = provider.get_lyrics(name=song_name, artists=song_artists)

                    if lyrics is None:
                        continue

                    break

            if lyrics is not None:
                with console.status("[bold bright_yellow]Setting lyrics..."):
                    song_file = MP4(os.path.join(str(path.resolve()), filename))

                    song_file[M4A_TAG_PRESET["lyrics"]] = lyrics
                    song_file.save()

                    ok_songs += 1
                    console.print(
                        f"[bold green]Succesfully applied lyrics to [/ bold green][bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
                    )
                continue

            # * Could not find lyrics for that m4a
            error_songs += 1
            console.print(
                f"[bold red]Could not find lyrics for [bold bright_yellow]{song_name}[/bold bright_yellow] by [bold bright_yellow]{song_artists[0]}[/bold bright_yellow]."
            )

    # * Runs at the end of all files in the dir.

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
