"""
Download module for the console.
"""

from typing import List

from spotdl.download.downloader import Downloader
from spotdl.utils.search import get_simple_songs

__all__ = ["download"]


def download(
    query: List[str],
    downloader: Downloader,
) -> None:
    """
    Find songs with the provided audio provider and save them to the disk.

    ### Arguments
    - query: list of strings to search for.
    """

    # Parse the query
    songs = get_simple_songs(
        query,
        use_ytm_data=downloader.settings["ytm_data"],
        playlist_numbering=downloader.settings["playlist_numbering"],
        albums_to_ignore=downloader.settings["ignore_albums"],
        album_type=downloader.settings["album_type"],
        playlist_retain_track_cover=downloader.settings["playlist_retain_track_cover"],
    )

    # Download the songs
    downloader.download_multiple_songs(songs)
