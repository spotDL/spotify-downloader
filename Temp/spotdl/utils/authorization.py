# This might have to move to a 'tools' submodule

#===============
#=== Imports ===
#===============
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from requests import Session

from spotdl.utils.loggingBase import getSubLoggerFor



#==================
#=== Exceptions ===
#==================
class spotifyAuthorizationError(Exception): pass



#========================
#=== Module Variables ===
#========================

# masterClient keeps the last logged-in client object in memory for persistance
masterClient = None

# logger
logger = getSubLoggerFor('authorization')



#=========================
#=== Utility functions ===
#=========================

def initialize():
    # initializes and caches spotifyClient
    getSpotifyClient(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )



#===============
#=== Classes ===
#===============

def getSpotifyClient(clientId = None, clientSecret = None):
    '''
    `str` `clientID` : Spotify client id

    `str` `clientSecret` : Spotify client secret

    returns cached Spotify client if available, else attempts to create
    and return a fresh client of type `spotify.Spotify`
    '''

    global masterClient

    # check if inputs are valid and usable
    credentialsProvided = (clientId != None) and (clientSecret != None)
    validInput = credentialsProvided or (masterClient != None)

    # if not valid input, raise error, else either pass on cached client or
    # create a new one as required
    if not validInput:
        logger.critical('Could not authorize Spotify Credentials, no' +
        ' clientId, clientSecret provided')
        raise spotifyAuthorizationError ('You must pass a clientId and' +
        ' clientSecret to this method when authenticating for first time')

    # Note that None can be used as False
    elif masterClient:
        logger.info('Returning cached Spotify Credentials')
    
    else:
        logger.info('Creating authorized Spotify Client >')
        
        # Oauth
        credentialManager = SpotifyClientCredentials(
            client_id = clientId,
            client_secret = clientSecret
        )
        spotifyClient = Spotify(client_credentials_manager = credentialManager)
        
        # Cache current client
        masterClient = spotifyClient
    
        logger.info('Client successfully created')
    
    return masterClient
