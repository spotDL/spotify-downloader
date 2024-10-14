"""
Sync Lyrics module for the console
"""

import asyncio
import logging
from pathlib import Path
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.lrc import generate_lrc
from spotdl.utils.metadata import embed_metadata, get_file_metadata
from spotdl.utils.search import QueryError, get_search_results, parse_query, reinit_song

__all__ = ["meta"]

logger = logging.getLogger(__name__)


def meta(query: List[str], downloader: Downloader) -> None:
    """
    This function applies metadata to the selected songs
    based on the file name.
    If song already has metadata, missing metadata is added

    ### Arguments
    - query: list of strings to search for.
    - downloader: Already initialized downloader instance.

    ### Notes
    - This function is multi-threaded.
    """

    # Create a list of all songs from all paths in query
    paths: List[Path] = []
    for path in query:
        test_path = Path(path)
        if not test_path.exists():
            logger.error("Path does not exist: %s", path)
            continue

        if test_path.is_dir():
            for out_format in FFMPEG_FORMATS:
                paths.extend(test_path.glob(f"*.{out_format}"))
        elif test_path.is_file():
            if test_path.suffix.split(".")[-1] not in FFMPEG_FORMATS:
                logger.error("File is not a supported audio format: %s", path)
                continue

            paths.append(test_path)

    def process_file(file: Path):
        # metadata of the file, url is present in the file.
        song_meta = get_file_metadata(file, downloader.settings["id3_separator"])

        # Check if song has metadata
        # and if it has all the required fields
        # if it has all of these fields, we can assume that the metadata is correct
        if song_meta and not downloader.settings["force_update_metadata"]:
            if (
                song_meta.get("artist")
                and song_meta.get("artists")
                and song_meta.get("name")
                and song_meta.get("lyrics")
                and song_meta.get("album_art")
            ):
                logger.info("Song already has metadata: %s", file.name)
                if downloader.settings["generate_lrc"]:
                    lrc_file = file.with_suffix(".lrc")
                    if lrc_file.exists():
                        logger.info("Lrc file already exists for %s", file.name)
                        return None

                    song = Song.from_missing_data(
                        name=song_meta["name"],
                        artists=song_meta["artists"],
                        artist=song_meta["artist"],
                    )

                    generate_lrc(song, file)
                    if lrc_file.exists():
                        logger.info("Saved lrc file for %s", song.display_name)
                    else:
                        logger.info("Could not find lrc file for %s", song.display_name)

                return None

        # Same as above
        if (
            not song_meta
            or None
            in [
                song_meta.get("name"),
                song_meta.get("album_art"),
                song_meta.get("artist"),
                song_meta.get("artists"),
                song_meta.get("track_number"),
            ]
            or downloader.settings["force_update_metadata"]
        ):
            # Song does not have metadata, or it is missing some fields
            # or we are forcing update of metadata
            # so we search for it
            logger.debug("Searching metadata for %s", file.name)
            search_results = get_search_results(file.stem)
            if not search_results:
                logger.error("Could not find metadata for %s", file.name)
                return None

            song = search_results[0]
        else:
            # Song has metadata, so we use it to reinitialize the song object
            # and fill in the missing metadata
            try:
                song = reinit_song(Song.from_missing_data(**song_meta))
            except QueryError:
                logger.error("Could not find metadata for %s", file.name)
                return None

        # Check if the song has lyric
        # if not use downloader to find lyrics
        if song_meta is None or song_meta.get("lyrics") is None:
            logger.debug("Fetching lyrics for %s", song.display_name)
            song.lyrics = downloader.search_lyrics(song)
            if song.lyrics:
                logger.info("Found lyrics for song: %s", song.display_name)
        else:
            song.lyrics = song_meta.get("lyrics")

        # Apply metadata to the song
        embed_metadata(file, song, skip_album_art=downloader.settings["skip_album_art"])

        logger.info("Applied metadata to %s", file.name)

        if downloader.settings["generate_lrc"]:
            lrc_file = file.with_suffix(".lrc")
            if lrc_file.exists():
                logger.info("Lrc file already exists for %s", file.name)
                return None

            generate_lrc(song, file)
            if lrc_file.exists():
                logger.info("Saved lrc file for %s", song.display_name)
            else:
                logger.info("Could not find lrc file for %s", song.display_name)
        return None

    async def pool_worker(file_path: Path) -> None:
        async with downloader.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            await downloader.loop.run_in_executor(None, process_file, file_path)

    tasks = [pool_worker(path) for path in paths]

    # call all task asynchronously, and wait until all are finished
    downloader.loop.run_until_complete(asyncio.gather(*tasks))

    # to re-download the local songs
    if downloader.settings["redownload"]:
        songs_url: List[str] = []
        for file in paths:
            meta_data = get_file_metadata(
                Path(file), downloader.settings["id3_separator"]
            )
            if meta_data and meta_data["url"]:
                songs_url.append(meta_data["url"])

        songs_list = parse_query(
            query=songs_url,
            threads=downloader.settings["threads"],
            use_ytm_data=downloader.settings["ytm_data"],
            playlist_numbering=downloader.settings["playlist_numbering"],
            album_type=downloader.settings["album_type"],
            playlist_retain_track_cover=downloader.settings[
                "playlist_retain_track_cover"
            ],
        )

        downloader.download_multiple_songs(songs_list)
