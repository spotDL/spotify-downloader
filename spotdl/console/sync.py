import json
import glob
import traceback

from pathlib import Path
from typing import List, Optional

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.query import parse_query
from spotdl.utils.formatter import create_file_name


def sync(
    query: List[str],
    downloader: Downloader,
    m3u_file: Optional[None] = None,
) -> None:
    """
    Get tracks from playlists/albums/tracks and save them to a file.
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
