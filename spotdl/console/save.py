"""
Save module for the console.
"""

import asyncio
import json
import logging
from typing import List

from spotdl.download.downloader import Downloader, DownloaderError
from spotdl.types.song import Song
from spotdl.utils.m3u import gen_m3u_files
from spotdl.utils.search import parse_query

__all__ = ["save"]

logger = logging.getLogger(__name__)


def save(
    query: List[str],
    downloader: Downloader,
) -> None:
    """
    Save metadata from spotify to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.

    ### Notes
    - This function is multi-threaded.
    """

    save_path = downloader.settings["save_file"]
    m3u_file = downloader.settings["m3u"]

    to_stdout = save_path == "-"

    if save_path is None and not to_stdout:
        raise DownloaderError("Save file is not specified")

    # Parse the query
    songs = parse_query(
        query=query,
        threads=downloader.settings["threads"],
        use_ytm_data=downloader.settings["ytm_data"],
        playlist_numbering=downloader.settings["playlist_numbering"],
        playlist_numbering_only=downloader.settings["playlist_numbering_only"],
        album_type=downloader.settings["album_type"],
        playlist_retain_track_cover=downloader.settings["playlist_retain_track_cover"],
    )
    save_data = [song.json for song in songs]

    def process_song(song: Song):
        download_url = None
        if downloader.settings["preload"]:
            try:
                download_url = downloader.search(song)
                if download_url is None:
                    logger.error("Could not find a match for %s", song.display_name)
                    return None

                logger.info("Found url for %s: %s", song.display_name, download_url)
            except Exception as exception:
                logger.error(
                    "%s generated an exception: %s", song.display_name, exception
                )
                return None

        lyrics = None
        try:
            lyrics = downloader.search_lyrics(song)
            if lyrics is None:
                logger.debug(
                    "No lyrics found for %s, lyrics providers: %s",
                    song.display_name,
                    ", ".join(
                        [lprovider.name for lprovider in downloader.lyrics_providers]
                    ),
                )
        except Exception as exception:
            logger.debug("Could not search for lyrics: %s", exception)

        return {**song.json, "download_url": download_url, "lyrics": lyrics}

    async def pool_worker(song: Song):
        async with downloader.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            return await downloader.loop.run_in_executor(None, process_song, song)

    tasks = [pool_worker(song) for song in songs]

    # call all task asynchronously, and wait until all are finished
    save_data = list(downloader.loop.run_until_complete(asyncio.gather(*tasks)))

    if to_stdout:
        # Print the songs to stdout
        print(json.dumps(save_data, indent=4, ensure_ascii=False))
    elif save_path:
        # Save the songs to a file
        with open(save_path, "w", encoding="utf-8") as save_file:
            json.dump(save_data, save_file, indent=4, ensure_ascii=False)

    if m3u_file:
        gen_m3u_files(
            songs,
            m3u_file,
            downloader.settings["output"],
            downloader.settings["format"],
            downloader.settings["restrict"],
            False,
        )

    if not to_stdout:
        logger.info(
            "Saved %s song%s to %s",
            len(save_data),
            "s" if len(save_data) > 1 else "",
            save_path,
        )
