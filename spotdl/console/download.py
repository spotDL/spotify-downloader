import traceback

from pathlib import Path
from typing import List, Optional

from spotdl.download.downloader import Downloader
from spotdl.utils.query import parse_query
from spotdl.utils.formatter import create_file_name
from spotdl.utils.m3u import create_m3u_file


def download(
    query: List[str],
    downloader: Downloader,
    m3u_file: Optional[None] = None,
) -> None:
    """
    Find matches on youtube, download the songs, and save them to the disk.
    """

    try:
        songs_list = parse_query(query, downloader.threads)

        if m3u_file:
            create_m3u_file(
                m3u_file, songs_list, downloader.output, downloader.output_format, False
            )

        songs = []
        for song in songs_list:
            song_path = create_file_name(
                song, downloader.output, downloader.output_format, song_list=songs_list
            )

            if Path(song_path).exists():
                if downloader.overwrite == "force":
                    downloader.progress_handler.log(f"Overwriting {song.display_name}")
                    songs.append(song)
                else:
                    downloader.progress_handler.warn(
                        f"{song.display_name} already exists."
                    )
            else:
                songs.append(song)

        downloader.download_multiple_songs(songs)
    except Exception as exception:
        downloader.progress_handler.debug(traceback.format_exc())
        downloader.progress_handler.error(str(exception))
