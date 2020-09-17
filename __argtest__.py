#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

#! Song Search from different start points
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! The actual download stuff
from spotdl.download.downloader import DownloadManager

#! to avoid packaging errors
from multiprocessing import freeze_support

from spotdl.cli.arguementHandler import passArgs2 

if __name__ == '__main__':
    freeze_support()

    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )
    
    downloader = DownloadManager()

    passArgs2(cliArgs[1:], downloader) # the [1:] removes the filename from the arg list
    
    downloader.close()