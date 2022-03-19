import traceback

from typing import List, Optional

from spotdl.download.downloader import Downloader
from spotdl.utils.m3u import create_m3u_file
from spotdl.utils.query import get_simple_songs


def download(
    query: List[str],
    downloader: Downloader,
    m3u_file: Optional[None] = None,
) -> None:
    """
    Find matches on youtube, download the songs, and save them to the disk.
    """

    try:
        # Parse the query
        songs = get_simple_songs(query)

        results = downloader.download_multiple_songs(songs)

        if m3u_file:
            song_list = [song for song, _ in results]
            create_m3u_file(
                m3u_file, song_list, downloader.output, downloader.output_format, False
            )

    except Exception as exception:
        downloader.progress_handler.debug(traceback.format_exc())
        downloader.progress_handler.error(str(exception))
