"""
Sync module for the console.
"""

import glob
import traceback

from pathlib import Path
from typing import List, Optional

from spotdl.download.downloader import Downloader
from spotdl.utils.search import parse_query
from spotdl.utils.formatter import create_file_name
from spotdl.utils.m3u import create_m3u_file


def sync(
    query: List[str],
    downloader: Downloader,
    save_path: Path,
    m3u_file: Optional[str] = None,
) -> None:
    """
    Removes the songs that are no longer present in the list and downloads the new ones.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to.
    - m3u_file: Path to the file to save the metadata to.
    """

    # Parse the query
    songs_list = parse_query(query, downloader.threads)

    if m3u_file:
        create_m3u_file(
            m3u_file, songs_list, downloader.output, downloader.output_format, False
        )

    # Get all files that are in the output directory
    parent_dir = Path(downloader.output).parent
    old_files = [
        Path(file) for file in glob.glob(f"{parent_dir}/*.{downloader.output_format}")
    ]

    # Get all output file names
    new_files = [
        create_file_name(song, downloader.output, downloader.output_format)
        for song in songs_list
    ]

    # Get all files that are no longer in the query
    to_delete = set(old_files) - set(new_files)

    # Delete all files that are no longer in the query
    for file in to_delete:
        file.unlink()

    # Download the rest of the songs
    try:
        to_download = []
        for song in songs_list:
            song_path = create_file_name(
                song, downloader.output, downloader.output_format
            )
            if Path(song_path).exists():
                if downloader.overwrite == "force":
                    downloader.progress_handler.log(f"Overwriting {song.display_name}")
                    to_download.append(song)
            else:
                to_download.append(song)

        if len(to_download) == 0:
            downloader.progress_handler.log("Nothing to do...")
            return

        downloader.download_multiple_songs(to_download)
    except Exception as exception:
        downloader.progress_handler.debug(traceback.format_exc())
        downloader.progress_handler.error(str(exception))
