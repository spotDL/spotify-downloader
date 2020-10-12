'''
Everything that has to do with multi-processing is in this file. 
'''


#===============
#=== Imports ===
#===============

# Switch to multiprocess (not multiprocessING) for better support
# from multiprocessing import Pool
# from multiprocessing.managers import BaseManager
import multiprocess
from multiprocess import Pool, Lock
from multiprocess.managers import BaseManager
import time
from urllib.request import urlopen

#! The following are not used, they are just here for static typechecking with mypy
from typing import List

from spotdl.search.songObj import SongObj
from spotdl.download.progressHandlers import DownloadTracker
from spotdl.download.downloader import download_song


from queue import Queue
import sys
from collections import defaultdict
from datetime import datetime


#===============================================
#=== Enabling work across multiple processes ===
#===============================================

class BasicDisplayMessenger():
    '''
    This Class is an placeholder for the shared message_queue & overall progress information.
    It is also responsible for dispatching Process Trackers.
    '''

    def __init__(self, message_queue, lock = None):
        self.message_queue = message_queue
        self.overallProgress = 0
        self.overallTotal = 100
        self.lock = lock

    def set_song_count_to(self, count: int):
        self.overallTotal = 100 * count
        self.put(0, 'Song Count', count)

    def put(self, ID, name, progress, message = ''):
        '''
        queue -> { (processID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message) } }
        '''

        message = { ID: { 'time': datetime.timestamp(datetime.now()), 'name': name, 'progress': int(progress), 'message': message}}
        self.message_queue.put(message)

    def newMessageTracker(self, name):
        return DownloadMessagesPlugin(self, name)
    
class DownloadMessagesPlugin():
    '''
    A Plugin for handling callback events from the download process. 
    Each function here corresponds to a function that is called throughout the main download process.
    This class handles things such as displayName, processProgress, processMessages, etc.
    A New message Tracker object is created for each download process and passed into it upon creation.
    '''

    def __init__(self, parent, displayName):
        self.parent = parent
        self.displayName = displayName
        self.ID = None
        self.progress = 0
        self.isComplete = False
        # print('New Tracker Initialized')
        # self.total = 100

    def notify_download_begin(self, ID: int):
        '''
        `ID` : `int` Process ID of download process

        RETURNS `~`

        Should be called at the beginning of each download
        '''
        self.ID = ID
        self.send_update('Download Started')


    def set_song_count_to(self, songCount: int) -> None:
        '''
        `songCount` : `int` number of songs being downloaded

        RETURNS `~`

        sets the size of the progressbar based on the number of songs in the current
        download set
        '''

        #! all calculations are based of the arbitrary choice that 1 song consists of
        #! 100 steps/points/iterations 

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

        self.progress += iterFraction
        # if not int(self.progress) % 10:
        self.send_update('Downloading...')

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

        self.progress = 95
        self.send_update('Conversion Complete, Tagging...')

    def notify_finished(self):
        '''
        updates progres to show the process is completed
        '''
        self.isComplete = True
        self.progress = 100
        self.send_update('Finished Tagging')
        time.sleep(0.01) # Or else the messages will not be distinguishable from a timestamp sort
        self.send_update('Done')

    def send_update(self, message = ''):
        '''
        Called everytime the user should be notified.
        This is where the communication information layout is defined.
        queue -> { (processID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message) } }
        '''
        if self.parent.lock:
            self.parent.lock.acquire()
        # self.parent.message_queue.put(line2) #, block=False
        self.parent.put(self.ID, self.displayName, self.progress, message)
        if self.parent.lock:
            self.parent.lock.release()

            
    def close(self) -> None:
        '''
        clean up and exit
        '''

        self.send_update('Leaving Display Manager')



#=================
#=== The Patch ===  https://stackoverflow.com/questions/46779860/multiprocessing-managers-and-custom-classes
#=================
# originalAutoproxy = multiprocessing.managers.AutoProxy
originalAutoproxy = multiprocess.managers.AutoProxy

def patchedAutoproxy(token, serializer, manager=None,
    authkey=None,exposed=None, incref=True, manager_owned=True):
    '''
    A patch to `multiprocessing.managers.AutoProxy`
    '''

    #! we bypass the unwanted key argument here
    return originalAutoproxy(token, serializer, manager, authkey, exposed, incref)

#! Update the Autoproxy definition in multiprocessing.managers package
# multiprocessing.managers.AutoProxy = patchedAutoproxy
multiprocess.managers.AutoProxy = patchedAutoproxy



            
#===============================================
#=== Enabling work across multiple processes ===
#===============================================

#! we actually run displayManagers and downloadTrackers in a separate process and pass
#! reference handles of those objects to various processes. Thats handled by a
#! BaseManager, i.e. this part of the file. Every bit of the above classes is designed
#! to work across multiple processes and work accurately but, this is the part that
#! puts multiprocessing into the picture

