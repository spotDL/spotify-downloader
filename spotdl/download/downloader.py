from os import remove

from spotdl.download.progressHandlers import    ProgressRootProcess
from spotdl.download.downloadProcesses import   download_song_to_local, \
                                                convert_song_to_mp3, \
                                                embed_metadata

#! These are just for mypy type checking
from typing import List

from spotdl.download.progressHandlers import DisplayManager, DownloadTracker
from spotdl.common.workers import WorkerPool
from spotdl.search.songObj import SongObj

def download_song(songObj: SongObj, displayManager: DisplayManager = None,
                                    downloadTracker: DownloadTracker = None) -> None:
    
    # download the song
    if displayManager:
        progHook = displayManager.pytube_progress_hook
    else:
        progHook = None

    downloadedPath = download_song_to_local(
        songObj = songObj,
        downloadFolder = '.\\',
        progressHook = progHook
    )

    if downloadedPath == '@!EXISTS':
        if displayManager: displayManager.notify_download_skip()
        if downloadTracker: downloadTracker.notify_download_completion(songObj)

        return None

    # convert song
    convertedPath = convert_song_to_mp3(downloadedPath)

    if displayManager:
        displayManager.notify_conversion_completion()
    
    # clear old files
    remove(downloadedPath)

    # embed metadata
    embed_metadata(songObj, convertedPath)


    if displayManager:
        displayManager.notify_conversion_completion()
    
    if downloadTracker:
        downloadTracker.notify_download_completion()

class DownloadManager():

    def __init__(self, workerPool):
        # start a server for objects shared across processes
        progressRoot = ProgressRootProcess()
        progressRoot.start()

        self.rootProcess = progressRoot

        # initialize shared objects
        self.displayManager  = progressRoot.DisplayManager()
        self.downloadTracker = progressRoot.DownloadTracker()

        self.displayManager.clear()

        # initialize worker pool
        self.workerPool = workerPool
    
    def download_single_song(self, songObj: SongObj) -> None:
        '''
        `songObj` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list([songObj])

        self.displayManager.reset()
        self.displayManager.set_song_count_to(1)

        download_song(songObj, self.displayManager, self.downloadTracker)

        print()
    
    def download_multiple_songs(self, songObjList: List[SongObj]) -> None:
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        RETURNS `~`

        downloads the given songs in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        self.displayManager.reset()
        self.displayManager.set_song_count_to(len(songObjList))

        self.workerPool.do(
            download_song,
            songObjList,
            self.displayManager,
            self.downloadTracker
        )

        print()
    
    def resume_download_from_tracking_file(self, trackingFilePath: str) -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        RETURNS `~`

        downloads songs present on the .spotdlTrackingFile in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_tracking_file(trackingFilePath)

        songObjList = self.downloadTracker.get_song_list()

        self.displayManager.reset()
        self.displayManager.set_song_count_to(len(songObjList))

        self.workerPool.do(
            download_song,
            songObjList,
            self.displayManager,
            self.downloadTracker
        )

        print()
    
    def close(self) -> None:
        '''
        RETURNS `~`

        cleans up across all processes
        '''

        self.displayManager.close()
        self.rootProcess.shutdown()

        self.workerPool.close()
        self.workerPool.join()