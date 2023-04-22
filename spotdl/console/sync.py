"""
Sync module for the console.
"""

import json
import logging
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name
from spotdl.utils.m3u import gen_m3u_files
from spotdl.utils.search import parse_query

__all__ = ["sync"]

logger = logging.getLogger(__name__)


def sync(
    query: List[str],
    downloader: Downloader,
) -> None:
    """
    Sync function for the console.
    It will download the songs and remove the ones that are no longer
    present in the playlists/albums/etc


    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    """

    save_path = downloader.settings["save_file"]
    downloader.settings["save_file"] = None

    m3u_file = downloader.settings["m3u"]
    downloader.settings["m3u"] = None

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
        songs_list = parse_query(query, downloader.settings["threads"])

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

        # Create m3u file
        if m3u_file:
            gen_m3u_files(
                songs_list,
                m3u_file,
                downloader.settings["output"],
                downloader.settings["format"],
                downloader.settings["restrict"],
                False,
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
        songs_playlist = parse_query(sync_data["query"], downloader.settings["threads"])

        # Get the names and URLs of previously downloaded songs from the sync file
        old_files = []
        for entry in sync_data["songs"]:
            file_name = create_file_name(
                Song.from_dict(entry),
                downloader.settings["output"],
                downloader.settings["format"],
                downloader.settings["restrict"],
            )
            old_files.append((file_name, entry["url"]))

        new_urls = [song.url for song in songs_playlist]

        # Delete all song files whose URL is no longer part of the latest playlist
        if not downloader.settings["sync_without_deleting"]:
            to_delete = [path for (path, url) in old_files if url not in new_urls]

            for file in to_delete:
                if file.exists():
                    logger.info("Deleting %s", file)
                    try:
                        file.unlink()
                    except (PermissionError, OSError) as exc:
                        logger.debug(
                            "Could not remove temp file: %s, error: %s", file, exc
                        )
                else:
                    logger.debug("%s does not exist.", file)

            if len(to_delete) == 0:
                logger.info("Nothing to delete...")
            else:
                logger.info("%s old songs were deleted.", len(to_delete))

        if m3u_file:
            gen_m3u_files(
                songs_playlist,
                m3u_file,
                downloader.settings["output"],
                downloader.settings["format"],
                downloader.settings["restrict"],
                False,
            )

        # Write the new sync file
        with open(query[0], "w", encoding="utf-8") as save_file:
            json.dump(
                {
                    "type": "sync",
                    "query": sync_data["query"],
                    "songs": [song.json for song in songs_playlist],
                },
                save_file,
                indent=4,
                ensure_ascii=False,
            )

        downloader.download_multiple_songs(songs_playlist)

        return None

    raise ValueError(
        "Wrong combination of arguments. "
        "Either provide a query and a save path. Or a single sync file in the query"
    )
