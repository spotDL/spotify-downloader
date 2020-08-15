# This might have to move to a 'tools' submodule

#===============
#=== Imports ===
#===============
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from requests import Session

from ..loggingBase import getSubLoggerFor

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

#===============
#=== Classes ===
#===============

class authorizedSpotify(Spotify):
    '''
    This class is a wrapper around spotipy.Spotify, what it does is to allow
    a one-time creation, multiple-times use is a simple intuitive way.
    '''
    
    def __init__(self, clientId = None, clientSecret = None):
        # spotipy.Spotify uses self.__session
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
            logger.info('Using cached Spotify Credentials')

            self = masterClient
        
        else:
            logger.info('Creating Spotify Credentials')

            # Oauth
            credentialManager = SpotifyClientCredentials(
                client_id = clientId,
                client_secret = clientSecret
            )

            super().__init__(
                client_credentials_manager = credentialManager
            )

            # Cache current client
            masterClient = self
        
        logger.info('Credentials successfully created')
        
    def __del__(self):
        # checking for '_session' in self.__dict__ as when this method is
        # called due to the exception raised in __init__, the '_session'
        # attribute has not yet been created and will trigger another Exception
        # for trying to refer an undefined attribute
        if '_session' in self.__dict__ and isinstance(self._session, Session):
            self._session.close()