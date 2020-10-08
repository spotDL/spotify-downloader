'''
Everything that has to do with multi-file is in this file. 
This library is completely optional to the base spotDL ecosystem but is apart of the command-line service.
'''


#===============
#=== Imports ===
#===============

# Switch to multiprocess (not multiprocessING) for better support
# from multiprocessing import Pool
# from multiprocessing.managers import BaseManager
from multiprocess import Pool
from multiprocess.managers import BaseManager

from urllib.request import urlopen

#! The following are not used, they are just here for static typechecking with mypy
from typing import List

from spotdl.search.songObj import SongObj
from spotdl.download.progressHandlers import DownloadTracker, ProgressRootProcess
from spotdl.download.downloader import download_song


from queue import Queue
import sys





class BasicDisplayMessenger():
    def __init__(self, message_queue = None):
        print('Subprocess Display Messenger Initialized')
        self.message_queue = message_queue
        self.overallProgress = 0
        self.overallTotal = 100

    def newTracker(self, name):
        return self.Tracker(self, name)
    
    class Tracker():
        def __init__(self, parent, songName):
            self.parent = parent
            self.songName = songName
            self.ID = None
            self.progress = 0
            self.isComplete = False
            print('New Tracker Initialized')
            # self.total = 100

        def notify_download_begin(self, ID: int):
            '''
            `int` `ID` : Process ID of download process

            RETURNS `~`

            Should be called at the beginning of each download
            '''
            self.ID = ID
            self.send_update('Downlod Started')


        def set_song_count_to(self, songCount: int) -> None:
            '''
            `int` `songCount` : number of songs being downloaded

            RETURNS `~`

            sets the size of the progressbar based on the number of songs in the current
            download set
            '''

            #! all calculations are based of the arbitrary choice that 1 song consists of
            #! 100 steps/points/iterations 

            # self.progressBar.total = songCount * 100
            self.parent.overallTotal = songCount * 100
            self.send_update('Song Count now' + str(songCount))

        def notify_download_skip(self) -> None:
            '''
            updates progress bar to reflect a song being skipped
            '''

            # self.progressBar.set_by_percent(100)
            self.progress = 100
            self.isComplete = True
            self.send_update('Skipping')

        def download_progress_hook(self, stream, chunk, bytes_remaining) -> None:
            '''
            Progress hook built according to pytube's documentation. It is called each time
            bytes are read from youtube.
            '''

            #! This will be called until download is complete, i.e we get an overall
            #! self.progressBar.update(90)

            fileSize = stream.filesize

            #! How much of the file was downloaded this iteration scaled put of 90.
            #! It's scaled to 90 because, the arbitrary division of each songs 100
            #! iterations is (a) 90 for download (b) 5 for conversion & normalization
            #! and (c) 5 for ID3 tag embedding
            iterFraction = len(chunk) / fileSize * 90

            # self.progressBar.set_by_incriment(iterFraction)
            self.progress += iterFraction
            self.send_update('Downloding...')

        def notify_download_completion(self) -> None:
            '''
            updates progresbar to reflect a download being completed. 
            '''
            self.progress = 90
            self.send_update('Download Complete, Converting....')
        
        def notify_conversion_completion(self) -> None:
            '''
            updates progresbar to reflect a audio conversion being completed
            '''

            # self.progressBar.set_by_incriment(5)
            self.progress = 95
            self.send_update('Conversion Complete, Tagging...')

        def notify_finished(self):
            self.isComplete = True
            self.progress = 100
            self.send_update('Finished Tagging')
            self.send_update('Done')

        def send_update(self, message):
            print(self.ID, self.songName, int(self.progress), message, flush=True)
            # line = '%s %s %s %s' % (self.ID, self.songName, int(self.progress), message) # \n is now in explicitly in line
            # print >>sys.stderr, line, # Use trailing , to indicate no implicit end-of-line
            # print(line, flush=True)

                
        def close(self) -> None:
            '''
            clean up and exit
            '''

            self.send_update('Leaving Display Manager')

            






#===========================================================
#=== The Download Manager (the tyrannical boss lady/guy) ===
#===========================================================

class DownloadManager():
    #! Big pool sizes on slow connections will lead to more incomplete downloads
    poolSize = 4

    def __init__(self, ProcessDisplayManager = BasicDisplayMessenger):
        # start a server for objects shared across processes

        queue = Queue()
        ProgressRootProcess.register('MessageQueue', callable=lambda: queue)
        ProgressRootProcess.register('ProcessDisplayManager', ProcessDisplayManager)
        progressRoot = ProgressRootProcess()
        progressRoot.start()

        
        # initialize shared objects

        self.messageQueue = progressRoot.MessageQueue()
        self.processDisplayManager = progressRoot.ProcessDisplayManager(self.messageQueue)
        self.downloadTracker = progressRoot.DownloadTracker()

        self.progressRoot = progressRoot

        # initialize worker pool
        self.workerPool = Pool( DownloadManager.poolSize )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
    
    def download_single_song(self, songObj: SongObj) -> None:
        '''
        `songObj` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list([songObj])

        download_song(songObj, self.processDisplayManager.newTracker(songObj.get_song_name()), self.downloadTracker)

        # print()
    
    def download_multiple_songs(self, songObjList: List[SongObj]) -> None:
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        RETURNS `~`

        downloads the given songs in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        # async to keep trunk process going
        return self.workerPool.starmap_async(
            func     = download_song,
            iterable = (
                (songObj, self.processDisplayManager.newTracker(songObj.get_song_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )
        # print()
    
    def resume_download_from_tracking_file(self, trackingFilePath: str) -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        RETURNS `~`

        downloads songs present on the .spotdlTrackingFile in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_tracking_file(trackingFilePath)

        songObjList = self.downloadTracker.get_song_list()

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (songObj, self.processDisplayManager.newTracker(songObj.get_song_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )
        # print()
    
    def close(self) -> None:
        '''
        RETURNS `~`

        cleans up across all processes
        '''

        self.progressRoot.shutdown()

        self.workerPool.close()
        self.workerPool.join()





