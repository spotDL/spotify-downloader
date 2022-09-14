"""
Sync Lyrics module for the console
"""

from fileinput import filename
import sys
import os
from pathlib import Path

from mutagen.easyid3 import ID3
from mutagen.id3 import USLT

from spotdl.providers.lyrics import Genius, AzLyrics, MusixMatch


# TODO: Get default lyrics provider or ask the user to pass in a provider. Or try with them until one returns the lyrics.
def set_lyrics(path: Path):
    print("set_lyrics ran")

    if path.is_file():
        # (
        #     path.endswith(".mp3")
        #     or path.endswith(".m4a")
        #     or path.endswith(".ogg")
        #     or path.endswith(".flac")
        #     or path.endswith(".opus")
        # ):
        print("is file")

        # Search with filename
        print("getting song lyrics")

        # Song filenames should be in format artist1, artist2 - song name.extension
        # TODO: Possibly search the song metadata and get artitst and song name, and not depend in filename

        filename = os.path.splitext(path.name)[0]
        song_data = filename.split("-")
        print(song_data)

        # Parse song name if there are any hypens in the name of the song
        # TODO: Get song name from the file's metadata.
        song_name = ""
        i = 0
        print("////")
        for entry in song_data:
            print(f"Current entry: {entry}")

            if entry == song_data[0]:
                print("entry is first, element (artists). skip...")
                continue

            if i == 0:
                print("First word of the song, dont add a hypgen before.")
                song_name += entry.strip()
                i += 1
                continue

            song_name += f"-{entry.strip()}"

        song_name.strip()
        artists = [artist.strip() for artist in song_data[0].strip().split(",")]

        print(
            f'Attempting to find lyrics with artists {artists} and song name: "{song_name}"...'
        )

        lyrics = MusixMatch().get_lyrics(name=song_name, artists=artists)

        print(lyrics)
        # if lyrics:
        #     if path.name.endswith(".mp3"):
        #         song_file = ID3(str(path.resolve()))

        #         song_file["USLT::'eng'"] = USLT(
        #             encoding=3, lang="eng", desc="desc", text=lyrics
        #         )

    return None
