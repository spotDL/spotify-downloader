'''
Everything that has to do with multi-processing is in this file. 
'''


#===============
#=== Imports ===
#===============

# Switch to multiprocess (not multiprocessING) for better support
# import multiprocessing
# from multiprocessing import Pool
# from multiprocessing.managers import BaseManager
import multiprocess
from multiprocess import Pool
from multiprocess.managers import BaseManager

#! The following are not used, they are just here for static typechecking with mypy
from typing import List

from spotdl.download.downloader import download_song
from spotdl.search.songObj import SongObj
from spotdl.download.progressHandlers import DownloadTracker
from spotdl.download.messageHandlers import ParentMessageTracker


from queue import Queue
# from multiprocessing import Queue
import sys
import time




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
queue =  Queue()
ProgressRootProcess.register('MessageQueue', callable=lambda: queue)
ProgressRootProcess.register('ParentMessageTracker', ParentMessageTracker)

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
        
        self.parentMessageTracker = progressRoot.ParentMessageTracker(self.messageQueue)
        self.downloadTracker = progressRoot.DownloadTracker()

        self.progressRoot = progressRoot

        # initialize worker pool
        self.workerPool = Pool( DownloadManager.poolSize )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
    
    def download_single_song_async(self, songObj: List[SongObj], callback = None) -> None:
        '''
        `songObj` `song` : song to be downloaded

        RETURNS `~`

        downloads the given song
        '''
        self.parentMessageTracker.set_song_count_to(1)
        self.downloadTracker.clear()
        self.downloadTracker.load_song_list([songObj])

        # download_song(songObj, self.parentMessageTracker.newMessageTracker(songObj.get_song_name()), self.downloadTracker)
        results = self.workerPool.apply_async(
            func     = download_song,
            args     = (
                songObj, self.parentMessageTracker.newMessageTracker(songObj.get_display_name()), self.downloadTracker
            )
        )

        if callback:
            callback(results, self.messageQueue)
            return
        elif self.asyncResultCallback:
            self.asyncResultCallback(results)

        return results
    
    def download_multiple_songs_async(self, songObjList: List[SongObj], callback = None):
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        `function` `cb` : (optional) Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argument.

        RETURNS `multiprocessing.pool.AsyncResult`

        downloads the given songs in parallel and returns an multiprocessing.pool.AsyncResult once the pool has been initiated
        '''
        self.parentMessageTracker.set_song_count_to(len(songObjList))
        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        # async to keep trunk process going
        results = self.workerPool.starmap_async(
            func     = download_song,
            iterable = (
                (songObj, self.parentMessageTracker.newMessageTracker(songObj.get_display_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )

        if callback:
            callback(results, self.messageQueue)
            return
        elif self.asyncResultCallback:
            self.asyncResultCallback(results)

        return results

    def download_multiple_songs_sync(self, songObjList: List[SongObj]):
        '''
        `list<songObj>` `songObjList` : list of songs to be downloaded

        RETURNS `multiprocessing.pool.Result`

        downloads the given songs in parallel and returns once the Pool is complete
        '''
        self.parentMessageTracker.set_song_count_to(len(songObjList))
        self.downloadTracker.clear()
        self.downloadTracker.load_song_list(songObjList)

        results = self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (songObj, self.parentMessageTracker.newMessageTracker(songObj.get_display_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )

        return results
    
    def resume_download_from_tracking_file_async(self, trackingFilePath: str, callback = None) -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        `function` `cb` : (optional) Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argument.

        RETURNS `multiprocessing.pool.AsyncResult`

        downloads songs present on the .spotdlTrackingFile in parallel
        '''

        self.downloadTracker.clear()
        self.downloadTracker.load_tracking_file(trackingFilePath)
        
        songObjList = self.downloadTracker.get_song_list()

        self.parentMessageTracker.set_song_count_to(len(songObjList))

        results = self.workerPool.starmap_async(
            func     = download_song,
            iterable = (
                (songObj, self.parentMessageTracker.newMessageTracker(songObj.get_display_name()), self.downloadTracker)
                    for songObj in songObjList
            )
        )

        if callback:
            callback(results)
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

    def set_callback_to(self, callback):
        '''
        `function` `cb` : Function called after jobs have been submitted to pool with the multiprocessing.pool.AsyncResult as the argument.

        RETURNS `~`

        sets callback function to be called after jobs submitted.
        '''
        self.asyncResultCallback = callback

    def own_result_callback(self, results):
        while not results.ready():
            time.sleep(0.1)
            messages = []
            try:
                for _ in range(self.messageQueue.qsize()):
                    data = self.messageQueue.get(False)
                    messages.append(data)
            except:
                data = None
            print(messages)

        # print(messages)
        results.wait()
        print(results.get())





