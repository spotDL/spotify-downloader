import json
import datetime
import asyncio
from shlex import quote
import sys
import concurrent.futures
import traceback

from pathlib import Path
from typing import List, Optional, Tuple

from yt_dlp.postprocessor.sponsorblock import SponsorBlockPP

from spotdl.types import Song
from spotdl.utils.ffmpeg import FFmpegError, convert_sync
from spotdl.utils.metadata import embed_metadata, MetadataError
from spotdl.utils.formatter import create_file_name, restrict_filename
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
    def __init__(
        self,
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
        search_query: str = "{artists} - {title}",
        log_level: str = "INFO",
        simple_tui: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        restrict: bool = False,
        print_errors: bool = False,
        sponsor_block: bool = False,
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
        self.ffmpeg = ffmpeg
        self.variable_bitrate = variable_bitrate
        self.constant_bitrate = constant_bitrate
        self.ffmpeg_args = ffmpeg_args
        self.restrict = restrict
        self.print_errors = print_errors
        self.errors: List[str] = []
        self.sponsor_block = sponsor_block
        self.lyrics_provider: LyricsProvider = lyrics_provider_class()
        self.progress_handler = ProgressHandler(NAME_TO_LEVEL[log_level], simple_tui)
        self.audio_provider: AudioProvider = self.audio_provider_class(
            output_directory=self.temp_directory,
            output_format=self.output_format,
            cookie_file=self.cookie_file,
            search_query=self.search_query,
            filter_results=self.filter_results,
        )

        self.progress_handler.debug("Downloader initialized")

    def download_song(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Download a single song.
        """

        self.progress_handler.set_song_count(1)

        results = self._download_asynchronously([song])

        if self.print_errors:
            for error in self.errors:
                self.progress_handler.error(error)

        return results[0]

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

        results = self._download_asynchronously(songs)

        if self.print_errors:
            for error in self.errors:
                self.progress_handler.error(error)

        return results

    def _download_asynchronously(
        self, songs: List[Song]
    ) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs asynchronously.
        """

        tasks = [self.pool_download(song) for song in songs]

        # call all task asynchronously, and wait until all are finished
        return list(self.loop.run_until_complete(asyncio.gather(*tasks)))

    async def pool_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Run asynchronous task in a pool to make sure that all processes
        don't run at once.
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

    def search_and_download(self, song: Song) -> Tuple[Song, Optional[Path]]:
        """
        Search for the song and download it.
        """

        # Check if we have all the metadata
        # and that the song object is not a placeholder
        # If it's None extract the current metadata
        # And reinitialize the song object
        if song.name is None and song.url:
            data = song.json
            new_data = Song.from_url(data["url"]).json
            data.update((k, v) for k, v in new_data.items() if v is not None)
            song = Song(**data)

        # Create the output file path
        output_file = create_file_name(song, self.output, self.output_format)

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
            # Search for the download url if it's none
            if song.download_url is None:
                url = self.audio_provider.search(song)
                if url is None:
                    raise LookupError(
                        f"No results found for song: {song.name} - {song.artist}"
                    )
            else:
                url = song.download_url

            # Get the download metadata using yt-dlp
            download_info = self.audio_provider.get_download_metadata(url)

            if download_info is None:
                self.progress_handler.debug(
                    f"No download info found for {song.display_name}, url: {url}"
                )
                raise LookupError(
                    f"yt-dlp failed to get metadata for: {song.name} - {song.artist}"
                )

            self.progress_handler.debug(
                f"Downloading {song.display_name} using {url}, "
                f"actual url: {download_info['url']}, format: {download_info['format']}"
            )

            if self.sponsor_block:
                post_processor = SponsorBlockPP(
                    self.audio_provider.audio_handler, SPONSOR_BLOCK_CATEGORIES
                )
                _, download_info = post_processor.run(download_info)
                chapters = download_info["sponsorblock_chapters"]
                if len(chapters) > 0:
                    self.progress_handler.debug(
                        f"Found {len(chapters)} SponsorBlock chapters for {song.display_name}"
                    )
                    self.progress_handler.debug(f"Chapters: {chapters}")
                    skip_args = ""
                    for chapter in chapters:
                        skip_args += '''-af "aselect='not(between(t, {}, {}))', asetpts=N/SR/TB"'''.format(
                            chapter["start_time"], chapter["end_time"]
                        )

                    if self.ffmpeg_args is None:
                        self.ffmpeg_args = skip_args
                    else:
                        self.ffmpeg_args += " " + skip_args

            success, result = convert_sync(
                (download_info["url"], download_info["ext"]),
                output_file,
                self.ffmpeg,
                self.output_format,
                self.variable_bitrate,
                self.constant_bitrate,
                self.ffmpeg_args,
                display_progress_tracker.progress_hook,
            )

            if not success and result:
                # If the conversion failed and there is an error message
                # create a file with the error message
                # and save it in the errors directory
                # raise an exception with file path
                file_name = (
                    get_errors_path() / f"ffmpeg_error_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
                )
                with open(file_name, "w", encoding="utf-8") as error_path:
                    json.dump(result, error_path, ensure_ascii=False, indent=4)

                raise FFmpegError(
                    f"Failed to convert {song.display_name}, "
                    f"you can find error here: {str(file_name.absolute())}"
                )

            # Set the song's download url
            if song.download_url is None:
                song.download_url = download_info["webpage_url"]

            display_progress_tracker.notify_download_complete()

            lyrics = self.lyrics_provider.get_lyrics(song.name, song.artists) or ""
            if not lyrics:
                self.progress_handler.debug(f"No lyrics found for {song.display_name}")

            try:
                embed_metadata(output_file, song, self.output_format, lyrics)
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
