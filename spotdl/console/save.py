"""
Save module for the console.
"""

import json
import concurrent.futures

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
    preload: bool = False,
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

    if preload:
        save_data = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=downloader.threads
        ) as executor:
            future_to_song = {
                executor.submit(downloader.search, song): song for song in songs
            }
            for future in concurrent.futures.as_completed(future_to_song):
                song = future_to_song[future]
                try:
                    data, _ = future.result()
                    if data is None:
                        downloader.progress_handler.error(
                            f"Could not find a match for {song.display_name}"
                        )
                        continue

                    downloader.progress_handler.log(
                        f"Found url for {song.display_name}: {data}"
                    )
                    save_data.append({**song.json, "download_url": data})
                except Exception as exc:
                    downloader.progress_handler.error(
                        f"{song} generated an exception: {exc}"
                    )

    # Save the songs to a file
    with open(save_path, "w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file, indent=4, ensure_ascii=False)

    if m3u_file:
        create_m3u_file(
            m3u_file, songs, downloader.output, downloader.output_format, False
        )

    downloader.progress_handler.log(
        f"Saved {len(save_data)} song{'s' if len(save_data) > 1 else ''} to {save_path}"
    )
