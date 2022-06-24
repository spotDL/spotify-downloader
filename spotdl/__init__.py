"""
Init module for spotdl. This module contains the main entry point for spotdl.
And Spotdl class
"""

import asyncio
import concurrent.futures

from pathlib import Path

from typing import List, Optional, Tuple

from spotdl.utils.spotify import SpotifyClient
from spotdl.console import console_entry_point
from spotdl.download import Downloader
from spotdl.utils.search import parse_query
from spotdl.types import Song
from spotdl._version import __version__


class Spotdl:
    """
    Spotdl class, which simplifies the process of downloading songs from Spotify.

    ```python
    from spotdl import Spotdl

    spotdl = Spotdl(client_id='your-client-id', client_secret='your-client-secret')

    songs = spotdl.search(['joji - test drive',
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT'])

    results = spotdl.download_songs(songs)
    song, path = spotd.download(songs[0])
    ```
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        cache_path: Optional[str] = None,
        no_cache: bool = False,
        headless: bool = False,
        audio_providers: Optional[List[str]] = None,
        lyrics_providers: Optional[List[str]] = None,
        ffmpeg: str = "ffmpeg",
        bitrate: Optional[str] = None,
        ffmpeg_args: Optional[str] = None,
        output_format: str = "mp3",
        threads: int = 4,
        output: str = ".",
        save_file: Optional[str] = None,
        overwrite: str = "skip",
        cookie_file: Optional[str] = None,
        filter_results: bool = True,
        search_query: Optional[str] = None,
        log_level: str = "INFO",
        simple_tui: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        restrict: bool = False,
        print_errors: bool = False,
        sponsor_block: bool = False,
    ):
        """
        Initialize the Spotdl class

        ### Arguments
        - client_id: Spotify client id
        - client_secret: Spotify client secret
        - user_auth: If true, user will be prompted to authenticate
        - cache_path: Path to cache directory
        - no_cache: If true, no cache will be used
        - headless: If true, no browser will be opened
        - audio_providers: The audio providers to use.
        - lyrics_providers: The lyrics providers to use.
        - ffmpeg: The ffmpeg executable to use.
        - variable_bitrate: The variable bitrate to use.
        - constant_bitrate: The constant bitrate to use.
        - ffmpeg_args: The ffmpeg arguments to use.
        - output_format: The output format to use.
        - threads: The number of threads to use.
        - output: The output directory to use.
        - save_file: The save file to use when saving/loading song metadata.
        - overwrite: The overwrite mode to use (force/skip).
        - cookie_file: The cookie file to use for yt-dlp.
        - filter_results: Whether to filter results.
        - search_query: The search query to use.
        - log_level: The log level to use.
        - simple_tui: Whether to use simple tui.
        - loop: The event loop to use.
        - restrict: Whether to restrict the filename to ASCII characters.
        - print_errors: Whether to print errors on exit.
        - sponsor_block: Whether to remove sponsor segments using sponsor block postprocessor.

        ### Notes
        - `search-query` uses the same format as `output`.
        """

        if audio_providers is None:
            audio_providers = ["youtube-music"]

        if lyrics_providers is None:
            lyrics_providers = ["musixmatch"]

        # Initialize spotify client
        SpotifyClient.init(
            client_id=client_id,
            client_secret=client_secret,
            user_auth=user_auth,
            cache_path=cache_path,
            no_cache=no_cache,
            open_browser=not headless,
        )

        # Initialize downloader
        self.downloader = Downloader(
            audio_providers=audio_providers,
            lyrics_providers=lyrics_providers,
            search_query=search_query,
            ffmpeg=ffmpeg,
            bitrate=bitrate,
            ffmpeg_args=ffmpeg_args,
            output_format=output_format,
            threads=threads,
            output=output,
            save_file=save_file,
            overwrite=overwrite,
            cookie_file=cookie_file,
            filter_results=filter_results,
            log_level=log_level,
            simple_tui=simple_tui,
            loop=loop,
            restrict=restrict,
            print_errors=print_errors,
            sponsor_block=sponsor_block,
        )

    def search(self, query: List[str]) -> List[Song]:
        """
        Search for songs.

        ### Arguments
        - query: List of search queries

        ### Returns
        - A list of Song objects

        ### Notes
        - query can be a list of song titles, urls, uris
        """

        return parse_query(query, self.downloader.threads)

    def get_download_urls(self, songs: List[Song]) -> List[Optional[str]]:
        """
        Get the download urls for a list of songs.

        ### Arguments
        - songs: List of Song objects

        ### Returns
        - A list of urls if successful.

        ### Notes
        - This function is multi-threaded.
        """

        urls: List[Optional[str]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.downloader.threads
        ) as executor:
            future_to_song = {
                executor.submit(self.downloader.search, song): song for song in songs
            }
            for future in concurrent.futures.as_completed(future_to_song):
                song = future_to_song[future]
                try:
                    data, _ = future.result()
                    urls.append(data)
                except Exception as exc:
                    self.downloader.progress_handler.error(
                        f"{song} generated an exception: {exc}"
                    )

        return urls

    def download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Download and convert song to the output format.

        ### Arguments
        - song: Song object

        ### Returns
        - A tuple containing the song and the path to the downloaded file if successful.
        """

        return self.downloader.download_song(song)

    def download_songs(self, songs: List[Song]) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download and convert songs to the output format.

        ### Arguments
        - songs: List of Song objects

        ### Returns
        - A list of tuples containing the song and the path to the downloaded file if successful.
        """

        return self.downloader.download_multiple_songs(songs)
