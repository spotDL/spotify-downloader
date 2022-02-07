import sys
import shutil
import asyncio
import traceback
import concurrent.futures

from pathlib import Path
from yt_dlp import YoutubeDL
from typing import List, Optional

from spotdl.search import SongObject
from spotdl.download.progress_ui_handler import YTDLLogger
from spotdl.download import ffmpeg, set_id3_data, DisplayManager, DownloadTracker
from spotdl.providers.provider_utils import (
    _get_converted_file_path,
    _parse_path_template,
)


class DownloadManager:
    def __init__(self, arguments: Optional[dict] = None):
        # start a server for objects shared across processes
        self.display_manager = DisplayManager()
        self.download_tracker = DownloadTracker()

        if arguments is None:
            arguments = {}

        arguments.setdefault("ffmpeg", "ffmpeg")
        arguments.setdefault("output_format", "mp3")
        arguments.setdefault("download_threads", 4)
        arguments.setdefault("path_template", None)

        if sys.platform == "win32":
            # ! ProactorEventLoop is required on Windows to run subprocess asynchronously
            # ! it is default since Python 3.8 but has to be changed for previous versions
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)

        self.loop = asyncio.get_event_loop()
        # ! semaphore is required to limit concurrent asyncio executions
        self.semaphore = asyncio.Semaphore(arguments["download_threads"])

        # ! thread pool executor is used to run blocking (CPU-bound) code from a thread
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=arguments["download_threads"]
        )

        self.arguments = arguments

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.display_manager.close()

        temp_folder = Path("spotdl-temp")

        if temp_folder.exists():
            shutil.rmtree(temp_folder)

    def download_single_song(self, song_object: SongObject) -> None:
        """
        `song_object` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        """

        self.download_tracker.clear()
        self.download_tracker.load_song_list([song_object])

        self.display_manager.set_song_count_to(1)

        self._download_asynchronously([song_object])

    def download_multiple_songs(self, song_list: List[SongObject]) -> None:
        """
        `list<song_object>` `song_list` : list of songs to be downloaded

        RETURNS `~`

        downloads the given songs in parallel
        """

        self.download_tracker.clear()
        self.download_tracker.load_song_list(song_list)

        self.display_manager.set_song_count_to(len(song_list))

        self._download_asynchronously(song_list)

    def resume_download_from_tracking_file(self, tracking_file_path: str) -> None:
        """
        `str` `tracking_file_path` : path to a .spotdlTrackingFile

        RETURNS `~`

        downloads songs present on the .spotdlTrackingFile in parallel
        """

        self.download_tracker.clear()
        self.download_tracker.load_tracking_file(tracking_file_path)

        song_list = self.download_tracker.get_song_list()

        self.display_manager.set_song_count_to(len(song_list))

        self._download_asynchronously(song_list)

    def _download_asynchronously(self, song_obj_list):
        tasks = [self._pool_download(song) for song in song_obj_list]
        # call all task asynchronously, and wait until all are finished
        self.loop.run_until_complete(asyncio.gather(*tasks))

    async def _pool_download(self, song_obj: SongObject):
        # ! Run asynchronous task in a pool to make sure that all processes
        # ! don't run at once.

        # tasks that cannot acquire semaphore will wait here until it's free
        # only certain amount of tasks can acquire the semaphore at the same time
        async with self.semaphore:
            return await self.download_song(song_obj)

    async def download_song(self, song_object: SongObject) -> None:
        """
        `song_object` `song_object` : song to be downloaded

        RETURNS `~`

        Downloads, Converts, Normalizes song & embeds metadata as ID3 tags.
        """

        display_progress_tracker = self.display_manager.new_progress_tracker(
            song_object
        )

        # ! since most errors are expected to happen within this function, we wrap in
        # ! exception catcher to prevent blocking on multiple downloads
        try:

            # ! all YouTube downloads are to .\Temp; they are then converted and put into .\ and
            # ! finally followed up with ID3 metadata tags

            # ! we explicitly use the os.path.join function here to ensure download is
            # ! platform agnostic

            # Create a spotdl-temp folder if not present
            temp_folder = Path("spotdl-temp")

            if not temp_folder.exists():
                temp_folder.mkdir()

            if self.arguments["path_template"] is not None:
                converted_file_path = _parse_path_template(
                    self.arguments["path_template"],
                    song_object,
                    self.arguments["output_format"],
                )
            else:
                converted_file_path = _get_converted_file_path(
                    song_object, self.arguments["output_format"]
                )

            # if a song is already downloaded skip it
            if converted_file_path.is_file():
                if self.display_manager:
                    display_progress_tracker.notify_download_skip()
                if self.download_tracker:
                    self.download_tracker.notify_download_completion(song_object)

                # ! None is the default return value of all functions, we just explicitly define
                # ! it here as a continent way to avoid executing the rest of the function.
                return None

            converted_file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.arguments["output_format"] == "m4a":
                ytdl_format = "bestaudio[ext=m4a]/bestaudio/best"
            elif self.arguments["output_format"] == "opus":
                ytdl_format = "bestaudio[ext=webm]/bestaudio/best"
            else:
                ytdl_format = "bestaudio"

            # download Audio from YouTube
            audio_handler = YoutubeDL(
                {
                    "format": ytdl_format,
                    "outtmpl": f"{temp_folder}/%(id)s.%(ext)s",
                    "quiet": True,
                    "no_warnings": True,
                    "encoding": "UTF-8",
                    "logger": YTDLLogger(),
                    "progress_hooks": [display_progress_tracker.ytdl_progress_hook]
                    if display_progress_tracker
                    else [],
                }
            )

            try:
                downloaded_file_path_string = await self._perform_audio_download_async(
                    converted_file_path.name.rsplit(".", 1)[0],
                    temp_folder,
                    audio_handler,
                    song_object.youtube_link,
                )
            except Exception:
                print(
                    f'Unable to get audio stream for "{song_object.song_name}" '
                    f'by "{song_object.contributing_artists[0]}" '
                    f'from video "{song_object.youtube_link}"'
                )
                return None

            if downloaded_file_path_string is None:
                return None

            if display_progress_tracker:
                display_progress_tracker.notify_youtube_download_completion()

            downloaded_file_path = Path(downloaded_file_path_string)

            if (
                downloaded_file_path.suffix == ".m4a"
                and self.arguments["output_format"] == "m4a"
            ):
                downloaded_file_path.rename(converted_file_path)
                ffmpeg_success = True
            else:
                ffmpeg_success = await ffmpeg.convert(
                    downloaded_file_path=downloaded_file_path,
                    converted_file_path=converted_file_path,
                    output_format=self.arguments["output_format"],
                    ffmpeg_path=self.arguments["ffmpeg"],
                )

            if display_progress_tracker:
                display_progress_tracker.notify_conversion_completion()

            if ffmpeg_success is False:
                # delete the file that wasn't successfully converted
                converted_file_path.unlink()
            else:
                # if a file was successfully downloaded, tag it
                set_id3_data(
                    converted_file_path, song_object, self.arguments["output_format"]
                )

            # Do the necessary cleanup
            if display_progress_tracker:
                display_progress_tracker.notify_download_completion()

            if self.download_tracker:
                self.download_tracker.notify_download_completion(song_object)

            # delete the unnecessary YouTube download File
            if downloaded_file_path and downloaded_file_path.is_file():
                downloaded_file_path.unlink()

        except Exception as e:
            tb = traceback.format_exc()
            if display_progress_tracker:
                display_progress_tracker.notify_error(e, tb)
            else:
                raise e

    async def _perform_audio_download_async(
        self, converted_file_name, temp_folder, track_audio_stream, youtube_link
    ):
        # ! The following function calls blocking code, which would block whole event loop.
        # ! Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
        # ! is not a problem, since GIL is released for the I/O operations, so it shouldn't
        # ! hurt performance.
        return await self.loop.run_in_executor(
            self.thread_executor,
            self._perform_audio_download,
            converted_file_name,
            temp_folder,
            track_audio_stream,
            youtube_link,
        )

    def _perform_audio_download(
        self, converted_file_name, temp_folder, audio_handler, youtube_link
    ):
        # ! The actual download, if there is any error, it'll be here,
        try:
            data = audio_handler.extract_info(youtube_link)
            # ! This is equivalent to a failed download, we do nothing, the song remains on
            # ! download_trackers download queue and all is well...
            return Path(temp_folder / f"{data['id']}.{data['ext']}")
        except Exception as e:
            temp_files = Path(temp_folder).glob(f"{converted_file_name}.*")
            for temp_file in temp_files:
                temp_file.unlink()
            raise e
