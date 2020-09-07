from spotdl.search.provider import search_and_get_best_match
from spotdl.search.spotifyClient import get_spotify_client
from json import dumps as convert_dict_to_json, loads as convert_json_to_dict

from typing import List

class songObj():
    #! This can be accessed as songObj.searchProvider. songObj acts like a namespace
    #! it allows us a convenient way of setting a search provider without using globals
    searchProvider = search_and_get_best_match

    #====================
    #=== Constructors ===
    #====================

    #! constructors here are a bit mucky, there are two different constructors for two
    #! different use cases, hence the actual __init__ function does not exist
    
    #! Note, since the following are class methods, an instance of songObj is initialized
    #! and passed to them
    @classmethod
    def from_url(thisClass, spotifyURL: str):
        # check if URL is a playlist, user, artist or album, if yes raise an Exception,
        # else procede
        if 'track' not in spotifyURL:
            raise Exception('passed URL is not that of a track: %s' % spotifyURL)



        # query spotify for song, artist, album details
        spotifyClient = get_spotify_client()

        thisClass.__rawTrackMeta = spotifyClient.track(spotifyURL)

        primaryArtistId = thisClass.__rawTrackMeta['artists'][0]['id']
        thisClass.__rawArtistMeta = spotifyClient.artist(primaryArtistId)

        albumId = thisClass.__rawTrackMeta['album']['id']
        thisClass.__rawAlbumMeta = spotifyClient.album(albumId)



        # get best match from the given provider
        songName = thisClass.__rawTrackMeta['name']

        albumName = thisClass.__rawTrackMeta['album']['name']

        duration = round(
            thisClass.__rawTrackMeta['duration_ms'] / 1000,
            ndigits = 3
        )

        contributingArtists = []

        for artist in thisClass.__rawTrackMeta['artists']:
            contributingArtists.append(artist['name'])

        youtubeLink = songObj.searchProvider(
            songName,
            contributingArtists,
            albumName,
            duration
        )

        thisClass.__youtubeLink = youtubeLink

        return thisClass()
    
    @classmethod
    def from_disk(thisClass, path: str):        
        with open(path, 'r') as songObjFile:
            dataDump    = convert_json_to_dict(songObjFile.read())
        
        thisClass.__rawTrackMeta  = dataDump['rawTrackMeta']
        thisClass.__rawAlbumMeta  = dataDump['rawAlbumMeta']
        thisClass.__rawArtistMeta = dataDump['rawAlbumMeta']
        thisClass.__youtubeLink   = dataDump['youtubeLink']
        thisClass.isInitialized = True

        return thisClass()

    #================================
    #=== Interface Implementation ===
    #================================

    def get_youtube_link(self) -> str:
        return self.__youtubeLink

    #! Song Details:
    
    #! 1. Name
    def get_song_name(self) -> str:
        ''''
        returns songs's name.
        '''
        
        return self.__rawTrackMeta['name']
    
    #! 2. Track Number
    def get_track_number(self) -> int:
        '''
        returns song's track number from album (as in weather its the first
        or second or third or fifth track in the album)
        '''

        return self.__rawTrackMeta['track_number']
    
    #! 3. Genres
    def get_genres(self) -> List[str]:
        '''
        returns a list of possible genres for the given song, the first member
        of the list is the most likely genre. returns None if genre data could
        not be found.
        '''

        if len(self.__rawAlbumMeta['genres']) > 0:
            return self.__rawAlbumMeta['genres']

        elif len(self.__rawArtistMeta['genres']) > 0:
            return self.__rawArtistMeta['genres']

        else:
            return None
    
    #! 4. Duration
    def get_duration(self) -> float:
        '''
        returns duration of song in seconds.
        '''

        return round(self.__rawTrackMeta['duration_ms'] / 1000, ndigits = 3)
    
    #! 5. All involved artists
    def get_contributing_artists(self) -> List[str]:
        '''
        returns a list of all artists who worked on the song.
        The first member of the list is likely the main artist.
        '''

        # we get rid of artist name that are in the song title so
        # naming the song would be as easy as 
        # $contributingArtists + songName.mp3, we would want to end up with
        # 'Jetta, Mastubs - I'd love to change the world (Mastubs remix).mp3'
        # as a song name, it's dumb.

        contributingArtists = []

        for artist in self.__rawTrackMeta['artists']:
            contributingArtists.append(artist['name'])
        
        return contributingArtists

    #! Album Details:
    
    #! 1. Name
    def get_album_name(self) -> str:
        '''
        returns name of the album that the song belongs to.
        '''

        return self.__rawTrackMeta['album']['name']
    
    #! 2. All involved artist
    def get_album_artists(self) -> List[str]:
        '''
        returns list of all artists who worked on the album that
        the song belongs to. The first member of the list is likely the main
        artist.
        '''

        albumArtists = []

        for artist in self.__rawTrackMeta['album']['artists']:
            albumArtists.append(artist['name'])
        
        return albumArtists
    
    #! 3. Release Year/Date
    def get_album_release(self) -> str:
        '''
        returns date/year of album release depending on what data is available.
        '''

        return self.__rawTrackMeta['album']['release_date']
    
    #! Utilities for genuine use and also for metadata freaks:
    
    #! 1. Album Art URL
    def get_album_cover_url(self) -> str:
        '''
        returns url of the biggest album art image available.
        '''

        return self.__rawTrackMeta['album']['images'][0]['url']
    
    #! 2. All the details the spotify-api can provide
    def get_data_dump(self) -> dict:
        '''
        returns a dictionary containing the spotify-api responses as-is. The
        dictionary keys are as follows:
            - rawTrackMeta      spotify-api track details
            - rawAlbumMeta      spotify-api song's album details
            - rawArtistMeta     spotify-api song's artist details
        
        Avoid using this function, it is implemented here only for those super
        rare occasions where there is a need to look up other details. Why
        have to look it up seperately when it's already been looked up once?
        '''

        #! internally the only reason this exists is that it helps in saving to disk

        return {
            'youtubeLink'  : self.__youtubeLink,
            'rawTrackMeta' : self.__rawTrackMeta,
            'rawAlbumMeta' : self.__rawAlbumMeta,
            'rawArtistMeta': self.__rawArtistMeta
        }
    
    def save(self):
        with open(self.get_song_name() + '.songObjData', 'wb') as file:
            file.write(
                convert_dict_to_json(
                    self.get_data_dump(),
                    sort_keys = True,
                    indent    = 4
                ).encode()
            )