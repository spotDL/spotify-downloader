"""
Save module for the console.
"""

import json

from typing import List, Optional
from pathlib import Path

from spotdl.download.downloader import Downloader
from spotdl.utils.search import parse_query
from spotdl.utils.m3u import create_m3u_file


def save(
    query: List[str],
    downloader: Downloader,
    save_path: Path,
    m3u_file: Optional[str] = None,
) -> None:
    """
    Save metadata from spotify to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to.
    - m3u_file: Path to the m3u file to save the songs to.

    ### Notes
    - This function is multi-threaded.
    """

    # Parse the query
    songs = parse_query(query, downloader.threads)

    # Convert the songs to JSON
    save_data = [song.json for song in songs]

    # Save the songs to a file
    with open(save_path, "w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file, indent=4, ensure_ascii=False)

    # Create an m3u file if requested
    if m3u_file:
        create_m3u_file(
            m3u_file, songs, downloader.output, downloader.output_format, False
        )

    downloader.progress_handler.log(
        f"Saved {len(save_data)} song{'s' if len(save_data) > 1 else ''} to {save_path}"
    )
