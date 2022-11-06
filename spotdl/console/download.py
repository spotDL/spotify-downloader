"""
Download module for the console.
"""

import json

from typing import List, Optional
from pathlib import Path

from spotdl.download.downloader import Downloader
from spotdl.utils.m3u import gen_m3u_files
from spotdl.utils.search import get_simple_songs
from spotdl.utils.archive import Archive


def download(
    query: List[str],
    downloader: Downloader,
    save_path: Optional[Path] = None,
    m3u_file: Optional[str] = None,
    archive: Optional[str] = None,
    **_
) -> None:
    """
    Find songs with the provided audio provider and save them to the disk.

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.
    - save_path: Path to save the songs to or None.
    - m3u_file: Path to the m3u file to save the songs to.
    """

    # Parse the query
    songs = get_simple_songs(query)

    url_archive: Archive = Archive()
    if archive:
        url_archive.load(archive)
        songs = [song for song in songs if song.url not in url_archive]

    results = downloader.download_multiple_songs(songs)

    if archive:
        for result in results:
            if result[1]:
                url_archive.add(result[0].url)

        url_archive.save(archive)

    if m3u_file:
        song_list = [song for song, _ in results]
        gen_m3u_files(
            query,
            m3u_file,
            song_list,
            downloader.output,
            downloader.output_format,
            False,
        )

    if save_path:
        # Save the songs to a file
        with open(save_path, "w", encoding="utf-8") as save_file:
            json.dump(
                [song.json for song, _ in results],
                save_file,
                indent=4,
                ensure_ascii=False,
            )
