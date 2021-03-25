from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials


class Singleton(type):
    """
    Singleton metaclass for SpotifyClient. Ensures that SpotifyClient is not
    instantiated without prior initialization. Every other instantiation of
    SpotifyClient will return the same instance.
    """
    _instance = None

    def __call__(cls):
        if cls._instance is None:
            raise Exception('Spotify client not created. Call SpotifyClient.init'
                            '(client_id, client_secret) first.')
        return cls._instance

    def init(cls, client_id: str, client_secret: str) -> "Singleton":
        '''
        `str` `client_id` : client id from your spotify account

        `str` `client_secret` : client secret for your client id

        creates and caches a spotify client if a client doesn't exist. Can only be called
        once, multiple calls will cause an Exception.
        '''

        # check if initialization has been completed, if yes, raise an Exception
        if cls._instance and cls._instance.is_initialized():
            raise Exception('A spotify client has already been initialized')

        credentialManager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        cls._instance = super().__call__(client_credentials_manager=credentialManager)
        return cls._instance


class SpotifyClient(Spotify, metaclass=Singleton):
    """
    This is the Spotify client meant to be used in the app. Has to be initialized first by
    calling `SpotifyClient.init(client_id, client_secret)`.
    """
    _initialized = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = True

    def is_intialized(self):
        return self._initialized
