"""
Preload module for the console.
"""

import json
import concurrent.futures

from typing import List

from spotdl.download.downloader import Downloader
from spotdl.providers.audio.base import AudioProvider
from spotdl.utils.search import parse_query


def preload(
    query: List[str],
    downloader: Downloader,
    save_path: str,
) -> None:
    """
    Use audio provider to find the download links for the songs
    and save them to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to the file to save the metadata to.

    ### Notes
    - This function is multi-threaded.
    """

    # Parse the query
    songs = parse_query(query, downloader.threads)

    # Initialize the audio provider
    audio_provider: AudioProvider = downloader.audio_provider_class(
        output_directory=downloader.temp_directory,
        output_format=downloader.output_format,
        cookie_file=downloader.cookie_file,
        search_query=downloader.search_query,
        filter_results=downloader.filter_results,
    )

    save_data = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=downloader.threads
    ) as executor:
        future_to_song = {
            executor.submit(audio_provider.search, song): song for song in songs
        }
        for future in concurrent.futures.as_completed(future_to_song):
            song = future_to_song[future]
            try:
                data = future.result()
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

    downloader.progress_handler.log(
        f"Saved {len(save_data)} song{'s' if len(save_data) > 1 else ''} to {save_path}"
    )
