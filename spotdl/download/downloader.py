"""
Downloader module, this is where all the downloading pre/post processing happens etc.
"""

import json
import datetime
import asyncio
import shutil
import sys
import concurrent.futures
import traceback

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from yt_dlp.postprocessor.sponsorblock import SponsorBlockPP
from yt_dlp.postprocessor.modify_chapters import ModifyChaptersPP

from spotdl.types import Song
from spotdl.utils.ffmpeg import FFmpegError, convert, get_ffmpeg_path
from spotdl.utils.metadata import embed_metadata, MetadataError
from spotdl.utils.formatter import create_file_name, restrict_filename
from spotdl.providers.audio.base import AudioProvider
from spotdl.providers.lyrics import Genius, MusixMatch, AzLyrics
from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.providers.audio import YouTube, YouTubeMusic
from spotdl.download.progress_handler import NAME_TO_LEVEL, ProgressHandler
from spotdl.utils.config import get_errors_path, get_temp_path


AUDIO_PROVIDERS: Dict[str, Type[AudioProvider]] = {
    "youtube": YouTube,
    "youtube-music": YouTubeMusic,
}

LYRICS_PROVIDERS: Dict[str, Type[LyricsProvider]] = {
    "genius": Genius,
    "musixmatch": MusixMatch,
    "azlyrics": AzLyrics,
}

SPONSOR_BLOCK_CATEGORIES = {
    "sponsor": "Sponsor",
    "intro": "Intermission/Intro Animation",
    "outro": "Endcards/Credits",
    "selfpromo": "Unpaid/Self Promotion",
    "preview": "Preview/Recap",
    "filler": "Filler Tangent",
    "interaction": "Interaction Reminder",
    "music_offtopic": "Non-Music Section",
}


class DownloaderError(Exception):
    """
    Base class for all exceptions related to downloaders.
    """


