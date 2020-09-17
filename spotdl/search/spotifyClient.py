#===============
#=== Imports ===
#===============

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials



#===============
#=== Globals ===
#===============

#! Look through both initialize() and get_spotify_client() for need of masterClient
masterClient = None



#=========================
#=== The actual action ===
#=========================

def initialize(clientId: str, clientSecret: str):
    '''
    `str` `clientId` : client id from your spotify account
    
    `str` `clientSecret` : client secret for your client id

    RETURNS `~`

    creates and caches a spotify client iff. a client doesn't exist. Can only be called
    once, multiple calls will cause an Exception.
    '''

    # check if initialization has been completed, if yes, raise an Exception
    #! None evaluates to False, objects evaluate to True.
    global masterClient

    if masterClient:
        raise Exception('A spotify client has already been initialized')



    # else create and cache a spotify client
    else:
        # create Oauth credentials for the SpotifyClient
        credentialManager = SpotifyClientCredentials(
            client_id = clientId,
            client_secret = clientSecret
        )

        client = Spotify(client_credentials_manager = credentialManager)
        
        masterClient = client

def get_spotify_client():
    '''
    RETURNS `Spotify`

    returns a cached spotify client of type `spotipy.Spotify`, can only be called after a
    call to `spotifyClient.initialize(clientId, clientSecret)`
    '''

    global masterClient
    
    #! None evaluvates to False, Objects evaluate to True
    if masterClient:
        return masterClient

    else:
        raise Exception('Spotify client not created. Call spotifyClient.initialize' +
            '(clientId, clientSecret) first.')