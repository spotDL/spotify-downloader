from spotdl.search.songObj import SongObj
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.download.downloader import download_song


request = "Thunderstruck - AC/DC"
try:
    songObj = search_for_song(request)
    download_song(songObj=songObj)

except Exception:
    print('No song named "%s" could be found on spotify' % request)