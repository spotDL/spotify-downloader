"""
Module for interacting with Spotify API.
To use this module, you must have a Spotify API key and Spotify API secret.

```python
import spotdl.utils.spotify
spotify.Spotify.init(client_id, client_secret)
```
"""

from typing import Dict, Optional

from spotipy import Spotify
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from spotdl.utils.config import get_cache_path

cache: Dict[str, Dict] = {}


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

    def __call__(self):  # pylint: disable=bad-mcs-method-argument
        """
        Call method for Singleton metaclass.

        ### Returns
        - The instance of the SpotifyClient.
        """

        if self._instance is None:
            raise SpotifyError(
                "Spotify client not created. Call SpotifyClient.init"
                "(client_id, client_secret, user_auth, cache_path, no_cache, open_browser) first."
            )
        return self._instance

    def init(  # pylint: disable=bad-mcs-method-argument
        self,
        client_id: str,
        client_secret: str,
        auth_token: Optional[str] = None,
        user_auth: bool = False,
        cache_path: Optional[str] = None,
        no_cache: bool = False,
        open_browser: bool = True,
    ) -> "Singleton":
        """
        Initializes the SpotifyClient.

        ### Arguments
        - client_id: The client ID of the application.
        - client_secret: The client secret of the application.
        - auth_token: The access token to use.
        - user_auth: Whether or not to use user authentication.
        - cache_path: The path to the cache file.
        - no_cache: Whether or not to use the cache.
        - open_browser: Whether or not to open the browser.

        ### Returns
        - The instance of the SpotifyClient.
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
                open_browser=open_browser,
            )
        # Use SpotifyClientCredentials as auth manager
        else:
            credential_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
                cache_handler=cache_handler,
            )
        if auth_token is not None:
            credential_manager = None

        self.user_auth = user_auth
        self.no_cache = no_cache

        # Create instance
        self._instance = super().__call__(
            auth=auth_token,
            auth_manager=credential_manager,
            status_forcelist=(429, 500, 502, 503, 504, 404),
        )

        # Return instance
        return self._instance


class SpotifyClient(Spotify, metaclass=Singleton):
    """
    This is the Spotify client meant to be used in the app.
    Has to be initialized first by calling
    `SpotifyClient.init(client_id, client_secret, user_auth, cache_path, no_cache, open_browser)`.
    """

    _initialized = False

    def __init__(self, *args, **kwargs):
        """
        Initializes the SpotifyClient.

        ### Arguments
        - auth: The access token to use.
        - auth_manager: The auth manager to use.
        """

        super().__init__(*args, **kwargs)
        self._initialized = True

    def _get(self, url, args=None, payload=None, **kwargs):
        """
        Overrides the get method of the SpotifyClient.
        Allows us to cache requests
        """

        use_cache = not self.no_cache  # type: ignore # pylint: disable=E1101

        if args:
            kwargs.update(args)

        if use_cache:
            if cache.get(url) is not None:
                return cache[url]

        response = self._internal_call("GET", url, payload, kwargs)

        if use_cache:
            cache[url] = response

        return response
