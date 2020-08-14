#===============
#=== Imports ===
#===============
from .authorization import authorizedSpotify
from ..loggingBase import getSubLoggerFor



#====================
#=== Initializing ===
#====================
logger = getSubLoggerFor('utility')

# We assume that authorizedSpotify has already been set up with a clientID and
# clientSecret somewhere else
spotify = authorizedSpotify()

logger.info('Obtained authorized spotify client')



#=================
#=== Functions ===
#=================
def searchForSong(songName, artist = None):
    # None evaluates to False
    if artist:
        results = spotify.search(artist + ' - ' + songName)
    else:
        results = spotify.search(songName)
    
    # Supposed best match
    rawTrackMeta = results['tracks']['items'][0]

    # I assume this works
    return 'http://open.spotify.com/track/' + rawTrackMeta['id']



#===============
#=== Classes ===
#===============
class trackDetails(object):
    # This class is used during both the search phase and also the metadata['duration_ms]
    # phase. Interesting, don't you think?

    def __init__(self, url):
        global spotify

        # Spotify api response, (JSON)
        rawTrackMeta = spotify.track(url)

        # Keeping theese for now, will probably use only for genres
        # rawArtistMeta = spotify.artist(rawTrackMeta['artists'][0]['id'])
        # rawAlbumMeta = spotify.album(rawTrackMeta['album']['id'])
    
        # Song related Details as follows:
        # 1. Song name
        self.songName = rawTrackMeta['name']

        # 2. Track number
        self.trackNumber = rawTrackMeta['track_number']

        # 3. genres
        # How? From album or artists? stack Overflow?
        # and also, single or multiple genres?

        # 4. Length
        self.length = rawTrackMeta['duration_ms'] / 1000.0

        # 5. Contributing artists
        self.contributingArtists = []

        for artist in rawTrackMeta['artists']:
            self.contributingArtists.append(artist['name'])

        # Album related Details as follows:
        # 1. Album name
        self.albumName = rawTrackMeta['album']['name']

        # 2. Album artists
        self.albumArtists = []

        for artist in rawTrackMeta['album']['artists']:
            self.albumArtists.append(artist['name'])

        # 3. Album release date/year
        self.albumRelease = rawTrackMeta['album']['release_date']

        # Other utilities
        # 1. Album art
        self.albumArtURL = rawTrackMeta['album']['images']['url']