"""
Save module for the console.
"""

import json

from typing import List, Optional
from pathlib import Path

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.search import parse_query
from spotdl.utils.m3u import gen_m3u_files


def save(
    query: List[str],
    downloader: Downloader,
    save_path: Path,
    m3u_file: Optional[str] = None,
    preload: bool = False,
    **_,
) -> None:
    """
    Save metadata from spotify to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to.
    - m3u_file: Path to the m3u file to save the songs to.
    - preload: If True, preload the songs.

    ### Notes
    - This function is multi-threaded.
    """

    # Parse the query
    songs = parse_query(query, downloader.threads)
    save_data = [song.json for song in songs]

    def process_song(song: Song):
        try:
            data, _ = downloader.search(song)
            if data is None:
                downloader.progress_handler.error(
                    f"Could not find a match for {song.display_name}"
                )

                return None

            downloader.progress_handler.log(
                f"Found url for {song.display_name}: {data}"
            )

            return {**song.json, "download_url": data}
        except Exception as exception:
            downloader.progress_handler.error(
                f"{song} generated an exception: {exception}"
            )

        return None

    async def pool_worker(song: Song):
        async with downloader.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            return await downloader.loop.run_in_executor(
                downloader.thread_executor, process_song, song
            )

    if preload:
        tasks = [pool_worker(song) for song in songs]

        # call all task asynchronously, and wait until all are finished
        save_data = list(
            downloader.loop.run_until_complete(downloader.aggregate_tasks(tasks))
        )

    # Save the songs to a file
    with open(save_path, "w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file, indent=4, ensure_ascii=False)

    if m3u_file:
        gen_m3u_files(
            query, m3u_file, songs, downloader.output, downloader.output_format, False
        )

    downloader.progress_handler.log(
        f"Saved {len(save_data)} song{'s' if len(save_data) > 1 else ''} to {save_path}"
    )
