from spotdl.search import spotifyClient

spotifyClient.initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )

from spotdl.search.utils import get_playlist_tracks
from spotdl.download.downloader import DownloadManager
from spotdl.download.playlist import M3U8

playlist_URI = 'https://open.spotify.com/playlist/37i9dQZF1EpiXbCbU404ST?si=gDiY-y6YTX-RBQ2c1vhvDQ'

q = get_playlist_tracks(playlist_URI)
m3u8 = M3U8()

w = DownloadManager()
w.download_multiple_songs(q, m3u8)

t = m3u8.build_m3u8()
print(t)

open(r'.\Temp\OnRepeat.m3u8', 'w').write(t)