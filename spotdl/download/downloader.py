from spotdl.download.downloadingActual import download_song, downloadTrackerManager
from spotdl.search.songObj import songObj

from typing import List

from multiprocessing import Pool


class downloadManager():
    poolSize = 4

    def __init__(self):
        trackerManager = downloadTrackerManager()
        trackerManager.start()

        self.rootProcess = trackerManager
        self.downloadTracker = trackerManager.downloadTracker()

        self.workerPool = Pool(downloadManager.poolSize)
    
    def download_single(self, song: songObj) -> None:
        self.downloadTracker.reset()

        self.downloadTracker.load_song_list([songObj])

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def download_multiple(self, songList: List[songObj]) -> None:
        self.downloadTracker.reset()
        
        self.downloadTracker.load_song_list(songList)

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def resume_download_from_tracking_file(self, trackingFilePath: str) -> None:
        self.downloadTracker.reset()
        
        self.downloadTracker.load_tracking_file(trackingFilePath)

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def close(self) -> None:
        self.downloadTracker.close()
        self.rootProcess.shutdown()

        self.workerPool.close()
        self.workerPool.join()