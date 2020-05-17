from spotdl.authorize import AuthorizeBase
from spotdl.authorize.exceptions import SpotifyAuthorizationError

import spotipy
import spotipy.oauth2 as oauth2

import logging
logger = logging.getLogger(__name__)

# This masterclient is used to keep the last logged-in client
# object in memory for for persistence. If credentials aren't
# provided when creating further objects, the last authenticated
# client object with correct credentials is returned when
# `AuthorizeSpotify().authorize()` is called.
masterclient = None

class AuthorizeSpotify(spotipy.Spotify):
    def __init__(self, client_id=None, client_secret=None):
        global masterclient

        credentials_provided = client_id is not None \
                           and client_secret is not None
        valid_input = credentials_provided or masterclient is not None

        if not valid_input:
            raise SpotifyAuthorizationError(
                "You must pass in client_id and client_secret to this method "
                "when authenticating for the first time."
            )

        if masterclient:
            logger.debug("Reading cached master Spotify credentials.")
            # Use cached client instead of authorizing again
            # and thus wasting time.
            self.__dict__.update(masterclient.__dict__)
        else:
            logger.debug("Setting master Spotify credentials.")
            credential_manager = oauth2.SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            super().__init__(client_credentials_manager=credential_manager)
            # Cache current client
            masterclient = self

