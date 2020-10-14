'''
Example of Utilizing DownloadManager for multiprocessing downloads
'''

from spotdl.search.songObj import SongObj
from spotdl.download.downloadManager import DownloadManager



with DownloadManager() as downloadManagerInstance:
    songObj2 = SongObj.from_url("https://open.spotify.com/track/0elizmA21eSQgorzFxU80l")
    songObj3 = SongObj.from_url("https://open.spotify.com/track/6TWjDrdEoFy4YWf2oAsy9s")
    downloadManagerInstance.download_multiple_songs([songObj2, songObj3])