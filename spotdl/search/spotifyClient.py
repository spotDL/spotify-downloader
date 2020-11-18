#===============
#=== Imports ===
#===============

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import pickle
from os import path


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

    creates and caches a spotify client if a client doesn't exist. Can only be called
    once, multiple calls will cause an Exception.
    '''

    # check if initialization has been completed, if yes, raise an Exception
    #! None evaluates to False, objects evaluate to True.
    global masterClient

    # create Oauth credentials for the SpotifyClient
    credentialManager = SpotifyClientCredentials(
        client_id = clientId,
        client_secret = clientSecret
    )

    client = Spotify(client_credentials_manager = credentialManager)

    # Save credentials as serialized binary file. If file does not exist, create now one. Overwrite if it does exist.
    with open("spotify.spotdlKey", "wb") as pickle_out:
        pickle.dump(client, pickle_out)
    
    masterClient = client


def get_spotify_client():
    '''
    RETURNS `Spotify`

    returns a cached spotify client of type `spotipy.Spotify`, can only be called after a
    call to `spotifyClient.initialize(clientId, clientSecret)`
    '''

    global masterClient
    
    #! None evaluates to False, Objects evaluate to True
    if masterClient:
        return masterClient

    # Checks if the credentials have been put in a file. Useful for multiprocessing applications
    if path.exists("spotify.spotdlKey"):
        with open("spotify.spotdlKey", "rb") as input:
            client = pickle.load(input)
        return client

    else:
        raise Exception('Spotify client not created. Call spotifyClient.initialize' +
            '(clientId, clientSecret) first.')