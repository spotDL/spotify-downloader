"""
Download module for the console.
"""

import json

from typing import List, Optional
from pathlib import Path

from spotdl.download.downloader import Downloader
from spotdl.utils.m3u import create_m3u_file
from spotdl.utils.search import get_simple_songs


def download(
    query: List[str],
    downloader: Downloader,
    save_path: Optional[Path] = None,
    m3u_file: Optional[str] = None,
    **_
) -> None:
    """
    Find songs with the provided audio provider and save them to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to or None.
    - m3u_file: Path to the m3u file to save the songs to.
    """

    # Parse the query
    songs = get_simple_songs(query)

    results = downloader.download_multiple_songs(songs)

    if m3u_file:
        song_list = [song for song, _ in results]
        create_m3u_file(
            m3u_file, song_list, downloader.output, downloader.output_format, False
        )

    if save_path:
        # Save the songs to a file
        with open(save_path, "w", encoding="utf-8") as save_file:
            json.dump(
                [song.json for song in songs], save_file, indent=4, ensure_ascii=False
            )
