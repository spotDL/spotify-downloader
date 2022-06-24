"""
Sync module for the console.
"""

import json

from pathlib import Path
from typing import List, Optional

from spotdl.download.downloader import Downloader
from spotdl.utils.search import parse_query
from spotdl.utils.formatter import create_file_name
from spotdl.utils.m3u import create_m3u_file
from spotdl.types.song import Song


def sync(
    query: List[str],
    downloader: Downloader,
    save_path: Optional[Path] = None,
    m3u_file: Optional[str] = None,
    **_,
) -> None:
    """
    Sync function for the console.
    It will download the songs and remove the ones that are no longer
    present in the playlists/albums/etc


    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to.
    - m3u_file: Path to the file to save the metadata to.
    """

    downloader.save_file = None

    # Query and save file
    # Create initial sync file
    if query and save_path:
        if any(req for req in query if req.endswith(".spotdl")):
            # If the query contains a .spotdl file, and we are about to create
            # .spotdl file, raise an error.
            raise ValueError(
                "Cannot create a sync file with a .spotdl file in the query."
            )

        # Parse the query
        songs_list = parse_query(query, downloader.threads)

        # Create sync file
        with open(save_path, "w", encoding="utf-8") as save_file:
            json.dump(
                {
                    "type": "sync",
                    "query": query,
                    "songs": [song.json for song in songs_list],
                },
                save_file,
                indent=4,
                ensure_ascii=False,
            )

        # Perform initial download
        downloader.download_multiple_songs(songs_list)

        if m3u_file:
            create_m3u_file(
                m3u_file, songs_list, downloader.output, downloader.output_format, False
            )

        return None

    # If the query is a single file, download it
    if len(query) == 1 and query[0].endswith(".spotdl") and not save_path:
        # Load the sync file
        with open(query[0], "r", encoding="utf-8") as sync_file:
            sync_data = json.load(sync_file)

        # Verify the sync file
        if sync_data.get("type") != "sync":
            raise ValueError("Sync file is not a valid sync file.")

        # Parse the query
        songs_list = parse_query(sync_data["query"], downloader.threads)

        # Get all the old files based on the songs from sync file
        old_files = [
            create_file_name(Song(**song), downloader.output, downloader.output_format)
            for song in sync_data["songs"]
        ]

        # Get all output file names
        new_files = [
            create_file_name(song, downloader.output, downloader.output_format)
            for song in songs_list
        ]

        # Get all files that are no longer in the song lists
        to_delete = set(old_files) - set(new_files)

        # Delete all files that are no longer in the song lists
        for file in to_delete:
            if file.exists():
                downloader.progress_handler.log(f"Deleting {file}")
                file.unlink()
            else:
                downloader.progress_handler.debug(f"{file} does not exist.")

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
            return None

        if m3u_file:
            create_m3u_file(
                m3u_file,
                songs_list,
                downloader.output,
                downloader.output_format,
                False,
            )

        with open(query[0], "w", encoding="utf-8") as save_file:
            json.dump(
                {
                    "type": "sync",
                    "query": sync_data["query"],
                    "songs": [song.json for song in songs_list],
                },
                save_file,
                indent=4,
                ensure_ascii=False,
            )

        downloader.download_multiple_songs(to_download)

        return None

    raise ValueError(
        "Wrong combination of arguments. "
        "Either provide a query and a save path. Or a single sync file in the query"
    )
