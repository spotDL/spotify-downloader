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


#! Usage is simple - call 'python __main__.py <links, search terms, tracking files seperated by spaces>
#! Eg.
#!      python __main__.py https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ 'old gods of asgard Control' https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA
#!
#! Well, yeah its a pretty long example but, in theory, it should work like a charm. 
#!
#! A '.spotdlTrackingFile' is automatically  created with the name of the first song in the playlist/album or
#! the name of the song supplied. We don't really re re re-query YTM and SPotify as all relevant details are
#! stored to disk.
#!
#! Files are cleaned up on download failure.
#!
#! All songs are normalized to standard base volume. the soft ones are made louder, the loud ones, softer.
#!
#! The progress bar is synched across multiple-processes (4 processes as of now), getting the progress bar to
#! synch was an absolute pain, each process knows how much 'it' progressed, but the display has to be for the
#! overall progress so, yeah... that took time.
#!
#! spotdl will show you its true speed on longer download's - so make sure you try downloading a playlist.
#!
#! still yet to try and package this but, in theory, there should be no errors.
#!
#!                                                          - cheerio! (Michael)
#!
#! P.S. Tell me what you think. Up to your expectations?

if __name__ == '__main__':
    freeze_support()

    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )
    
    downloader = DownloadManager()

    for request in cliArgs[1:]:
        if 'open.spotify.com' in request and 'track' in request:
            print('Fetching Song...')
            song = SongObj.from_url(request)

            downloader.download_single_song(song)
        
        elif 'open.spotify.com' in request and 'album' in request:
            print('Fetching Album...')
            songObjList = get_album_tracks(request)

            downloader.download_multiple_songs(songObjList)
        
        elif 'open.spotify.com' in request and 'playlist' in request:
            print('Fetching Playlist...')
            songObjList = get_playlist_tracks(request)

            downloader.download_multiple_songs(request)
        
        elif request.endswith('.spotdlTrackingFile'):
            print('Preparing to resume download...')
            downloader.resume_download_from_tracking_file(request)
        
        else:
            print('Searching for song "%s"...' % request)
            try:
                song = search_for_song(request)
                downloader.download_single_song(song)

            except:            
                print('No song named "%s" could be found on spotify' % request)
    
    downloader.close()