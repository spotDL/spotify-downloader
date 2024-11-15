"""
Sync module for the console.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple

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
        songs_list = parse_query(
            query=query,
            threads=downloader.settings["threads"],
            use_ytm_data=downloader.settings["ytm_data"],
            playlist_numbering=downloader.settings["playlist_numbering"],
            album_type=downloader.settings["album_type"],
            playlist_retain_track_cover=downloader.settings[
                "playlist_retain_track_cover"
            ],
        )

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
                downloader.settings["m3u_output"],
                downloader.settings["format"],
                downloader.settings["restrict"],
                False,
            )

        return None

    # If the query is a single file, download it
    if (  # pylint: disable=R1702
        len(query) == 1  # pylint: disable=R1702
        and query[0].endswith(".spotdl")  # pylint: disable=R1702
        and not save_path  # pylint: disable=R1702
    ):
        # Load the sync file
        with open(query[0], "r", encoding="utf-8") as sync_file:
            sync_data = json.load(sync_file)

        # Verify the sync file
        if (
            not isinstance(sync_data, dict)
            or sync_data.get("type") != "sync"
            or sync_data.get("songs") is None
        ):
            raise ValueError("Sync file is not a valid sync file.")

        # Parse the query
        songs_playlist = parse_query(
            query=sync_data["query"],
            threads=downloader.settings["threads"],
            use_ytm_data=downloader.settings["ytm_data"],
            playlist_numbering=downloader.settings["playlist_numbering"],
            album_type=downloader.settings["album_type"],
            playlist_retain_track_cover=downloader.settings[
                "playlist_retain_track_cover"
            ],
        )

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
            # Rename songs that have "{list-length}", "{list-position}", "{list-name}",
            # in the output path so that we don't have to download them again,
            # and to avoid mangling the directory structure.
            to_rename: List[Tuple[Path, Path]] = []
            to_delete = []
            for path, url in old_files:
                if url not in new_urls:
                    to_delete.append(path)
                else:
                    new_song = songs_playlist[new_urls.index(url)]

                    new_path = create_file_name(
                        Song.from_dict(new_song.json),
                        downloader.settings["output"],
                        downloader.settings["format"],
                        downloader.settings["restrict"],
                    )

                    if path != new_path:
                        to_rename.append((path, new_path))

            # fix later Downloading duplicate songs in the same playlist
            # will trigger a re-download of the song. To fix this we have to copy the song
            # to the new location without removing the old one.
            for old_path, new_path in to_rename:
                if old_path.exists():
                    logger.info("Renaming %s to %s", f"'{old_path}'", f"'{new_path}'")
                    if new_path.exists():
                        old_path.unlink()
                        continue

                    try:
                        old_path.rename(new_path)
                    except (PermissionError, OSError) as exc:
                        logger.debug(
                            "Could not rename temp file: %s, error: %s", old_path, exc
                        )
                else:
                    logger.debug("%s does not exist.", old_path)

                if downloader.settings["sync_remove_lrc"]:
                    lrc_file = old_path.with_suffix(".lrc")
                    new_lrc_file = new_path.with_suffix(".lrc")
                    if lrc_file.exists():
                        logger.debug(
                            "Renaming lrc %s to %s",
                            f"'{lrc_file}'",
                            f"'{new_lrc_file}'",
                        )
                        try:
                            lrc_file.rename(new_lrc_file)
                        except (PermissionError, OSError) as exc:
                            logger.debug(
                                "Could not rename lrc file: %s, error: %s",
                                lrc_file,
                                exc,
                            )
                    else:
                        logger.debug("%s does not exist.", lrc_file)

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

                if downloader.settings["sync_remove_lrc"]:
                    lrc_file = file.with_suffix(".lrc")
                    if lrc_file.exists():
                        logger.debug("Deleting lrc %s", lrc_file)
                        try:
                            lrc_file.unlink()
                        except (PermissionError, OSError) as exc:
                            logger.debug(
                                "Could not remove lrc file: %s, error: %s",
                                lrc_file,
                                exc,
                            )
                    else:
                        logger.debug("%s does not exist.", lrc_file)

            if len(to_delete) == 0:
                logger.info("Nothing to delete...")
            else:
                logger.info("%s old songs were deleted.", len(to_delete))

        if m3u_file:
            gen_m3u_files(
                songs_playlist,
                m3u_file,
                downloader.settings["m3u_output"],
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
