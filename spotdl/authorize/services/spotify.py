from spotdl.authorize import AuthorizeBase
from spotdl.authorize.exceptions import SpotifyAuthorizationError

import spotipy
import spotipy.oauth2 as oauth2

# This global_client is used to keep the last logged-in client
# object in memory for for persistence. If credentials aren't
# provided when creating further objects, the last authenticated
# client object with correct credentials is returned when
# `AuthorizeSpotify().authorize()` is called.
global_client = None

class AuthorizeSpotify(AuthorizeBase):
    def __init__(self):
        global global_client
        self._client = global_client

    def _generate_token(self, client_id, client_secret):
        """ Generate the token. """
        credentials = oauth2.SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
        token = credentials.get_access_token()
        return token

    def authorize(self, client_id=None, client_secret=None):
        no_credentials_provided = client_id is None and client_secret is None
        not_valid_input = no_credentials_provided and self._client is None

        if not_valid_input:
            raise SpotifyAuthorizationError(
                "You must pass in client_id and client_secret to this method "
                "when authenticating for the first time."
            )

        if no_credentials_provided:
            return self._client

        try:
            token = self._generate_token(client_id, client_secret)
        except spotipy.SpotifyOauthError:
            raise SpotifyAuthorizeError(
                "Failed to retrieve token. Perhaps you provided invalid credentials?"
            )

        spotify = spotipy.Spotify(auth=token)

        self._client = spotify
        global global_client
        global_client = spotify

        return spotify

