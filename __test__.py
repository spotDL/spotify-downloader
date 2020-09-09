from spotdl.search.songObj import songObj
from spotdl.search.spotifyClient import initialize

initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )

q = songObj.from_url('https://open.spotify.com/track/0uYPsl955ngOyNBzfp0EYg')
q.save()

for each in [
    q.get_song_name(),
    q.get_contributing_artists()
]:
    print(each)

w = songObj.from_disk(input())
w.get_song_name()
