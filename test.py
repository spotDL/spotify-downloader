from spotdl.search.spotifyClient import initialize
initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )

from spotdl.search.utils import get_album_tracks
from spotdl.download.downloader import download_song

q = get_album_tracks('https://open.spotify.com/album/0v1VLjgwVun46wA13DWUJI?si=nkRyfk2_Rn2Ddph0Zo9T8A')

for each in q[:4]:
    download_song(each)