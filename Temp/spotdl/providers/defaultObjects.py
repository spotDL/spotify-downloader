'''
Implementation of the Object interfaces defined in interfaces.md

See interfaces.md on the github repo from more details
'''



#===============
#=== Imports ===
#===============
from spotdl.utils.spotifyHelpers import trackDetails
from spotdl.utils.loggingBase import getSubLoggerFor



#==========================
#=== Initializing Stuff ===
#==========================
logger = getSubLoggerFor('other')



#===============
#=== Classes ===
#===============

# 01. Metadata Object Interface Provider

# trackDetails class form spotdl.utils implements the same interface as a
# metadata object should. So we just reuse the same. As of now, for simplicity,
# no special/specific/feature-rich implementations of the metadata class is
# created.
metadataObject = trackDetails

# 02. Song Object Interface Provider

class songObject(object):
    '''
    Default implementation of the 'song object interface'. It uniquely
    identifies a given song using details from spotify and YouTube Music.
    '''
    
    # name      >   song name
    # artists   >   list of contributing artists
    # sLen      >   length of song on spotify (sec)
    # yLen      >   length of song on youtube (sec)
    # sLink     >   spotify url of song
    # yLink     >   youtube url of song
    def __init__(self, name, artists, sLen, yLen, sLink, yLink, metadata = None):
        
        # Check validity of inputs before assignment, else raise an Exception
        # these exceptions are not meant to be handled so also log a critical
        # message

        # name must be str
        if isinstance(name, str):
            self.name = name
        else:
            logger.critical('name passed to songObject not a str')
            raise Exception('"name" passed to songObject must be a str')

        # artist must be list<str>
        if isinstance(artists, list) and isinstance(artists[0], str):
            self.artists = artists
        else:
            logger.critical('artists passed to songObject not list<str>')
            raise Exception('"artists" passed to songObject must be list<str>')
        
        # sLen, yLen must be int
        if isinstance(sLen, int) and isinstance(yLen, int):
            self.sLen = sLen
            self.yLen = yLen
        else:
            logger.critical('sLen/yLen passed to songObject not int')
            raise Exception('"sLen/yLen" passed to songObject must be int')

        # sLink, yLink must be str, start with 'http'

        if (isinstance(sLink, str) and sLink.startswith('http')) and (
            isinstance(yLink, str) and yLink.startswith('http')):
            self.sLink = sLink
            self.yLink = yLink
        else:
            logger.critical('sLink/yLink passed to songObject not Url\'s')
            raise Exception('"sLink/yLink" passed to songObject must be Url')

        if isinstance(metadata, metadataObject):
            self.metadata = metadata
        else:
            self.metadata = metadataObject(self.sLink)
    
    def getSongName(self):
        '''
        returns name of the song
        '''

        return self.name
    
    def getContributingArtists(self):
        '''
        returns a `list<str>` containing names of contributing artists
        '''

        return self.artists
    
    def getSpotifyLength(self):
        '''
        returns length of song as on Spotify in seconds
        '''

        return self.sLen
    
    def getYoutubeLength(self):
        '''
        returns length of song as on YouTube Music in seconds
        '''

        return self.yLen
    
    def getSpotifyLink(self):
        '''
        returns link of song from Spotify's web player
        '''

        return self.sLink
    
    def getYoutubeLink(self):
        '''
        returns link of the song from YouTube
        '''

        return self.yLink
    
    def getMetadata(self):
        '''
        returns a `metadataObj` containing song metadata
        '''

        return self.metadata