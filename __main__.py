#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

#! Song Search from different start points
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! The actual download stuff
from spotdl.download.downloader import DownloadManager

#! to avoid packaging errors
from multiprocess import freeze_support

#! used to quiet the output
from io import StringIO as quiet
import sys

import dill

initialize(
    clientId     = '4fe3fecfe5334023a1472516cc99d805',
    clientSecret = '0f02b7c483c04257984695007a4a8d5c'
    )


#! Script Help
help_notice = '''
To download a song run,
    spotdl $trackUrl
    eg. spotdl https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA

To download a album run,
    spotdl $albumUrl
    eg. spotdl https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ

To download a playlist run,
    spotdl $playlistUrl
    eg. spotdl https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ

To search for and download a song (not very accurate) run,
    spotdl $songQuery
    eg. spotdl 'The HU - Sugaan Essenna'

To resume a failed/incomplete download run,
    spotdl $pathToTrackingFile
    eg. spotdl 'Sugaan Essenna.spotdlTrackingFile'

    Note, '.spotDlTrackingFiles' are automatically created during download start, they are deleted on
    download completion

You can chain up download tasks by seperating them with spaces:
    spotdl $songQuery1 $albumUrl $songQuery2 ... (order does not matter)
    eg. spotdl 'The Hu - Sugaan Essenna' https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ ...

Spotdl downloads up to 4 songs in parallel - try to download albums and playlists instead of
tracks for more speed
'''

def console_entry_point():
    '''
    This is where all the console processing magic happens.
    Its super simple, rudimentary even but, it's dead simple & it works.
    '''

    if '--help' in cliArgs or '-h' in cliArgs:
        print(help_notice)

        #! We use 'return None' as a convenient exit/break from the function
        return None

    if '--quiet' in cliArgs:
        #! removing --quiet so it doesnt mess up with the download
        cliArgs.remove('--quiet')
        #! make stdout & stderr silent
        sys.stdout = quiet()
        sys.stderr = quiet()

    initialize(
        clientId     = '4fe3fecfe5334023a1472516cc99d805',
        clientSecret = '0f02b7c483c04257984695007a4a8d5c'
        )

    downloader = DownloadManager()

    for request in cliArgs[1:]:
        if ('open.spotify.com' in request and 'track' in request) or 'spotify:track:' in request:
            print('Fetching Song...')
            song = SongObj.from_url(request)

            if song.get_youtube_link() != None:
                downloader.download_single_song(song)
            else:
                print('Skipping %s (%s) as no match could be found on youtube' % (
                    song.get_song_name(), request
                ))
        
        elif ('open.spotify.com' in request and 'album' in request) or 'spotify:album:' in request:
            print('Fetching Album...')
            songObjList = get_album_tracks(request)

            downloader.download_multiple_songs(songObjList)
        
        elif ('open.spotify.com' in request and 'playlist' in request) or 'spotify:playlist:' in request:
            print('Fetching Playlist...')
            songObjList = get_playlist_tracks(request)

            downloader.download_multiple_songs(songObjList)

        elif request.endswith('.txt'):
            print('Fetching songs from %s...' % request)
            songObjList = []

            with open(request, 'r') as songFile:
                for songLink in songFile.readlines():
                    song = SongObj.from_url(songLink)
                    songObjList.append(song)

            downloader.download_multiple_songs(songObjList)

        elif request.endswith('.spotdlTrackingFile'):
            print('Preparing to resume download...')
            downloader.resume_download_from_tracking_file(request)

        else:
            print('Searching for song "%s"...' % request)
            try:
                song = search_for_song(request)
                downloader.download_single_song(song)

            except Exception:
                print('No song named "%s" could be found on spotify' % request)

    downloader.close()

if __name__ == '__main__':
    freeze_support()
    
    from spotdl.search.spotifyClient import initialize


    from spotdl.common.workers import WorkerPool
    from datetime import datetime

    print('starting')
    #! biggerpool size faster it is (provided you have that many processors)
    #! Note to maintainance testers
    #!initialize(
    #!    clientId     = '4fe3fecfe5334023a1472516cc99d805',
    #!    clientSecret = '0f02b7c483c04257984695007a4a8d5c'
    #!)

    st0 = datetime.now()
    q = WorkerPool(poolSize=4)
    dlm = DownloadManager(q)
    start = datetime.now()

    print(start - st0)

    print('lookup')
#    w = q.do(
#        get_album_tracks,
#        [
#            'https://open.spotify.com/album/6mUdeDZCsExyJLMdAfDuwh?si=fUnrDYEBTPilDgnS_v46sQ',
#            'https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=BQEKilFAQMCYqyatB-1Cag',
#            #'https://open.spotify.com/album/6thZ5crAR7sABcxy4FOzxh?si=29ssaWHGRP6AHx85mLvyvw',
#            #'https://open.spotify.com/album/3B0PgLmgaW0gJth55ApWbw?si=JAaCetp5Qt60CYZPNvnigA',
#            #'https://open.spotify.com/album/5iDRB3mIvV9ceXZIkXA4KT?si=ozJ0xEZeRW6Rqamdt3bfGA',
#            #'https://open.spotify.com/album/0v1VLjgwVun46wA13DWUJI?si=Xn0O7SAgS_iqzeL5esccCw',
#            #'https://open.spotify.com/album/5ikgQawMuw7aC6VPEfJJ7C?si=tfrgm7haTX62nPnjv9dMXQ',
#            #'https://open.spotify.com/album/4xFmHg5dYvaqmn9ZNQpjWL?si=dnZb1mCmSraSV1HOiELHnw',
#            #'https://open.spotify.com/album/4xFmHg5dYvaqmn9ZNQpjWL?si=Cjz4G0gNSwSffQJtbIhH2Q',
#            #'https://open.spotify.com/album/0o2Y0VeJEZ72wA6ug0yN8X?si=X89joxHTRtiarvFG3m-Iyw',
#            #'https://open.spotify.com/album/6BJ3qH85n2juWivLlEybAw?si=1UxQGqhZTy-xxp1ulyCArw',
#            #'https://open.spotify.com/album/40J4xZREcFpeJVnXDXntvk?si=SbNjxO-_TTa_IEo7ogCGKw'
#        ]
#    )
#
#    masterList = []
#
#    for each in w:
#        masterList += each

    end1 = datetime.now()

    print(end1 - start)


    #! Number of processes  | Time taken to get songObj's   | Avg speed
    #! 01                     05.20.667661                    192kbps
    #! 04                     01.47.572535                    380Kbps
    #! 08                     01.24.923228                    800kbps (no major gains here prolly due to my internet speed)

    print('download')
    from spotdl.download.downloader import download_song
    download_song(SongObj.from_url('https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA'))
    dlm.resume_download_from_tracking_file('.\Hells Bells.spotdlTrackingFile')

    end2 = datetime.now()
    print(end2-end1)

    console_entry_point()
