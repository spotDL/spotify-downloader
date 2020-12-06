#===============
#=== Imports ===
#===============

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials


class SpotifyClient:
    
    #=========================
    #=== The actual action ===
    #=========================
    
    def __init__(self, clientId: str, clientSecret: str):
        '''
        `str` `clientId` : client id from your spotify account
        
        `str` `clientSecret` : client secret for your client id
    
        RETURNS `SpotifyClient`
    
        creates a spotify client
        '''

        # create Oauth credentials for the SpotifyClient
        credentialManager = SpotifyClientCredentials(
            client_id = clientId,
            client_secret = clientSecret
        )
    
        client = Spotify(client_credentials_manager = credentialManager)
        
        self.client = client

    def get(self) -> Spotify:
        return self.client