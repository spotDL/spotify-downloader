#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

from spotdl.cli.displayManager import DisplayManager
from spotdl.download.downloadManager import DownloadManager
from spotdl.cli.argumentHandler import passArgs2 
from spotdl.cli.argumentHandler import get_options

from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! to avoid packaging errors
from multiprocessing import freeze_support


if __name__ == '__main__':
    try:
        freeze_support()

        initialize(
            clientId='4fe3fecfe5334023a1472516cc99d805',
            clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )
        

        with DisplayManager() as displayManagerInstance:
            with DownloadManager() as downloadManagerInstance:
                songObj = SongObj.from_url("https://open.spotify.com/track/7fcEMgPlojD0LzPHwMsoic")
                songObj2 = SongObj.from_url("https://open.spotify.com/track/0elizmA21eSQgorzFxU80l")
                # downloadManagerInstance.download_multiple_songs([songObj, songObj2])
                displayManagerInstance.monitor_process(downloadManagerInstance.download_multiple_songs([songObj, songObj2]), downloadManagerInstance.messageQueue)
                    


    except Exception as inst:
        # displayManager.log("there was an unknown error of:   " + str(inst.__str__()))
        # displayManager.log(str(inst.args))
        # exit_handler()
        raise
