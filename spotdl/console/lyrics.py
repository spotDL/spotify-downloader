"""
Sync Lyrics module for the console
"""

import sys
import os
from pathlib import Path
from mutagen.easyid3 import ID3
from mutagen.id3 import USLT

from spotdl.providers.lyrics import Genius, AzLyrics, MusixMatch
from spotdl.providers.lyrics.base import LyricsProvider

from typing import List

providers: List[LyricsProvider] = [
    Genius(),
    AzLyrics(),
    MusixMatch(),
]

# TODO: Get default lyrics provider or ask the user to pass in a provider. Or try with them until one returns the lyrics.
def set_lyrics(path: Path):
    print("Lyrics operation was ran.")

    if path.is_file():
        # (
        #     path.endswith(".mp3")
        #     or path.endswith(".m4a")
        #     or path.endswith(".ogg")
        #     or path.endswith(".flac")
        #     or path.endswith(".opus")
        # ):

        # Search with filename
        print("Getting song lyrics...")
        # Song filenames should be in format artist1, artist2 - song name.extension
        # TODO: Possibly search the song metadata and get artitst and song name, and not depend in filename

        filename = os.path.splitext(path.name)[0]
        song_data = filename.split("-")

        # Parse song name if there are any hypens in the name of the song
        # TODO: Get song name from the file's metadata.
        song_name = ""
        i = 0
        print("////")
        for entry in song_data:

            if entry == song_data[0]:
                continue

            if i == 0:
                song_name += entry.strip()
                i += 1
                continue

            song_name += f"-{entry.strip()}"

        song_name.strip()
        artists = [artist.strip() for artist in song_data[0].strip().split(",")]

        for provider in providers:
            print(
                f'Attempting to find lyrics with artists {artists} and song name: "{song_name}" with {type(provider).__name__}...'
            )

            lyrics = MusixMatch().get_lyrics(name=song_name, artists=artists)

            if not lyrics:
                print("Could not find lyrics. Re trying...")
                continue

            print(lyrics)
            break

        # if lyrics:
        #     if path.name.endswith(".mp3"):
        #         song_file = ID3(str(path.resolve()))

        #         song_file["USLT::'eng'"] = USLT(
        #             encoding=3, lang="eng", desc="desc", text=lyrics
        #         )

    return None
