"""
    Url user friendly module for the console
"""

import asyncio
import logging
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.search import parse_query

__all__ = ["url_user_friendly"]

logger = logging.getLogger(__name__)

def url_user_friendly(
        query: List[str],
        downloader: Downloader,
) -> None:
    """
    Print user friendly yt links for the provided songs

    ### Arguments
    - query: list of strings to search for.
    """
    #Parse de query
    songs = parse_query(
        query=query,
        threads=downloader.settings["threads"],
        use_ytm_data=downloader.settings["ytm_data"],
        playlist_numbering=downloader.settings["playlist_numbering"],
        album_type=downloader.settings["album_type"],
        playlist_retain_track_cover=downloader.settings["playlist_retain_track_cover"],
    )

    def process_song(song: Song):
        try:
            data = downloader.search(song)
            if data is None:
                logger.error("Could not find a match for %s", song.display_name)

                return None

        

            print(data)
        except Exception as exception:
            logger.error("%s generated an exception: %s", song.display_name, exception)

        return None

    async def pool_worker(song: Song):
        async with downloader.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            return await downloader.loop.run_in_executor(None, process_song, song)

    tasks = [pool_worker(song) for song in songs]
    downloader.loop.run_until_complete(asyncio.gather(*tasks))
