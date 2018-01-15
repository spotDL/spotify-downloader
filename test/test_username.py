import spotdl

spotify = spotdl.spotify_tools.spotify
username = 'alex'


def test_user():
    expect_playlists = 7
    playlists = spotify.user_playlists(username)
    playlists = len(playlists['items'])
    assert playlists == expect_playlists


def test_playlist():
    expect_tracks = 14
    playlist = spotify.user_playlists(username)['items'][0]
    tracks = playlist['tracks']['total']
    assert tracks == expect_tracks


def test_tracks():
    playlist = spotify.user_playlists(username)['items'][0]
    expect_lines = playlist['tracks']['total']
    result = spotify.user_playlist(
        playlist['owner']['id'], playlist['id'], fields='tracks,next')
    tracks = result['tracks']

    with open('list.txt', 'w') as fout:
        while True:
            for item in tracks['items']:
                track = item['track']
                try:
                    fout.write(track['external_urls']['spotify'] + '\n')
                except KeyError:
                    pass
            # 1 page = 50 results
            # check if there are more pages
            if tracks['next']:
                tracks = spotify.next(tracks)
            else:
                break

    with open('list.txt', 'r') as listed:
        expect_song = (listed.read()).splitlines()[0]

    spotdl.internals.trim_song('list.txt')
    with open('list.txt', 'a') as myfile:
        myfile.write(expect_song)

    with open('list.txt', 'r') as listed:
        songs = (listed.read()).splitlines()

    lines = len(songs)
    song = songs[-1]
    assert (expect_lines == lines and expect_song == song)
