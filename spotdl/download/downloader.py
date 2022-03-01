import json
import datetime
import asyncio
import sys
import concurrent.futures
import traceback

from pathlib import Path
from typing import List, Optional, Tuple

from spotdl.types import Song
from spotdl.utils.ffmpeg import FFmpeg
from spotdl.utils.ffmpeg import FFmpegError
from spotdl.utils.metadata import embed_metadata
from spotdl.utils.formatter import create_file_name
from spotdl.providers.audio.base import AudioProvider
from spotdl.providers.lyrics import Genius, MusixMatch, AzLyrics
from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.providers.audio import YouTube, YouTubeMusic
from spotdl.download.progress_handler import NAME_TO_LEVEL, ProgressHandler
from spotdl.utils.config import get_errors_path, get_temp_path


AUDIO_PROVIDERS = {
    "youtube": YouTube,
    "youtube-music": YouTubeMusic,
}

LYRICS_PROVIDERS = {
    "genius": Genius,
    "musixmatch": MusixMatch,
    "azlyrics": AzLyrics,
}


class DownloaderError(Exception):
    """
    Base class for all exceptions related to downloaders.
    """


class Downloader:
    def __init__(
        self,
        audio_provider: str = "youtube-music",
        lyrics_provider: str = "musixmatch",
        ffmpeg: str = "ffmpeg",
        variable_bitrate: Optional[str] = None,
        constant_bitrate: Optional[str] = None,
        ffmpeg_args: Optional[List] = None,
        output_format: str = "mp3",
        threads: int = 4,
        output: str = ".",
        save_file: Optional[str] = None,
        overwrite: str = "overwrite",
        cookie_file: Optional[str] = None,
        search_query: str = "{artists} - {title}",
        filter_results: bool = True,
        log_level: str = "INFO",
        simple_tui: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initialize the Downloader class.
        """
        audio_provider_class = AUDIO_PROVIDERS.get(audio_provider)
        if audio_provider_class is None:
            raise DownloaderError(f"Invalid audio provider: {audio_provider}")

        lyrics_provider_class = LYRICS_PROVIDERS.get(lyrics_provider)
        if lyrics_provider_class is None:
            raise DownloaderError(f"Invalid lyrics provider: {lyrics_provider}")

        self.temp_directory = get_temp_path()
        if self.temp_directory.exists() is False:
            self.temp_directory.mkdir()

        if loop is None:
            if sys.platform == "win32":
                # ProactorEventLoop is required on Windows to run subprocess asynchronously
                # it is default since Python 3.8 but has to be changed for previous versions
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        # semaphore is required to limit concurrent asyncio executions
        self.semaphore = asyncio.Semaphore(threads)

        # thread pool executor is used to run blocking (CPU-bound) code from a thread
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=threads
        )

        self.output = output
        self.output_format = output_format
        self.save_file = save_file
        self.threads = threads
        self.cookie_file = cookie_file
        self.overwrite = overwrite
        self.search_query = search_query
        self.filter_results = filter_results
        self.audio_provider_name = audio_provider
        self.lyrics_provider_name = lyrics_provider
        self.audio_provider_class = audio_provider_class
        self.lyrics_provider: LyricsProvider = lyrics_provider_class()
        self.ffmpeg = FFmpeg(
            ffmpeg=ffmpeg,
            output_format=output_format,
            variable_bitrate=variable_bitrate,
            constant_bitrate=constant_bitrate,
            ffmpeg_args=["-v", "debug"] if ffmpeg_args is None else ffmpeg_args,
        )

        self.progress_handler = ProgressHandler(NAME_TO_LEVEL[log_level], simple_tui)

        self.progress_handler.debug("Downloader initialized")

    def download_song(self, song: Song) -> None:
        """
        Download a single song.
        """

        self.progress_handler.set_song_count(1)

        self._download_asynchronously([song])

    def download_multiple_songs(
        self, songs: List[Song]
    ) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs to the temp directory.
        After that convert the songs to the output format with ffmpeg.
        And move it to the output directory following the output format.
        Embed metadata to the songs.
        """

        self.progress_handler.set_song_count(len(songs))

        return self._download_asynchronously(songs)

    async def perform_audio_download_async(
        self, song: Song, audio_provider
    ) -> Tuple[Optional[Path], str]:
        """
        Download song to the temp directory.
        """

        if song.download_url is None:
            url = audio_provider.search(song)
            if url is None:
                raise LookupError(
                    f"No results found for song: {song.name} - {song.artist}"
                )
        else:
            url = song.download_url

        # The following function calls blocking code, which would block whole event loop.
        # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
        # is not a problem, since GIL is released for the I/O operations, so it shouldn't
        # hurt performance.
        return (
            await self.loop.run_in_executor(
                self.thread_executor, audio_provider.perform_audio_download, url
            ),
            url,
        )

    async def download_song_async(
        self, song: Song, song_list: List[Song] = None
    ) -> Tuple[Song, Optional[Path]]:
        """
        Download a song to the temp directory.
        After that convert the song to the output format with ffmpeg.
        And move it to the output directory following the output format.
        Embed metadata to the song.

        Returns tuple containing the song object and the path to the song
        if the song was downloaded successfully.
        """

        # Initialize the audio provider
        audio_provider: AudioProvider = self.audio_provider_class(
            output_directory=self.temp_directory,
            output_format=self.output_format,
            cookie_file=self.cookie_file,
            search_query=self.search_query,
            filter_results=self.filter_results,
        )

        # Initalize the progress tracker
        display_progress_tracker = self.progress_handler.get_new_tracker(song)
        audio_provider.add_progress_hook(display_progress_tracker.progress_hook)
        try:
            # Perform the actual download
            try:
                temp_file, url = await self.perform_audio_download_async(
                    song, audio_provider
                )
            except LookupError as exception:
                raise DownloaderError(
                    "LookupError: Couldn't find download URL for song: "
                    f"{song.display_name}"
                ) from exception
            except Exception as exception:
                raise DownloaderError(
                    "DownloaderError: Failed to get audio file for song: "
                    f"{song.display_name}"
                ) from exception

            # Set the song's download url
            song.download_url = url

            # Song failed to download or something went wrong
            if temp_file is None:
                return song, None

            display_progress_tracker.notify_download_complete()

            output_file = create_file_name(
                song, self.output, self.output_format, song_list=song_list
            )
            if output_file.exists() is False:
                output_file.parent.mkdir(parents=True, exist_ok=True)

            # Don't convert m4a files
            # just move the file to the output directory
            if temp_file.suffix == ".m4a" and self.output_format == "m4a":
                temp_file.rename(output_file)
                success = True
                error_message = None
            else:
                success, error_message = await self.ffmpeg.convert(
                    input_file=temp_file,
                    output_file=output_file,
                )
                temp_file.unlink()

            if success is False and error_message:
                # If the conversion failed and there is an error message
                # create a file with the error message
                # and save it in the errors directory
                # raise an exception with file path
                file_name = (
                    get_errors_path() / f"ffmpeg_error_{datetime.date.today()}.txt"
                )
                with open(file_name, "w", encoding="utf-8") as error_path:
                    json.dump(error_message, error_path, ensure_ascii=False, indent=4)

                raise FFmpegError(
                    f"Failed to convert {song.name}, "
                    f"you can find error here: {str(file_name.absolute())}"
                )

            display_progress_tracker.notify_conversion_complete()

            lyrics = self.lyrics_provider.get_lyrics(song.name, song.artists)
            if not lyrics:
                self.progress_handler.debug(
                    f"No lyrics found for {song.name} - {song.artist}"
                )

                lyrics = ""

            try:
                embed_metadata(output_file, song, self.output_format, lyrics)
            except Exception as exception:
                raise DownloaderError(
                    "MetadataError: Failed to embed metadata to the song"
                ) from exception

            display_progress_tracker.notify_complete()

            self.progress_handler.log(f'Downloaded "{song.display_name}": {url}')

            return song, output_file
        except Exception as exception:
            display_progress_tracker.notify_error(traceback.format_exc(), exception)
            return song, None

    def _download_asynchronously(
        self, songs: List[Song]
    ) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs asynchronously.
        """

        tasks = [self.pool_download(song, songs) for song in songs]

        # call all task asynchronously, and wait until all are finished
        return list(self.loop.run_until_complete(asyncio.gather(*tasks)))

    async def pool_download(
        self, song: Song, song_list: List[Song] = None
    ) -> Tuple[Song, Optional[Path]]:
        """
        Run asynchronous task in a pool to make sure that all processes
        don't run at once.
        """

        # tasks that cannot acquire semaphore will wait here until it's free
        # only certain amount of tasks can acquire the semaphore at the same time
        async with self.semaphore:
            return await self.download_song_async(song, song_list)
