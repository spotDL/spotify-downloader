from spotdl.search.utils import get_playlist_tracks
#from spotdl.download.dlBase import downloadManager, downloadTracker, download_song
from spotdl.search.spotifyClient import initialize
from spotdl.download.downloader import downloadManager

from spotdl.search.songObj import songObj

if __name__ == '__main__':
    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )


    #playlistSongObjects = get_playlist_tracks('https://open.spotify.com/playlist/37i9dQZF1EpGlVPORupxY0?si=qD6l3hEQQ6uHgpG9etwtOg')
    q = downloadManager()
    q.resume_download_from_tracking_file('weekend.spotdlTrackingFile')