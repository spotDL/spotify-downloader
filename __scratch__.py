from spotdl.download.downloader import download_song
from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import initialize
import time

import multiprocessing
import asyncio
from multiprocessing import Process, Manager
from multiprocessing.managers import BaseManager
from multiprocessing import Pool
from rich.console import Console


initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
)

songs = ["https://open.spotify.com/track/7fcEMgPlojD0LzPHwMsoic", "https://open.spotify.com/track/0elizmA21eSQgorzFxU80l", "https://open.spotify.com/track/6TWjDrdEoFy4YWf2oAsy9s"]


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
        p = multiprocessing.Process(target=download_song, args=(songObj,))
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
    songObj = SongObj.from_url(song)
    download_song(songObj)
    dispmgr.print("Sucessfully downloaded and alerted")


class minidlmgr():
    def __init__(self, parentminidisp):
        print('minidlmgr init', parentminidisp.name)
        self.parentminidisp = parentminidisp
        # BaseManager.register('processminidisp', self.parentminidisp.getnewminisubdisp)
        # BaseManager.register('processminidisp', minidisp)
        BaseManager.register('processminidisp', minisubdisp)
        
        manager = BaseManager()
        manager.start()
        # self.processminidisp = manager.processminidisp(self.parentminidisp.getself(), 'df')#.getnewminisubdisp(song)
        self.manager = manager
        self.workerPool = Pool( 4 )
    def dlit(self):
        download_song(songs[0])
        self.minidisp1.print('Done downloading 1 song')

    def dlthem2(self):
        itera = []
        for song in songs:
            itera.append((song, self.manager.processminidisp(self.parentminidisp.getself(), song)))
        # iter = (song, self.manager.processminidisp(self.parentminidisp.getself(), song)) for song in songs
        self.workerPool.starmap(
            func     = minidl2,
            iterable = #(
                # (song, self.minisubdisp(song))
                # (song, self.processminidisp(self.parentminidisp.getself(), song))
                # (song, self.manager.processminidisp(self.parentminidisp.getself(), song))
                itera
                # (song, self.processminidisp)
                    # for song in songs
            # )
        )


class minidisp():
    def __init__(self, name="0"):
        self.name = name
        self.console = Console()
        print('init md', self.name)
    def __enter__(self):
        print('entering md')
        return self # VERY IMPRTANT! DONT FORGET!
    def __exit__(self, type, value, traceback):
        print("leaving md")
    def print(self, *text):
        # self.console.print(text, style="bold red")
        print(text)
    def getnewminisubdisp(self, this, name):
        return minisubdisp(this, name)
    def getself(self):
        return self

class minisubdisp():
    def __init__(self, parent, name):
        # self.parent = parent
        self.name = name
        self.parent.print('init subprocess md', name)
    def print(self, text):
        self.parent.print(text)

def main():
    with minidisp("parent") as md:
        dl = minidlmgr(md)
        dl.dlthem2()



if __name__ == "__main__":
    print("Downloading...")
    # sync()
    # multi()
    # asyncrunner()
    main()