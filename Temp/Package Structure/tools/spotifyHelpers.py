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
    # This class is used during both the search phase and also the metadata
    # phase. Interesting, don't you think?

    def __init__(self, url):
        global spotify

        # Spotify api response, (JSON)
        rawTrackMeta = spotify.track(url)
        rawArtistMeta = spotify.artist(rawTrackMeta['artists'][0]['id'])
        rawAlbumMeta = spotify.album(rawTrackMeta['album']['id'])

        # I'm not sure if theses are the right indexes and don't have an
        # internet connection at the moment, commenting them out for future
        # tests. the correctness of the uncommented code is also questionable
        #
        # self.songName = rawTrackMeta['name']
        # self.albumArtist = rawArtistMeta['artists'][0]['name']
        # 
        # self.contributingArtist = []
        # 
        # for artist in rawArtistMeta[1:]:
        #     self.contributingArtist.append(artist['name'])
        # 
        # self.album = rawAlbumMeta['name']

        albumReleaseYear = rawAlbumMeta['release_date'].split('-')[0]
        self.year = int(albumReleaseYear)

        # How to songnumber?

        # Can we make this song specific instead of artist basesd?
        # Should we consider all artists?
        if 'genres' in rawTrackMeta.keys():
            self.genre = rawArtistMeta['genres'][0].title()

        self.length = rawTrackMeta['duration_ms'] / 1000

        # The following provided by @ritek, should we retain theese?
        if 'copyrights' in rawAlbumMeta.keys():
            self.copyright = rawAlbumMeta['copyrights'][0]['text']
        
        self.releaseDate = rawAlbumMeta['release_date']
        self.label = rawAlbumMeta['label']
        self.totalTracks = rawAlbumMeta['tracks']['total']

        logger.info('Obtained details for ' + url)