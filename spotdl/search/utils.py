from spotdl.search.spotifyClient import get_spotify_client
from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import initialize
from spotdl.common.workers import WorkerPool

from typing import List

def search_for_song(query: str) ->  SongObj:
    '''
    `str` `query` : what you'd type into spotify's search box

    Queries Spotify for a song and returns the best match
    '''

    # get a spotify client
    spotifyClient = get_spotify_client()

    # get possible matches from spotify
    result = spotifyClient.search(query, type = 'track')

    # return first result link or if no matches are found, raise and Exception
    if len(result['tracks']['items']) == 0:
        raise Exception('No song matches found on Spotify')
    else:
        for songResult in result['tracks']['items']:
            songUrl = 'http://open.spotify.com/track/' + songResult['id']
            song = SongObj.from_url(songUrl)

            if song.get_youtube_link() != None:
                return song

        raise Exception('Could not match any of the results on YouTube')

def get_album_tracks(albumUrl: str) -> List[SongObj]:
    '''
    `str` `albumUrl` : Spotify Url of the album whose tracks are to be
    retrieved

    returns a `list<songObj>` containing Url's of each track in the given album
    '''

    spotifyClient = get_spotify_client()
    albumTracks = []

    trackResponse = spotifyClient.album_tracks(albumUrl)

    # while loop acts like do-while
    while True:

        for track in trackResponse['items']:
            song = SongObj.from_url('https://open.spotify.com/track/' + track['id'])

            if song.get_youtube_link() != None:
                albumTracks.append(song)

        # check if more tracks are to be passed
        if trackResponse['next']:
            trackResponse = spotifyClient.album_tracks(
                albumUrl,
                offset = len(albumTracks)
            )
        else:
            break

    return albumTracks

def get_playlist_tracks(playlistUrl: str) -> List[SongObj]:
    '''
    `str` `playlistUrl` : Spotify Url of the album whose tracks are to be
    retrieved

    returns a `list<songObj>` containing Url's of each track in the given playlist
    '''

    spotifyClient = get_spotify_client()
    playlistTracks = []

    playlistResponse = spotifyClient.playlist_tracks(playlistUrl)

    # while loop to mimic do-while
    while True:

        for songEntry in playlistResponse['items']:
            song = SongObj.from_url(
                'https://open.spotify.com/track/' + songEntry['track']['id'])

            if song.get_youtube_link() != None:
                playlistTracks.append(song)

        # check if more tracks are to be passed
        if playlistResponse['next']:
            playlistResponse = spotifyClient.playlist_tracks(
                playlistUrl,
                offset = len(playlistTracks)
            )
        else:
            break

    return playlistTracks


def get_artist_discography_tracks(artistUrl: str) -> List[SongObj]:
    '''
    `str` `artistUrl` : Spotify Url of the artist whose tracks are to be
    retrieved

    returns a `List` containing Url's of each track of the artist.
    '''

    spotifyClient = get_spotify_client()
    artistAlbums = []
    artistTracks = []

    artistResponse = spotifyClient.artist_albums(artistUrl)
    artistName     = spotifyClient.artist(artistUrl)['name']

    while True:

        for album in artistResponse['items']:
            albumUrl  = album['external_urls']['spotify']

            artistAlbums.append(albumUrl)

        # Check if the artist has more albums.
        if artistResponse['next']:
            artistResponse = spotifyClient.artist_albums(
                artistUrl,
                offset = len(artistAlbums)
            )
        else:
            break

    for album in artistAlbums:
        albumTracks = get_album_tracks(album)

        artistTracks += albumTracks

    #! Filter out the Songs in which the given artist has not contributed.
    artistTracks = [track for track in artistTracks if artistName in track.get_contributing_artists()]

    return artistTracks


def get_artist_tracks_new(artistUrl: str) -> List[SongObj]:
    '''
    `str` `artistUrl` : Spotify Url of the artist whose tracks are to be
    retrieved

    returns a `List` containing Url's of each track of the artist.
    '''

    spotifyClient = get_spotify_client()

    # artistResponse = spotifyClient.artist_albums(artistUrl)
    artistName      = spotifyClient.artist(artistUrl)['name']
    artistTracks     = []

    artistResponse = spotifyClient.search(q='artist:' + artistName, type='track')

    print(artistResponse)

    # while loop acts like do-while
    while True:

        for track in artistResponse['tracks']['items']:
            song = SongObj.from_url('https://open.spotify.com/track/' + track['id'])
            print(song)

            if (song.get_youtube_link() != None) and (artistName in song.get_contributing_artists()):
                artistTracks.append(song)
                print(song, song.get_song_name())

        # check if more tracks are to be passed
        if artistResponse['tracks']['next']:
            artistResponse = spotifyClient.search(
                q='artist:' + artistName, 
                type='track',
                offset = len(artistTracks)
            )
        else:
            break

    #! Filter out the Songs in which the given artist has not contributed.
    # artistTracks = [track for track in artistTracks if artistName in track.get_contributing_artists()]

    # print(artistTracks)

    # return artistTracks

def _get_songObj_from_url_and_artist(url, artistName):
    initialize(
        clientId     = '4fe3fecfe5334023a1472516cc99d805',
        clientSecret = '0f02b7c483c04257984695007a4a8d5c'
        )
    song_preliminary = SongObj.from_url(url, preliminary=True)
    if artistName in song_preliminary.get_contributing_artists():
        song = SongObj.from_url(url, preliminary=False)
        if song.get_youtube_link() != None:
            return song

def get_artist_tracks(artistUrl: str) -> List[SongObj]:
    '''
    `str` `artistUrl` : Spotify Url of the artist whose tracks are to be
    retrieved

    returns a `List` containing Url's of each track of the artist.
    '''

    spotifyClient = get_spotify_client()

    artistName      = spotifyClient.artist(artistUrl)['name']
    songURLlist = []

    artistResponse = spotifyClient.search(q='artist:' + artistName, type='track') # remove 'artist:' to included contributed tracks

    # while loop acts like do-while
    while True:

        for track in artistResponse['tracks']['items']:
            songURLlist.append('https://open.spotify.com/track/' + track['id'])

        # check if more tracks are to be passed
        if artistResponse['tracks']['next']:
            artistResponse = spotifyClient.search(
                q='artist:' + artistName, 
                type='track',
                offset = len(songURLlist)
            )
        else:
            break

    q = WorkerPool(poolSize=4)

    artistTracks_raw_results = q.do(
        _get_songObj_from_url_and_artist, songURLlist, [artistName]*len(songURLlist)
    )

    q.close()

    # Remove all the 'None' values. None values occur when the artist isn't actually on the list of contributing artist or when a Youtube URL was not found
    artistTracks = [i for i in artistTracks_raw_results if i] 

    print('Spotify gave ', len(songURLlist), 'songs, then sorted that down to', len(artistTracks_raw_results), 'candidates, then found', len(artistTracks), ' to download')
    return artistTracks
