'''
A few helper utilities for spotify access
'''

#===============
#=== Imports ===
#===============
from spotdl.utils.authorization import getSpotifyClient
from spotdl.utils.loggingBase import getSubLoggerFor



#====================
#=== Initializing ===
#====================
logger = getSubLoggerFor('utility')

logger.info('Requesting authorized spotify client >')

# We assume that authorizedSpotify has already been set up with a clientID and
# clientSecret somewhere else
spotify = getSpotifyClient()

logger.info('Obtained authorized spotify client')



#=================
#=== Functions ===
#=================
def getsearchForSong(songName, artist = None):
    '''
    str : songName      > name of the song
    str : artist        > name of the primary artist

    Queries Spotify for a song and returns the best match. 
    '''

    # None evaluates to False, non-None values to True
    if artist:
        results = spotify.search(artist + ' - ' + songName)
    else:
        results = spotify.search(songName)
    
    # Supposed best match
    rawTrackMeta = results['tracks']['items'][0]
    
    return 'http://open.spotify.com/track/' + rawTrackMeta['id']



#===============
#=== Classes ===
#===============
class trackDetails(object):
    '''
    str: url        > URL of a spotify track, usually from open.spotify.com

    trackDetails is an abstraction layer over the standart spotify-api
    response.
    '''
    
    # This class is used during both the search phase and also the
    # metadata['duration_ms] phase. Interesting, don't you think? On a second
    # note, if your interested in the structure of the spotify-api response,
    # look up the REFS folder under TEMP on the github repo

    def get__init__(self, url):
        global spotify

        # Spotify api response, (JSON)
        self.__rawTrackMeta = spotify.track(url)

        # Barely use these two - they're here just to provide genre info and
        # use by enterprising young coders. Look to the dataDump method below
        self.__rawArtistMeta = spotify.artist(
            self.__rawTrackMeta['artists'][0]['id']
            )

        self.__rawAlbumMeta = spotify.album(
            self.__rawTrackMeta['album']['id']
            )
        
        # log successful detail retrieval
        logMessage = 'Obtained metadata for %-10s (%s)' % (
            self.__rawTrackMeta['name'],
            url
        )

        logger.info(logMessage)

    # Song Details:
    # 1. Name
    def getSongName(self):
        ''''
        returns songs's name.
        '''
        
        return self.__rawTrackMeta['name']
    
    # 2. Track Number
    def getTrackNumber(self):
        '''
        returns song's track number from album (as in weather its the first
        or second or third or fifth track in the album)
        '''

        return self.__rawTrackMeta['track_number']
    
    # 3. Genres
    def getGenres(self):
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
    
    # 4. Duration
    def getLength(self):
        '''
        returns duration of song in seconds.
        '''

        return self.__rawTrackMeta['duration_ms'] / 1000.0
    
    # 5. All involved artists
    def getContributingArtists(self):
        '''
        returns a list of all artists who worked on the song.
        The first member of the list is likely the main artist.
        '''

        contributingArtists = []

        for artist in self.__rawTrackMeta['artists']:
            contributingArtists.append(artist['name'])
        
        return contributingArtists
    
    # Album Details:
    # 1. Name
    def getAlbumName(self):
        '''
        returns name of the album that the song belongs to.
        '''

        return self.__rawTrackMeta['album']['name']
    
    # 2. All involved artist
    def getAlbumArtists(self):
        '''
        returns list of all artists who worked on the album that
        the song belongs to. The first member of the list is likely the main
        artist.
        '''

        albumArtists = []

        for artist in self.__rawTrackMeta['album']['artists']:
            albumArtists.append(artist['name'])
        
        return albumArtists
    
    # 3. Release Year/Date
    def getAlbumRelease(self):
        '''
        returns date/year of album release depending on what data is available.
        '''

        return self.__rawTrackMeta['album']['release_date']
    
    # Utilities for genuine coders and also for metadata freaks:
    # 1. Album Art URL
    def getAlbumArtUrl(self):
        '''
        returns url of the biggest album art image available.
        '''

        return self.__rawTrackMeta['album']['images'][0]['url']
    
    # 2. All the details the spotify-api can provide
    def getDataDump(self):
        '''
        returns a dictionary containing the spotify-api responses as-is. The
        dictionary keys are as follows:
            - rawTrackMeta      > spotify-api track details
            - rawAlbumMeta      > spotify-api song's album details
            - rawArtistMeta     > spotify-api song's artist details
        
        Avoid using this function, it is implemented here only for those super
        rare occasions where there is a need to look up other details. Why
        have to look it up seperately when it's already been looked up once?
        '''

        return {
            'rawTrackMeta': self.__rawTrackMeta,
            'rawAlbumMeta': self.__rawAlbumMeta,
            'rawArtistMeta': self.__rawArtistMeta
        }