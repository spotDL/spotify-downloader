import asyncio
import concurrent.futures
from pathlib import Path

from typing import List, Optional, Tuple

from spotdl.utils.spotify import SpotifyClient
from spotdl.console import console_entry_point
from spotdl.utils.query import parse_query
from spotdl.download import Downloader
from spotdl.types import Song
from spotdl._version import __version__


class Spotdl:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        cache_path: Optional[str] = None,
        no_cache: bool = False,
        headless: bool = False,
        audio_provider: str = "youtube-music",
        lyrics_provider: str = "musixmatch",
        ffmpeg: str = "ffmpeg",
        variable_bitrate: Optional[str] = None,
        constant_bitrate: Optional[str] = None,
        ffmpeg_args: Optional[str] = None,
        output_format: str = "mp3",
        threads: int = 4,
        output: str = ".",
        save_file: Optional[str] = None,
        overwrite: str = "skip",
        cookie_file: Optional[str] = None,
        filter_results: bool = True,
        search_query: str = "{artist} - {title}",
        log_level: str = "INFO",
        simple_tui: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        restrict: bool = False,
        print_errors: bool = False,
    ):
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
            audio_provider=audio_provider,
            search_query=search_query,
            lyrics_provider=lyrics_provider,
            ffmpeg=ffmpeg,
            variable_bitrate=variable_bitrate,
            constant_bitrate=constant_bitrate,
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
        )

    def get_download_urls(self, songs: List[Song]) -> List[Optional[str]]:
        """
        Get the download urls for a list of songs.
        """

        urls = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.downloader.threads
        ) as executor:
            future_to_song = {
                executor.submit(self.downloader.audio_provider.search, song): song
                for song in songs
            }
            for future in concurrent.futures.as_completed(future_to_song):
                song = future_to_song[future]
                try:
                    data = future.result()
                    urls.append(data)
                except Exception as exc:
                    self.downloader.progress_handler.error(
                        f"{song} generated an exception: {exc}"
                    )

        return urls

    def download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Download and convert song to the output format.
        """

        return self.downloader.download_song(song)

    def download_songs(self, songs: List[Song]) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download and convert songs to the output format.
        """

        return self.downloader.download_multiple_songs(songs)
