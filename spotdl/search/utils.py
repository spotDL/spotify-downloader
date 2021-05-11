from typing import List, Dict

from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import SpotifyClient


def search_for_song(query: str) -> SongObj:
    '''
    `str` `query` : what you'd type into spotify's search box

    Queries Spotify for a song and returns the best match
    '''

    # get a spotify client
    spotifyClient = SpotifyClient()

    # get possible matches from spotify
    result = spotifyClient.search(query, type='track')

    # return first result link or if no matches are found, raise and Exception
    if len(result['tracks']['items']) == 0:
        raise Exception('No song matches found on Spotify')
    else:
        for songResult in result['tracks']['items']:
            songUrl = 'http://open.spotify.com/track/' + songResult['id']
            song = SongObj.from_url(songUrl)

            if song.get_youtube_link() is not None:
                return song

        raise Exception('Could not match any of the results on YouTube')


def get_album_tracks(albumUrl: str) -> List[SongObj]:
    '''
    `str` `albumUrl` : Spotify Url of the album whose tracks are to be
    retrieved

    returns a `list<songObj>` containing Url's of each track in the given album
    '''

    spotifyClient = SpotifyClient()
    albumTracks = []

    trackResponse = spotifyClient.album_tracks(albumUrl)

    # while loop acts like do-while
    while True:

        for track in trackResponse['items']:
            song = SongObj.from_url('https://open.spotify.com/track/' + track['id'])

            if song.get_youtube_link() is not None:
                albumTracks.append(song)

        # check if more tracks are to be passed
        if trackResponse['next']:
            trackResponse = spotifyClient.album_tracks(
                albumUrl,
                offset=len(albumTracks)
            )
        else:
            break

    return albumTracks


def get_artist_tracks(artistUrl: str) -> List[SongObj]:
    '''
    `str` `albumUrl` : Spotify Url of the artist whose tracks are to be
    retrieved

    returns a `list<songObj>` containing Url's of each track in the artist profile
    '''

    spotifyClient = SpotifyClient()
    artistTracks = []
    albums = []
    offset = 0

    artistResponse = spotifyClient.artist_albums(artistUrl)

    # loop until we get all tracks from all albums/playlists
    while True:
        for album in artistResponse['items']:

            # return an iterable containing the string's alphanumeric characters
            alphaNumericFilter = filter(str.isalnum, album['name'].lower())

            # join all characters into one string
            albumName = "".join(alphaNumericFilter)

            # check if we've already downloaded album with this name
            if not (albumName in albums) and not (
                # exclude compilation playlists
                album['album_group'] == 'appears_on' and album['album_type'] in [
                    'album', 'compilation']
            ):
                trackResponse = spotifyClient.album_tracks(album['uri'])
                albumTracks: Dict[str, SongObj] = {}

                # loop until we get all tracks from playlist
                while True:
                    for track in trackResponse['items']:
                        # return an iterable containing the string's alphanumeric characters
                        alphaNumericFilter = filter(str.isalnum, track['name'].lower())

                        # join all characters into one string
                        trackName = "".join(alphaNumericFilter)

                        # check if we've alredy downloaded this track
                        if albumTracks.get(trackName) is None:
                            for artist in track['artists']:
                                # get artist id from url
                                # https://api.spotify.com/v1/artists/1fZAAHNWdSM5gqbi9o5iEA/albums
                                # split string
                                # ['https:', '', 'api.spotify.com', 'v1', 'artists', '1fZAAHNWdSM5gqbi9o5iEA', 'albums']
                                # get second element from the end
                                # '1fZAAHNWdSM5gqbi9o5iEA'
                                artistId = artistResponse['href'].split('/')[-2]

                                # ignore tracks that are not from our artist by checking
                                # the id
                                if artist['id'] == artistId:
                                    song = SongObj.from_url(
                                        'https://open.spotify.com/track/' + track['id']
                                    )

                                    if song.get_youtube_link() is not None:
                                        albumTracks[trackName] = song

                    # check if more tracks are to be passed
                    if trackResponse['next']:
                        trackResponse = spotifyClient.album_tracks(
                            album['uri'],
                            offset=len(albumTracks)
                        )
                    else:
                        break

                artistTracks.extend(list(albumTracks.values()))
                albums.append(albumName)

        offset += len(artistResponse['items'])

        # check if more albums are to be passed
        if artistResponse['next']:
            artistResponse = spotifyClient.artist_albums(
                artistUrl,
                offset=offset
            )
        else:
            break

    return artistTracks


def get_playlist_tracks(playlistUrl: str) -> List[SongObj]:
    '''
    `str` `playlistUrl` : Spotify Url of the album whose tracks are to be
    retrieved

    returns a `list<songObj>` containing Url's of each track in the given playlist
    '''

    spotifyClient = SpotifyClient()
    playlistTracks = []

    playlistResponse = spotifyClient.playlist_tracks(playlistUrl)

    # while loop to mimic do-while
    while True:

        for songEntry in playlistResponse['items']:
            if songEntry['track'] is None or songEntry['track']['id'] is None:
                continue

            song = SongObj.from_url(
                'https://open.spotify.com/track/' + songEntry['track']['id'])

            if song.get_youtube_link() is not None:
                playlistTracks.append(song)

        # check if more tracks are to be passed
        if playlistResponse['next']:
            playlistResponse = spotifyClient.playlist_tracks(
                playlistUrl,
                offset=playlistResponse['offset'] + playlistResponse['limit']
            )
        else:
            break

    return playlistTracks