class Downloader:
    """
    Downloader class, this is where all the downloading pre/post processing happens etc.
    It handles the downloading/moving songs, multthreading, metadata embedding etc.
    """

    def __init__(
        self,
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
        Initialize the Downloader class.

        ### Arguments
        - audio_provider: Audio providers to use.
        - lyrics_provider: The lyrics providers to use.
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
        - if `audio_provider` or `lyrics_provider` is a list, then if no match is found,
            the next provider in the list will be used.
        """

        if audio_providers is None:
            audio_providers = ["youtube-music"]

        if lyrics_providers is None:
            lyrics_providers = ["musixmatch"]

        audio_providers_classes: List[Type[AudioProvider]] = []
        lyrics_providers_classes: List[Type[LyricsProvider]] = []

        for provider in audio_providers:
            new_audio_provider = AUDIO_PROVIDERS.get(provider)
            if new_audio_provider is None:
                raise DownloaderError(f"Invalid audio provider: {provider}")

            audio_providers_classes.append(new_audio_provider)

        if len(audio_providers_classes) == 0:
            raise DownloaderError(
                "No audio providers specified. Please specify at least one."
            )

        for provider in lyrics_providers:
            new_lyrics_provider = LYRICS_PROVIDERS.get(provider)
            if new_lyrics_provider is None:
                raise DownloaderError(f"Invalid lyrics provider: {provider}")

            lyrics_providers_classes.append(new_lyrics_provider)

        if loop is None:
            if sys.platform == "win32":
                # ProactorEventLoop is required on Windows to run subprocess asynchronously
                # it is default since Python 3.8 but has to be changed for previous versions
                self.loop = asyncio.ProactorEventLoop()
            else:
                self.loop = asyncio.new_event_loop()

            asyncio.set_event_loop(self.loop)
        else:
            self.loop = loop

        # semaphore is required to limit concurrent asyncio executions
        self.semaphore = asyncio.Semaphore(threads)

        # thread pool executor is used to run blocking (CPU-bound) code from a thread
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=threads
        )

        # If ffmpeg is the default value and it's not installed
        # try to use the spotdl's ffmpeg
        if ffmpeg == "ffmpeg" and shutil.which("ffmpeg") is None:
            ffmpeg_exec = get_ffmpeg_path()
            if ffmpeg_exec is None:
                raise DownloaderError("ffmpeg is not installed")

            ffmpeg = str(ffmpeg_exec.absolute())

        self.output = output
        self.output_format = output_format
        self.save_file = save_file
        self.threads = threads
        self.cookie_file = cookie_file
        self.overwrite = overwrite
        self.search_query = search_query
        self.filter_results = filter_results
        self.ffmpeg = ffmpeg
        self.bitrate = bitrate
        self.ffmpeg_args = ffmpeg_args
        self.restrict = restrict
        self.print_errors = print_errors
        self.errors: List[str] = []
        self.sponsor_block = sponsor_block
        self.audio_providers_classes = audio_providers_classes
        self.progress_handler = ProgressHandler(NAME_TO_LEVEL[log_level], simple_tui)

        self.lyrics_providers: List[LyricsProvider] = []
        for lyrics_provider_class in lyrics_providers_classes:
            self.lyrics_providers.append(lyrics_provider_class())

        self.progress_handler.debug("Downloader initialized")

    def download_song(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Download a single song.

        ### Arguments
        - song: The song to download.

        ### Returns
        - tuple with the song and the path to the downloaded file if successful.
        """

        self.progress_handler.set_song_count(1)

        results = self.download_multiple_songs([song])

        return results[0]

    def download_multiple_songs(
        self, songs: List[Song]
    ) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs to the temp directory.

        ### Arguments
        - songs: The songs to download.

        ### Returns
        - list of tuples with the song and the path to the downloaded file if successful.
        """

        self.progress_handler.set_song_count(len(songs))

        tasks = [self.pool_download(song) for song in songs]

        # call all task asynchronously, and wait until all are finished
        results = list(self.loop.run_until_complete(self._aggregate_tasks(tasks)))

        if self.print_errors:
            for error in self.errors:
                self.progress_handler.error(error)

        if self.save_file:
            with open(self.save_file, "w", encoding="utf-8") as save_file:
                json.dump([song.json for song, _ in results], save_file, indent=4)

        return results

    async def pool_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Run asynchronous task in a pool to make sure that all processes.

        ### Arguments
        - song: The song to download.

        ### Returns
        - tuple with the song and the path to the downloaded file if successful.

        ### Notes
        - This method calls `self.search_and_download` in a new thread.
        """

        # tasks that cannot acquire semaphore will wait here until it's free
        # only certain amount of tasks can acquire the semaphore at the same time
        async with self.semaphore:
            # The following function calls blocking code, which would block whole event loop.
            # Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
            # is not a problem, since GIL is released for the I/O operations, so it shouldn't
            # hurt performance.
            return await self.loop.run_in_executor(
                self.thread_executor, self.search_and_download, song
            )

    def search(self, song: Song) -> Tuple[str, AudioProvider]:
        """
        Search for a song using all available providers.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - tuple with download url and audio provider if successful.
        """

        audio_providers: List[AudioProvider] = []
        for audio_provider_class in self.audio_providers_classes:
            audio_providers.append(
                audio_provider_class(
                    output_format=self.output_format,
                    cookie_file=self.cookie_file,
                    search_query=self.search_query,
                    filter_results=self.filter_results,
                )
            )

        for audio_provider in audio_providers:
            url = audio_provider.search(song)
            if url:
                return url, audio_provider

            self.progress_handler.debug(
                f"{audio_provider.name} failed to find {song.display_name}"
            )

        raise LookupError(f"No results found for song: {song.display_name}")

    def search_lyrics(self, song: Song) -> str:
        """
        Search for lyrics using all available providers.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - lyrics if successful.
        """

        for lyrics_provider in self.lyrics_providers:
            lyrics = lyrics_provider.get_lyrics(song.name, song.artists)
            if lyrics:
                self.progress_handler.debug(
                    f"Found lyrics for {song.display_name} on {lyrics_provider.name}"
                )
                return lyrics

            self.progress_handler.debug(
                f"{lyrics_provider.name} failed to find lyrics "
                f"for {song.display_name}"
            )

        raise LookupError(f"No lyrics found for song: {song.display_name}")

    def search_and_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Search for the song and download it.

        ### Arguments
        - song: The song to download.

        ### Returns
        - tuple with the song and the path to the downloaded file if successful.

        ### Notes
        - This function is synchronous.
        """

        # Check if we have all the metadata
        # and that the song object is not a placeholder
        # If it's None extract the current metadata
        # And reinitialize the song object
        if song.name is None and song.url:
            data = song.json
            new_data = Song.from_url(data["url"]).json
            data.update((k, v) for k, v in new_data.items() if v is not None)

            if data.get("song_list"):
                # Reinitialize the correct song list object
                data["song_list"] = song.song_list.__class__(**data["song_list"])

            # Reinitialize the song object
            song = Song(**data)

        # Create the output file path
        output_file = create_file_name(song, self.output, self.output_format)
        temp_folder = get_temp_path()

        # Restrict the filename if needed
        if self.restrict is True:
            output_file = restrict_filename(output_file)

        # If the file already exists and we don't want to overwrite it,
        # we can skip the download
        if output_file.exists() and self.overwrite == "skip":
            self.progress_handler.log(f"Skipping {song.display_name}")
            self.progress_handler.overall_completed_tasks += 1
            self.progress_handler.update_overall()
            return song, None

        # Don't skip if the file exists and overwrite is set to force
        if output_file.exists() and self.overwrite == "force":
            self.progress_handler.debug(f"Overwriting {song.display_name}")

        # Initalize the progress tracker
        display_progress_tracker = self.progress_handler.get_new_tracker(song)

        # Create the output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if song.download_url is None:
                url, audio_provider = self.search(song)
            else:
                url = song.download_url
                audio_provider = AudioProvider(
                    output_format=self.output_format,
                    cookie_file=self.cookie_file,
                    search_query=self.search_query,
                    filter_results=self.filter_results,
                )

            self.progress_handler.debug(
                f"Downloading {song.display_name} using {url}, "
                f"audio provider: {audio_provider.name}"
            )

            # Add progress hook to the audio provider
            audio_provider.audio_handler.add_progress_hook(
                display_progress_tracker.yt_dlp_progress_hook
            )

            # Download the song using yt-dlp
            download_info = audio_provider.get_download_metadata(url, download=True)
            temp_file = Path(
                temp_folder / f"{download_info['id']}.{download_info['ext']}"
            )

            if download_info is None:
                self.progress_handler.debug(
                    f"No download info found for {song.display_name}, url: {url}"
                )

                raise LookupError(
                    f"yt-dlp failed to get metadata for: {song.name} - {song.artist}"
                )

            display_progress_tracker.notify_download_complete()

            success, result = convert(
                temp_file,
                output_file,
                self.ffmpeg,
                self.output_format,
                self.bitrate,
                self.ffmpeg_args,
                display_progress_tracker.ffmpeg_progress_hook,
            )

            # Remove the temp file
            if temp_file.exists():
                temp_file.unlink()

            if not success and result:
                # If the conversion failed and there is an error message
                # create a file with the error message
                # and save it in the errors directory
                # raise an exception with file path
                file_name = (
                    get_errors_path()
                    / f"ffmpeg_error_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
                )

                error_message = ""
                for key, value in result.items():
                    error_message += f"### {key}:\n{str(value).strip()}\n\n"

                with open(file_name, "w", encoding="utf-8") as error_path:
                    error_path.write(error_message)

                # Remove the file that failed to convert
                if output_file.exists():
                    output_file.unlink()

                raise FFmpegError(
                    f"Failed to convert {song.display_name}, "
                    f"you can find error here: {str(file_name.absolute())}"
                )

            download_info["filepath"] = str(output_file)

            # Set the song's download url
            if song.download_url is None:
                song.download_url = download_info["webpage_url"]

            display_progress_tracker.notify_conversion_complete()

            if self.sponsor_block:
                post_processor = SponsorBlockPP(
                    audio_provider.audio_handler, SPONSOR_BLOCK_CATEGORIES
                )

                _, download_info = post_processor.run(download_info)
                chapters = download_info["sponsorblock_chapters"]
                if len(chapters) > 0:
                    self.progress_handler.log(
                        f"Removing {len(chapters)} sponsor segments for {song.display_name}"
                    )

                    modify_chapters = ModifyChaptersPP(
                        audio_provider.audio_handler,
                        remove_sponsor_segments=SPONSOR_BLOCK_CATEGORIES,
                    )

                    files_to_delete, download_info = modify_chapters.run(download_info)

                    for file_to_delete in files_to_delete:
                        Path(file_to_delete).unlink()

            try:
                song.lyrics = self.search_lyrics(song)
            except LookupError:
                self.progress_handler.debug(
                    f"No lyrics found for {song.display_name}, "
                    "lyrics providers: "
                    f"{', '.join([lprovider.name for lprovider in self.lyrics_providers])}"
                )

            try:
                embed_metadata(output_file, song, self.output_format)
            except Exception as exception:
                raise MetadataError(
                    "Failed to embed metadata to the song"
                ) from exception

            display_progress_tracker.notify_complete()

            self.progress_handler.log(
                f'Downloaded "{song.display_name}": {song.download_url}'
            )

            return song, output_file
        except Exception as exception:
            display_progress_tracker.notify_error(traceback.format_exc(), exception)
            self.errors.append(
                f"{song.url} - {exception.__class__.__name__}: {exception}"
            )
            return song, None

    @staticmethod
    async def _aggregate_tasks(tasks):
        """
        Aggregate the futures and return the results
        """

        return await asyncio.gather(*(task for task in tasks))
