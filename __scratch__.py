#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize

from spotdl.cli.displayManager import DisplayManager
from spotdl.download.downloadManager import DownloadManager

from spotdl.cli.argumentHandler import get_options

from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

import logging

#! to avoid packaging errors
from multiprocessing import freeze_support


if __name__ == '__main__':

    freeze_support()

    with DisplayManager() as disp:
        with DownloadManager() as downloader:
            # disp.listen_to_queue(downloader.messageQueue)
            # downloader.set_callback_to(disp.process_monitor)


            options = get_options()
            logging.debug("Arguments:" + str(options))

            if options.debug:
                disp.print('Debug mode on', options.debug)
                disp.set_log_level(scope=options.debug)


            if options.spotify_client_id:
                if options.spotify_client_secret:
                    disp.print('Using id:', options.spotify_client_id)
                    disp.print('Using secret:', options.spotify_client_secret)
                    initialize(
                        clientId=options.spotify_client_id,
                        clientSecret=options.spotify_client_secret
                    )
                else: 
                    disp.print('Spotify Secret has to be supplied with ID')
            else:
                initialize(
                    clientId='4fe3fecfe5334023a1472516cc99d805',
                    clientSecret='0f02b7c483c04257984695007a4a8d5c'
                )

            if options.url:
                request = options.url
                disp.print('gonna get song by url: ' + request)
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
                    downloader.download_multiple_songs_sync(songObjList)
                
                elif 'open.spotify.com' in request and 'playlist' in request:
                    disp.print('Fetching Playlist...')
                    songObjList = get_playlist_tracks(request)

                    downloader.download_multiple_songs(songObjList)


            elif options.file:
                disp.print('File')
                downloader.resume_download_from_tracking_file(options.file)

            elif options.query:
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
                        try:
                            songObj = search_for_song(request)
                            disp.print('Closest Match: "%s"' % songObj.get_display_name())
                            downloader.download_single_song(songObj)

                        except Exception:
                            disp.print('No song named "%s" could be found on spotify' % request)

            else:
                disp.print('Idk what im supposed to do...')
   
                

