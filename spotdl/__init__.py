__version__ = "4.0.0"

import concurrent.futures

from pathlib import Path
from typing import List, Optional, Tuple

from spotdl.providers.audio.base import AudioProvider
from spotdl.utils.spotify import SpotifyClient
from spotdl.console import console_entry_point
from spotdl.utils.query import parse_query
from spotdl.download import Downloader
from spotdl.types import Song


class Spotdl:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        audio_provider: str = "youtube-music",
        lyrics_provider: str = "musixmatch",
        ffmpeg: str = "ffmpeg",
        variable_bitrate: str = None,
        constant_bitrate: str = None,
        ffmpeg_args: Optional[List] = None,
        output_format: str = "mp3",
        threads: int = 4,
        output: str = ".",
        save_file: Optional[str] = None,
        overwrite: str = "overwrite",
        cookie_file: Optional[str] = None,
        filter_results: bool = True,
        search_query: str = "{artist} - {title}",
        log_level: str = "INFO",
        simple_tui: bool = False,
    ):
        # Initialize spotify client
        SpotifyClient.init(
            client_id=client_id, client_secret=client_secret, user_auth=user_auth
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
        )

        self.audio_provider = audio_provider

    def get_download_urls(self, songs: List[Song]) -> List[Optional[str]]:
        """
        Search.
        """

        # Initialize the audio provider
        audio_provider: AudioProvider = self.downloader.audio_provider_class(
            output_directory=self.downloader.temp_directory,
            output_format=self.downloader.output_format,
            cookie_file=self.downloader.cookie_file,
            search_query=self.downloader.search_query,
            filter_results=self.downloader.filter_results,
        )

        urls = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.downloader.threads
        ) as executor:
            future_to_song = {
                executor.submit(audio_provider.search, song): song for song in songs
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

    def parse_query(self, query: List[str]) -> List[Song]:
        """
        Parse a list of queries and return a list of Song objects.
        """

        return parse_query(query, self.downloader.threads)

    def download(self, song: Song) -> None:
        """
        Download and convert song to the output format.
        """

        self.downloader.download_song(song)

    async def download_no_convert(self, song: Song) -> Tuple[Optional[Path], str]:
        """
        Download song without converting it.
        """

        # Initialize the audio provider
        audio_provider: AudioProvider = self.downloader.audio_provider_class(
            output_directory=self.downloader.temp_directory,
            output_format=self.downloader.output_format,
            cookie_file=self.downloader.cookie_file,
            search_query=self.downloader.search_query,
            filter_results=self.downloader.filter_results,
        )

        return await self.downloader.perform_audio_download_async(song, audio_provider)

    def download_list(self, songs: List[Song]) -> None:
        """
        Download and convert songs to the output format.
        """

        self.downloader.download_multiple_songs(songs)
