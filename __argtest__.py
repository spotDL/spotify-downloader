
import spotdl.cli.displayManager as displayManager
# displayManager.initializer()

#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

#! Song Search from different start points
# from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
# from spotdl.search.songObj import SongObj

#! The actual download stuff

from spotdl.download.downloader import DownloadManager

#! to avoid packaging errors
from multiprocessing import freeze_support

from spotdl.cli.arguementHandler import passArgs2 
# import io
import sys
import signal
# import atexit


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    displayManager.stop()
    sys.exit(0)

def exit_handler(quit=False):
    # print('I exited i guess')
    displayManager.stop()
    if quit:
        sys.exit(0)


# atexit.register(exit_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)




if __name__ == '__main__':
    try:
        freeze_support()

        initialize(
            clientId='4fe3fecfe5334023a1472516cc99d805',
            clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )
        
        downloader = DownloadManager()

        with displayManager as DisplayManager():

            passArgs2(cliArgs[1:], downloader, displayManager) # the [1:] removes the filename from the arg list
        
        # downloader.close()

    except Exception as inst:
        displayManager.log("there was an unknown error of:   " + str(inst.__str__()))
        # displayManager.log(str(inst.args))
        exit_handler()
        raise

exit_handler()