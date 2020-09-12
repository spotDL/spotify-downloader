from spotdl.search.spotifyClient import initialize

#from spotdl.search.utils import get_playlist_tracks

from spotdl.download.downloader import DownloadManager
from spotdl.search.songObj import SongObj

if __name__ == '__main__':
    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )

    
    man = DownloadManager()
    #song = SongObj.from_url('https://open.spotify.com/track/6r0H7a2OoqXpU1v5ekRKji?si=pxdnB3-xSmuiJdOvDIOoTw')
    #man.download_single_song(song)
    
    print('Resuming Playlist Tracks...')
    man.resume_download_from_tracking_file("Cicatrices.spotdlTrackingFile")
    man.resume_download_from_tracking_file("Losing Hold (feat. Austin Jenckes).spotdlTrackingFile")
