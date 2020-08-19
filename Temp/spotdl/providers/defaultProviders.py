'''
Implementation of the Search interfaces defined in interfaces.md
'''



#===============
#=== Imports ===
#===============
from defaultObjects import metadataObject



#========================
#=== Provider Classes ===
#========================
class metadataProvider(object):

    def __init__(self): pass

    def getDetails(self, songObj):
        # The metadata class is the same as the trackDetails class from
        # spotdl.utils.spotifyHelpers.py, it takes a spotify Url as its
        # __init__ arg and implements the metadata object interface over
        # metadata queried from spotify.
        #
        # see also, comment above metadata class declaration in
        # defaultObjects.py
        
        return metadataObject(songObj.getSpotifyLink())
    
    def getLyrics(self, songObj):
        # Not yet implemented, return None as-per the interface rules from
        # interface.md
        return None

class searchProvider(object):
    # To be implemented
    pass