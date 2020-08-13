#===============
#=== Imports ===
#===============
from tools import spotifyHelpers



#===============
#=== Classes ===
#===============
class metadataProvider(object):
    def __init__(self):
        pass

    def getDetails(self, song):
        songUrl = song.spotifyLink
        songDetails = spotifyHelpers.trackDetails(songUrl)

        return songDetails
    
    def getLyrics(self, song):
        return None