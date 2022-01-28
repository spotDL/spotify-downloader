from spotipy import Spotify
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from spotdl.utils.config import get_cache_path


class SpotifyError(Exception):
    """
    Base class for all exceptions related to SpotifyClient.
    """


class Singleton(type):
    """
    Singleton metaclass for SpotifyClient. Ensures that SpotifyClient is not
    instantiated without prior initialization. Every other instantiation of
    SpotifyClient will return the same instance.
    """

    _instance = None

    def __call__(self):
        if self._instance is None:
            raise SpotifyError(
                "Spotify client not created. Call SpotifyClient.init"
                "(client_id, client_secret, user_auth, cache_path, no_cache) first."
            )
        return self._instance

    def init(
        self,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        cache_path: str = None,
        no_cache: bool = False,
    ) -> "Singleton":
        """
        Initializes the SpotifyClient.
        """

        # check if initialization has been completed, if yes, raise an Exception
        if isinstance(self._instance, self):
            raise SpotifyError("A spotify client has already been initialized")

        credential_manager = None

        cache_handler = (
            CacheFileHandler(cache_path or get_cache_path())
            if not no_cache
            else MemoryCacheHandler()
        )
        # Use SpotifyOAuth as auth manager
        if user_auth:
            credential_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://127.0.0.1:8080/",
                scope="user-library-read",
                cache_handler=cache_handler,
            )
        # Use SpotifyClientCredentials as auth manager
        else:
            credential_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
                cache_handler=cache_handler,
            )

        self.user_auth = user_auth

        # Create instance
        self._instance = super().__call__(auth_manager=credential_manager)

        # Return instance
        return self._instance


class SpotifyClient(Spotify, metaclass=Singleton):
    """
    This is the Spotify client meant to be used in the app. Has to be initialized first by
    calling `SpotifyClient.init(client_id, client_secret, user_auth)`.
    """

    _initialized = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = True
