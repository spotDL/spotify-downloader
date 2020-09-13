#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

#! Song Search from different start points
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! The actual download stuff
from spotdl.download.downloader import DownloadManager

if __name__ == '__main__':
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