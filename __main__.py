from spotdl.search.spotifyClient import initialize

from spotdl.search.utils import get_playlist_tracks
from spotdl.download.downloader import DownloadManager
from spotdl.search.songObj import songObj

if __name__ == '__main__':
    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )


    #playlistSongObjects = get_playlist_tracks('https://open.spotify.com/playlist/37i9dQZF1EpGlVPORupxY0?si=qD6l3hEQQ6uHgpG9etwtOg')
    
    man = DownloadManager()
    song = songObj.from_url('https://open.spotify.com/track/6r0H7a2OoqXpU1v5ekRKji?si=pxdnB3-xSmuiJdOvDIOoTw')
    man.download_single_song(song)
    #man.download_multiple_songs(playlistSongObjects)
    print('Fetching Playlist Tracks...')
    man.resume_download_from_tracking_file("D:\\Projects\\GitHub\\spotify-downloader\\Losing Hold (feat. Austin Jenckes).spotdlTrackingFile")
