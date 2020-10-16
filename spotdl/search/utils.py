from spotdl.search.spotifyClient import get_spotify_client
from spotdl.search.songObj import SongObj

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