# class ProgressRootProcess(multiprocessing.managers.BaseManager): pass
class ProgressRootProcess(multiprocess.managers.BaseManager): pass

ProgressRootProcess.register('DownloadTracker', DownloadTracker)
# ProgressRootProcess.register('DisplayManager',  ProcessDisplayManager)
queue = Queue()
ProgressRootProcess.register('MessageQueue', callable=lambda: queue)
lock = Lock()
ProgressRootProcess.register('Lock', callable=lambda: lock)
ProgressRootProcess.register('ProcessDisplayManager', BasicDisplayMessenger)

#! You can now run the following code to work with both DisplayManagers and
#! DownloadTrackers:
#!
#!          rootProc = progressRootProcess()
#!          rootProc.start()
#!
#!          displayManager  = rootProc.DisplayManager()
#!          downloadTracker = rootProc.DownloadTracker()
#!
#! The returned objects will be instances of AutoProxy but you can use them like a normal
#! DisplayManager or DowloadTracker




#===========================================================
#=== The Download Manager (the tyrannical boss lady/guy) ===
#===========================================================

class DownloadManager():
    #! Big pool sizes on slow connections will lead to more incomplete downloads. Best option is approx. cpu count
    poolSize = 4

    def __init__(self, asyncResultCallback = None):

        if asyncResultCallback:
            self.asyncResultCallback = asyncResultCallback
        else:
            # If no callback is specified, use internal callback logging
            self.asyncResultCallback = self.own_result_callback

        # start a server for objects shared across processes
        progressRoot = ProgressRootProcess()
        progressRoot.start()

        # initialize shared objects

        self.messageQueue = progressRoot.MessageQueue()
        # self.lock = progressRoot.Lock()
        
        self.processDisplayManager = progressRoot.ProcessDisplayManager(self.messageQueue)
        self.downloadTracker = progressRoot.DownloadTracker()

        self.progressRoot = progressRoot

        # initialize worker pool
        self.workerPool = Pool( DownloadManager.poolSize )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
    
    def download_single_song(self, songObj: List[SongObj], cb = None) -> None:
        '''
        `songObj` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        '''
        self.processDisplayManager.set_song_count_to(1)
        self.downloadTracker.clear()
        self.downloadTracker.load_song_list([songObj])

        # download_song(songObj, self.processDisplayManager.newMessageTracker(songObj.get_song_name()), self.downloadTracker)
        results = self.workerPool.apply_async(
            func     = download_song,
            args     = (
                songObj, self.processDisplayManager.newMessageTracker(songObj.get_song_name()), self.downloadTracker
            )
        )

        if cb:
            cb(results)
            return
        elif self.asyncResultCallback:
            self.asyncResultCallback(results)

        return results
    
    def download_multiple_songs(self, songObjList: List[SongObj], cb = None):
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        `function` `cb` : (optional) Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argument.

        RETURNS `multiprocessing.pool.AsyncResult`

        downloads the given songs in parallel
        '''
        self.processDisplayManager.set_song_count_to(len(songObjList))
        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        # async to keep trunk process going
        results = self.workerPool.starmap_async(
            func     = download_song,
            iterable = (
                (songObj, self.processDisplayManager.newMessageTracker(songObj.get_song_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )

        if cb:
            cb(results)
            return
        elif self.asyncResultCallback:
            self.asyncResultCallback(results)

        return results
    
    def resume_download_from_tracking_file(self, trackingFilePath: str, cb = None) -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        `function` `cb` : (optional) Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argument.

        RETURNS `multiprocessing.pool.AsyncResult`

        downloads songs present on the .spotdlTrackingFile in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_tracking_file(trackingFilePath)
        
        songObjList = self.downloadTracker.get_song_list()

        self.processDisplayManager.set_song_count_to(len(songObjList))

        results = self.workerPool.starmap_async(
            func     = download_song,
            iterable = (
                (songObj, self.processDisplayManager.newMessageTracker(songObj.get_song_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )

        if cb:
            cb(results)
            return
        elif self.asyncResultCallback:
            self.asyncResultCallback(results)
    
    def close(self) -> None:
        '''
        RETURNS `~`

        cleans up across all processes
        '''

        self.progressRoot.shutdown()

        self.workerPool.close()
        self.workerPool.join()

    def send_results_to(self, cb):
        '''
        `function` `cb` : Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argement.

        RETURNS `~`

        sets callback function to be called after jobs submitted.
        '''
        self.asyncResultCallback = cb

    def own_result_callback(self, results):
        while not results.ready():
            time.sleep(0.1)
            messages = []
            try:
                for _ in range(queue.qsize()):
                    data = queue.get(False)
                    messages.append(data)
            except:
                data = None
            print(messages)

        # print(messages)
        results.wait()
        print(results.get())





