#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

from spotdl.cli.displayManager import DisplayManager
from spotdl.cli.downloadManager import DownloadManager
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
            # print(displayManagerInstance)
            # print('printing')
            displayManagerInstance.print('asdf')
            print = displayManagerInstance.print
            downloader = DownloadManager(displayManagerInstance)

            # passArgs2(cliArgs[1:], downloader) # the [1:] removes the filename from the arg list

            options = get_options(cliArgs) # the [1:] removes the filename from the arg list
            print("options:" + str(options))


            if options.spotify_client_id:
                print('gonna use id:', options.spotify_client_id)

            if options.song:
                print('gonna get song by url: ' + options.song[0])
                request = options.song[0]
                if 'open.spotify.com' in request and 'track' in request:
                    print('Fetching Song...')
                    song = SongObj.from_url(request)
                    downloader.download_single_song(song)
                
                elif request.endswith('.spotdlTrackingFile'):
                    print('Preparing to resume download...')
                    downloader.resume_download_from_tracking_file(request)
                
                else:
                    print('Searching for song "%s"...' % request)
                    try:
                        song = search_for_song(request)
                    except:            
                        print('No song named "%s" could be found on spotify' % request)
                    downloader.download_single_song(song)

            elif options.album:
                print('gonna get album' + options.album[0])

            elif options.query:
                print('Main')

            else:
                print('Idk what im supposed to do...')
                    
        downloader.close()

    except Exception as inst:
        # displayManager.log("there was an unknown error of:   " + str(inst.__str__()))
        # displayManager.log(str(inst.args))
        # exit_handler()
        raise
