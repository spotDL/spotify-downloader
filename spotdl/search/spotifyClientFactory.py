#===============
#=== Imports ===
#===============

from spotdl.search.spotifyClient import SpotifyClient


class SpotifyClientFactory:

    def build(self, clientId: str, clientSecret: str) -> SpotifyClient:
        '''
        `str` `clientId` : client id from your spotify account
        
        `str` `clientSecret` : client secret for your client id
    
        RETURNS `SpotifyClient`
        ''
    
        creates a SpotifyClient instance
        '''

        return SpotifyClient(
                clientId = clientId,
                clientSecret = clientSecret
            )
