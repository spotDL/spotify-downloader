#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

from spotdl.cli.displayManager import DisplayManager
from spotdl.download.downloadManager import DownloadManager
# from spotdl.cli.argumentHandler import passArgs2 

from spotdl.cli.argumentHandler import get_options

from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! to avoid packaging errors
from multiprocessing import freeze_support


if __name__ == '__main__':

    freeze_support()

    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )
    

    with DisplayManager() as displayManagerInstance:
        with DownloadManager() as downloader:
            disp = displayManagerInstance
            displayManagerInstance.listen_to_queue(downloader.messageQueue)
            downloader.send_results_to(displayManagerInstance.process_monitor)

            # songObj = SongObj.from_url("https://open.spotify.com/track/7fcEMgPlojD0LzPHwMsoic")
            # songObj2 = SongObj.from_url("https://open.spotify.com/track/0elizmA21eSQgorzFxU80l")
            # songObj3 = SongObj.from_url("https://open.spotify.com/track/6TWjDrdEoFy4YWf2oAsy9s")
            # downloadManagerInstance.download_multiple_songs([songObj])
            # downloadManagerInstance.download_multiple_songs([songObj2, songObj3])

            options = get_options()
            disp.print("options:" + str(options))


            if options.spotify_client_id:
                disp.print('gonna use id:', options.spotify_client_id)

            if options.url:
                disp.print('gonna get song by url: ' + options.song[0])


            elif options.file:
                disp.print('File')
                downloader.resume_download_from_tracking_file(options.file)

            elif options.query:
                # disp.print('Main')
                for request in options.query:
                    if 'open.spotify.com' in request and 'track' in request:
                        disp.print('Fetching Song...')
                        songObj = SongObj.from_url(request)

                        if songObj.get_youtube_link() != None:
                            downloader.download_single_song(songObj)
                        else:
                            disp.print('Skipping %s (%s) as no match could be found on youtube' % (
                                songObj.get_song_name(), request
                            ))
                    
                    elif 'open.spotify.com' in request and 'album' in request:
                        disp.print('Fetching Album...')
                        songObjList = get_album_tracks(request)
                        downloader.download_multiple_songs(songObjList)
                    
                    elif 'open.spotify.com' in request and 'playlist' in request:
                        disp.print('Fetching Playlist...')
                        songObjList = get_playlist_tracks(request)

                        downloader.download_multiple_songs(songObjList)
                    
                    elif request.endswith('.spotdlTrackingFile'):
                        disp.print('Preparing to resume download...')
                        downloader.resume_download_from_tracking_file(request)
                    
                    else:
                        disp.print('Searching for song "%s"...' % request)
                        # try:
                        songObj = search_for_song(request)
                        downloader.download_single_song(songObj)

                        # except Exception:
                            # disp.print('No song named "%s" could be found on spotify' % request)

            else:
                disp.print('Idk what im supposed to do...')
   
                

