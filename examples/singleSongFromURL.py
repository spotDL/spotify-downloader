from spotdl.search.songObj import SongObj
from spotdl.download.downloader import download_song


songObj = SongObj.from_url("https://open.spotify.com/track/7fcEMgPlojD0LzPHwMsoic")
download_song(songObj=songObj)