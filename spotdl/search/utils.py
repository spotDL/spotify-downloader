from spotdl.search.spotifyClient import get_spotify_client
from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import initialize
from spotdl.common.workers import WorkerPool

from typing import List


def _get_songObj_from_url(url):
    song = SongObj.from_url(url)
    if song.get_youtube_link() != None:
        return song

def _get_songObj_from_url_and_artist(url, artistName):
    # Gather quick metadata (without searching youtube or gathering Lyrics) beforehand to validate found song is by artist
    song_preliminary = SongObj.from_url(url, preliminary=True)
    if artistName in song_preliminary.get_contributing_artists():
        song = SongObj.from_url(url, preliminary=False)
        if song.get_youtube_link() != None:
            return song

def search_for_song(query: str) ->  SongObj:
    '''
    `str` `query` : what you'd type into Spotify's search box

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

    returns a `list<songObj>` containing URLs of each track in the given album
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

    returns a `list<songObj>` containing URLs of each track in the given playlist
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


def get_artist_tracks(artistUrl: str, isPrimaryArtistOnly: bool=False) -> List[SongObj]:
    '''
    `str` `artistUrl` : Spotify URL of the artist whose tracks are to be
    retrieved

    `bool` `isPrimaryArtist` : Whether or not to search for songs that include him as contributing artist

    returns a `List` containing URLs of each track in which the specified 
    artist is the primary/contributing artist.
    '''

    spotifyClient = get_spotify_client()

    artistName      = spotifyClient.artist(artistUrl)['name']
    songURLlist = []

    if isPrimaryArtistOnly == True:
        searchQuery = q='artist:' + artistName  # Spotify API for searching for songs where artist is the primary artist
    else:
        searchQuery = q=artistName # Generic search for songs

    artistResponse = spotifyClient.search(q= searchQuery, type='track')

    # while loop acts like do-while
    while True:

        for track in artistResponse['tracks']['items']:
            songURLlist.append('https://open.spotify.com/track/' + track['id'])

        # check if more tracks are to be passed
        if artistResponse['tracks']['next']:
            artistResponse = spotifyClient.search(
                q=searchQuery, 
                type='track',
                offset = len(songURLlist)
            )
        else:
            break

    print('Found', len(songURLlist), 'tracks in search')

    q = WorkerPool(poolSize=4)

    artistTracks_raw_results = q.do(
        _get_songObj_from_url_and_artist, songURLlist, [artistName]*len(songURLlist)
    )

    q.close()

    # Remove all the 'None' values. None values occur when the artist isn't actually on the list of contributing artist or when a Youtube URL was not found
    artistTracks = [i for i in artistTracks_raw_results if i] 

    print('Spotify gave ', len(songURLlist), 'songs, then sorted that down to', len(artistTracks_raw_results), 'candidates, then found', len(artistTracks), ' to download')
    return artistTracks


def get_artist_discography(artistUrl: str) -> List[SongObj]:
    '''
    `str` `artistUrl` : Spotify Url of the artist whose tracks are to be
    retrieved

    returns a `List` containing URLs of each track of the artist including albums the artist is featured on.
    '''

    spotifyClient = get_spotify_client()
    artistAlbums = []
    artistTracks = []

    artistResponse = spotifyClient.artist_albums(artistUrl, album_type='album,single') # ‘album’,‘single’,‘appears_on’,‘compilation’,'None': all
    artistName     = spotifyClient.artist(artistUrl)['name']

    # Gather albums
    while True:

        for album in artistResponse['items']:
            albumUrl  = album['external_urls']['spotify']

            artistAlbums.append(albumUrl)

        # Check if the artist has more albums.
        if artistResponse['next']:
            artistResponse = spotifyClient.artist_albums(
                artistUrl,
                album_type='album,single',
                offset = len(artistAlbums)
            )
        else:
            break

    print('Found', len(artistAlbums), 'albums')

    # Gather tracks from those albums.
    for album in artistAlbums:

        trackResponse = spotifyClient.album_tracks(album)

        # while loop acts like do-while
        while True:

            for track in trackResponse['items']:
                artistTracks.append('https://open.spotify.com/track/' + track['id'])

            # check if more tracks are to be passed
            if trackResponse['next']:
                trackResponse = spotifyClient.album_tracks(
                    album,
                    offset = len(artistTracks)
                )
            else:
                break

    print('Found', len(artistTracks), 'songs')

    q = WorkerPool(poolSize=4)

    artistTracks_raw_results = q.do(
        _get_songObj_from_url, artistTracks
    )

    q.close()

    # Remove all 'None' values
    artistTracks = [i for i in artistTracks_raw_results if i] 

    #! Filter out the Songs in which the given artist has not contributed.
    artistTracks = [track for track in artistTracks if artistName in track.get_contributing_artists()]

    print("Downloading", len(artistTracks), "songs")

    return artistTracks