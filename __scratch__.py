from spotdl.download.downloader import download_song
from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import initialize
import time

import multiprocess
# multiprocessing.set_start_method('spawn')
import asyncio
from multiprocess import Process, Manager
import multiprocess.managers
from multiprocess.managers import BaseManager, SyncManager
from multiprocess import Pool
from rich.console import Console
# import queue as queue
from queue import Queue
import os

initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
)

songs = ["https://open.spotify.com/track/7fcEMgPlojD0LzPHwMsoic",
         "https://open.spotify.com/track/0elizmA21eSQgorzFxU80l", "https://open.spotify.com/track/6TWjDrdEoFy4YWf2oAsy9s"]


originalAutoproxy = multiprocess.managers.AutoProxy


def patchedAutoproxy(token, serializer, manager=None,
                     authkey=None, exposed=None, incref=True, manager_owned=True):
    '''
    A patch to `multiprocessing.managers.AutoProxy`
    '''

    #! we bypass the unwanted key argument here
    return originalAutoproxy(token, serializer, manager, authkey, exposed, incref)


#! Update the Autoproxy definition in multiprocessing.managers package
multiprocess.managers.AutoProxy = patchedAutoproxy


class Mapping(dict):
    def __init__(self):
        return

    def __setitem__(self, key, item):
        self.__dict__[key] = item

    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        return repr(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __delitem__(self, key):
        del self.__dict__[key]

    def clear(self):
        return self.__dict__.clear()

    def copy(self):
        return self.__dict__.copy()

    def has_key(self, k):
        return k in self.__dict__

    def update(self, *args, **kwargs):
        return self.__dict__.update(*args, **kwargs)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def pop(self, *args):
        return self.__dict__.pop(*args)

    def __cmp__(self, dict_):
        return self.__cmp__(self.__dict__, dict_)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __unicode__(self):
        return unicode(repr(self.__dict__))




def dl(song):
    songObj = SongObj.from_url(song)
    download_song(songObj)


# Syncronous
def sync():
    start = time.time()

    for song in songs:
        songObj = SongObj.from_url(song)
        download_song(songObj)

    end = time.time()
    print("Straight:", end - start)


# Multiprocessing
def multi():
    start = time.time()

    jobs = []
    for song in songs:
        songObj = SongObj.from_url(song)
        p = multiprocess.Process(target=download_song, args=(songObj,))
        jobs.append(p)
        p.start()

    # for proc in procs:
    #     proc.join()

    end = time.time()
    print("Multiprocessed:", end - start)


async def asyncdl(song):
    songObj = SongObj.from_url(song)
    download_song(songObj)


def minidl(songObj, dispmgr):
    # songObj = SongObj.from_url(song)
    download_song(songObj)
    dispmgr.print("Sucessfully downloaded and alerted")


def minidl2(song, dispmgr):
    dispmgr.print((os.getpid(), "Starting Download"))
    songObj = SongObj.from_url(song)
    download_song(songObj)
    # text = str(os.getpid()) + ' - ' + str(text)
    dispmgr.print((os.getpid(), "Sucessfully downloaded and alerted"))


# class MyManager(SyncManager):
#     pass
class ProgressRootProcess(multiprocess.managers.BaseManager):
    pass


class minidlmgr():
    def __init__(self, parentminidisp):
        print('minidlmgr init', parentminidisp.name)
        # start a server for objects shared across processes
        ProgressRootProcess.register('minisubdisp', minisubdisp)
        # MapDict = Mapping()
        ProgressRootProcess.register('dictionary', Mapping)
        
        # q = queue.Queue()
        queue = Queue()
        # ProgressRootProcess.register('get_queue', q)
        ProgressRootProcess.register('get_queue', callable=lambda: queue)
        # ProgressRootProcess.register('DisplayManager',  DisplayManagerInstance.GetProcessDisplayManager())

        progressRoot = ProgressRootProcess()

        progressRoot.start()
        self.queue = progressRoot.get_queue()
        self.dictionary = progressRoot.dictionary()
        self.rootProcess = progressRoot

        # initialize shared objects

        # self.displayManager  = progressRoot.DisplayManager(DisplayManagerInstance.getself())
        self.displayManager = progressRoot.minisubdisp('dispmgr', self.queue)

        # self.displayManager = DisplayManagerInstance.ProcessDisplayManager()
        # self.downloadTracker = progressRoot.DownloadTracker()

        # self.displayManager.clear()

        # initialize worker pool
        self.workerPool = Pool(4)

    def __enter__(self):
        print('entering dlmgr')
        return self  # VERY IMPRTANT! DONT FORGET!

    def __exit__(self, type, value, traceback):
        print("leaving dlmgr")
        # result.wait()
        # print('Results', result)
        self.workerPool.close()
        self.workerPool.join()

    def dlthem2(self):
        # q = self.manager.Queue()
        itera = []
        for song in songs:
            itera.append(
                (song, self.displayManager.newsong(song))
            )
        # iter = (song, self.manager.processminidisp(self.parentminidisp.getself(), song)) for song in songs
        return self.workerPool.starmap_async(
            func=minidl2,
            iterable=itera
        )

        # while not result.ready():
        #     print('not yet')
        #     time.sleep(0.1)

        # result.wait()
        # self.workerPool.close()
        # self.workerPool.join()
        # return result


class minidisp():
    def __init__(self, name="0"):
        self.name = name
        self.console = Console()
        print('init md', self.name)

    def __enter__(self):
        print('entering md')
        return self  # VERY IMPRTANT! DONT FORGET!

    def __exit__(self, type, value, traceback):
        print("leaving md")

    def print(self, *text):
        # self.console.print(text, style="bold red")
        print(text)

    def getnewminisubdisp(self, this, name):
        return minisubdisp(this, name)

    def getself(self):
        return self

    def manageProcesses(self, result, q):
        # result = function()
        print('Proc:', result)

        while not result.ready():
            time.sleep(0.1)
            messages = []
            try:
                # data = q.get(False)
                # If `False`, the program is not blocked. `Queue.Empty` is thrown if
                # the queue is empty
                for _ in range(q.qsize()):
                    data = q.get(False)
                    messages.append(data)
            except:
                data = None

            print('refresh: not yet', self.name, messages)

        print('Results Ready')
        result.wait()


class minisubdisp():
    def __init__(self, name, q=None, parent=None):
        self.queue = q
        self.name = name
        self.parent = parent
        print('init subprocess md', name)

    def print(self, text):
        # print(text)

        self.queue.put(text, False)

    def makenewsong(self, song):
        return self.newsong(self, song)

    class newsong():
        def __init__(self, parent, name):
            # super(Whatever.Bar, self).__init__(text)
            self.parent = parent
            self.name = name

        def print(self, text):
            


# MyManager.register('processminidisp', minisubdisp)


def main():
    with minidisp("parent") as md:
        with minidlmgr(md) as dl:
            # dl = minidlmgr(md)
            # dl.dlthem2()
            md.manageProcesses(dl.dlthem2(), dl.queue)
            print('after function')


if __name__ == "__main__":
    print("Downloading...")
    # sync()
    # multi()
    # asyncrunner()
    main()
