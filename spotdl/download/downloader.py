# ===============
# === Imports ===
# ===============
import asyncio
import concurrent.futures
from spotdl.download.embed_metadata import set_id3_data
import sys
import traceback

from pathlib import Path
# ! The following are not used, they are just here for static typechecking with mypy
from typing import List

from pytube import YouTube

from spotdl.download.progressHandlers import DisplayManager, DownloadTracker
from spotdl.search.songObj import SongObj
from spotdl.download import ffmpeg


# ==========================
# === Base functionality ===
# ==========================


# ===========================================================
# === The Download Manager (the tyrannical boss lady/guy) ===
# ===========================================================

class DownloadManager():
    # ! Big pool sizes on slow connections will lead to more incomplete downloads
    poolSize = 4

    def __init__(self):

        # start a server for objects shared across processes
        self.displayManager = DisplayManager()
        self.downloadTracker = DownloadTracker()

        if sys.platform == "win32":
            # ! ProactorEventLoop is required on Windows to run subprocess asynchronously
            # ! it is default since Python 3.8 but has to be changed for previous versions
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)

        self.loop = asyncio.get_event_loop()
        # ! semaphore is required to limit concurrent asyncio executions
        self.semaphore = asyncio.Semaphore(self.poolSize)

        # ! thread pool executor is used to run blocking (CPU-bound) code from a thread
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.poolSize)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.displayManager.close()

    def download_single_song(self, songObj: SongObj, outputFormat: str = "mp3") -> None:
        '''
        `songObj` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list([songObj])

        self.displayManager.set_song_count_to(1)

        self._download_asynchronously([songObj], outputFormat)

    def download_multiple_songs(self, songObjList: List[SongObj], outputFormat: str = "mp3") -> None:
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        RETURNS `~`

        downloads the given songs in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        self.displayManager.set_song_count_to(len(songObjList))

        self._download_asynchronously(songObjList, outputFormat)

    def resume_download_from_tracking_file(self, trackingFilePath: str, outputFormat: str = "mp3") -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        RETURNS `~`

        downloads songs present on the .spotdlTrackingFile in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_tracking_file(trackingFilePath)

        songObjList = self.downloadTracker.get_song_list()

        self.displayManager.set_song_count_to(len(songObjList))

        self._download_asynchronously(songObjList, outputFormat)

    async def download_song(self, songObj: SongObj, outputFormat: str) -> None:
        '''
        `songObj` `songObj` : song to be downloaded
        `str` `outputFormat` : output format

        RETURNS `~`

        Downloads, Converts, Normalizes song & embeds metadata as ID3 tags.
        '''

        dispayProgressTracker = self.displayManager.new_progress_tracker(
            songObj)

        # ! since most errors are expected to happen within this function, we wrap in
        # ! exception catcher to prevent blocking on multiple downloads
        try:

            # ! all YouTube downloads are to .\Temp; they are then converted and put into .\ and
            # ! finally followed up with ID3 metadata tags

            # ! we explicitly use the os.path.join function here to ensure download is
            # ! platform agnostic

            # Create a .\Temp folder if not present
            tempFolder = Path('.', 'Temp')

            if not tempFolder.exists():
                tempFolder.mkdir()

            # build file name of converted file
            artistStr = ''

            # ! we eliminate contributing artist names that are also in the song name, else we
            # ! would end up with things like 'Jetta, Mastubs - I'd love to change the world
            # ! (Mastubs REMIX).mp3' which is kinda an odd file name.
            for artist in songObj.get_contributing_artists():
                if artist.lower() not in songObj.get_song_name().lower():
                    artistStr += artist + ', '

            # make sure that main artist is included in artistStr even if they
            # are in the song name, for example
            # Lil Baby - Never Recover (Lil Baby & Gunna, Drake).mp3
            if songObj.get_contributing_artists()[0].lower() not in artistStr.lower():
                artistStr = songObj.get_contributing_artists()[0] + ', ' + artistStr

            # ! the ...[:-2] is to avoid the last ', ' appended to artistStr
            convertedFileName = artistStr[:-2] + \
                ' - ' + songObj.get_song_name()

            # ! this is windows specific (disallowed chars)
            for disallowedChar in ['/', '?', '\\', '*', '|', '<', '>']:
                if disallowedChar in convertedFileName:
                    convertedFileName = convertedFileName.replace(
                        disallowedChar, '')

            # ! double quotes (") and semi-colons (:) are also disallowed characters but we would
            # ! like to retain their equivalents, so they aren't removed in the prior loop
            convertedFileName = convertedFileName.replace(
                '"', "'").replace(':', '-')

            convertedFilePath = Path(".", f"{convertedFileName}.{outputFormat}")

            # if a song is already downloaded skip it
            if convertedFilePath.is_file():
                if self.displayManager:
                    dispayProgressTracker.notify_download_skip()
                if self.downloadTracker:
                    self.downloadTracker.notify_download_completion(songObj)

                # ! None is the default return value of all functions, we just explicitly define
                # ! it here as a continent way to avoid executing the rest of the function.
                return None

            # download Audio from YouTube
            if dispayProgressTracker:
                youtubeHandler = YouTube(
                    url=songObj.get_youtube_link(),
                    on_progress_callback=dispayProgressTracker.pytube_progress_hook
                )

            else:
                youtubeHandler = YouTube(songObj.get_youtube_link())

            trackAudioStream = youtubeHandler.streams.filter(
                only_audio=True).order_by('bitrate').last()
            if not trackAudioStream:
                print(f"Unable to get audio stream for \"{songObj.get_song_name()}\" "
                      f"by \"{songObj.get_contributing_artists()[0]}\" "
                      f"from video \"{songObj.get_youtube_link()}\"")
                return None

            downloadedFilePathString = await self._download_from_youtube(
                convertedFileName,
                tempFolder,
                trackAudioStream
            )

            if downloadedFilePathString is None:
                return None

            if dispayProgressTracker:
                dispayProgressTracker.notify_youtube_download_completion()

            downloadedFilePath = Path(downloadedFilePathString)

            ffmpeg_success = await ffmpeg.convert(
                trackAudioStream=trackAudioStream,
                downloadedFilePath=downloadedFilePath,
                convertedFilePath=convertedFilePath,
                outputFormat=outputFormat
            )

            if dispayProgressTracker:
                dispayProgressTracker.notify_conversion_completion()

            if ffmpeg_success is False:
                # delete the file that wasn't successfully converted
                convertedFilePath.unlink()
            else:
                # if a file was successfully downloaded, tag it
                set_id3_data(convertedFilePath, songObj, outputFormat)

            # Do the necessary cleanup
            if dispayProgressTracker:
                dispayProgressTracker.notify_download_completion()

            if self.downloadTracker:
                self.downloadTracker.notify_download_completion(songObj)

            # delete the unnecessary YouTube download File
            if downloadedFilePath and downloadedFilePath.is_file():
                downloadedFilePath.unlink()

        except Exception as e:
            tb = traceback.format_exc()
            if dispayProgressTracker:
                dispayProgressTracker.notify_error(e, tb)
            else:
                raise e

    async def _download_from_youtube(self, convertedFileName, tempFolder, trackAudioStream):
        # ! The following function calls blocking code, which would block whole event loop.
        # ! Therefore it has to be called in a separate thread via ThreadPoolExecutor. This
        # ! is not a problem, since GIL is released for the I/O operations, so it shouldn't
        # ! hurt performance.
        return await self.loop.run_in_executor(
            self.thread_executor,
            self._perform_audio_download,
            convertedFileName,
            tempFolder,
            trackAudioStream
        )

    def _perform_audio_download(self, convertedFileName, tempFolder, trackAudioStream):
        # ! The actual download, if there is any error, it'll be here,
        try:
            # ! pyTube will save the song in .\Temp\$songName.mp4 or .webm,
            # ! it doesn't save as '.mp3'
            downloadedFilePath = trackAudioStream.download(
                output_path=tempFolder,
                filename=convertedFileName,
                skip_existing=False
            )
            return downloadedFilePath
        except:  # noqa:E722
            # ! This is equivalent to a failed download, we do nothing, the song remains on
            # ! downloadTrackers download queue and all is well...
            # !
            # ! None is again used as a convenient exit
            tempFiles = Path(tempFolder).glob(f'{convertedFileName}.*')
            for tempFile in tempFiles:
                tempFile.unlink()
            return None

    async def _pool_download(self, song_obj: SongObj, outputFormat: str):
        # ! Run asynchronous task in a pool to make sure that all processes
        # ! don't run at once.

        # tasks that cannot acquire semaphore will wait here until it's free
        # only certain amount of tasks can acquire the semaphore at the same time
        async with self.semaphore:
            return await self.download_song(song_obj, outputFormat)

    def _download_asynchronously(self, song_obj_list, outputFormat):
        tasks = [self._pool_download(song, outputFormat) for song in song_obj_list]
        # call all task asynchronously, and wait until all are finished
        self.loop.run_until_complete(asyncio.gather(*tasks))
