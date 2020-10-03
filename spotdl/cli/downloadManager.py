'''
Everything that has to do with multi-file is in this file. 
This library is completely optional to the base spotDL ecosystem but is apart of the command-line service.
'''


#===============
#=== Imports ===
#===============



# from os import mkdir, remove, system as run_in_shell
# from os.path import join, exists

from multiprocessing import Pool
from multiprocessing.managers import BaseManager

# from spotdl.patches.pyTube import YouTube

# from mutagen.easyid3 import EasyID3, ID3
# from mutagen.id3 import APIC as AlbumCover

from urllib.request import urlopen

#! The following are not used, they are just here for static typechecking with mypy
from typing import List

from spotdl.search.songObj import SongObj
from spotdl.cli.progressHandlers import DownloadTracker, ProgressRootProcess
# from spotdl.cli.progressHandlers import DownloadTracker
from spotdl.download.downloader import download_song



#===========================================================
#=== The Download Manager (the tyrannical boss lady/guy) ===
#===========================================================

class DownloadManager():
    #! Big pool sizes on slow connections will lead to more incomplete downloads
    poolSize = 4

    def __init__(self, DisplayManagerInstance):
        # start a server for objects shared across processes
        ProgressRootProcess.register('DownloadTracker', DownloadTracker)
        # ProgressRootProcess.register('DisplayManager',  DisplayManagerInstance.ProcessDisplayManager)

        progressRoot = ProgressRootProcess()
        progressRoot.start()

        self.rootProcess = progressRoot

        # initialize shared objects
        # self.displayManager  = progressRoot.DisplayManager()
        self.displayManager = DisplayManagerInstance.ProcessDisplayManager()
        self.downloadTracker = progressRoot.DownloadTracker()

        self.displayManager.clear()

        # initialize worker pool
        self.workerPool = Pool( DownloadManager.poolSize )
    
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

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (song, self.displayManager, self.downloadTracker)
                    for song in songObjList
            )
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

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (song, self.displayManager, self.downloadTracker)
                    for song in songObjList
            )
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