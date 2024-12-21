"""
Module for interacting with Spotify API.
To use this module, you must have a Spotify API key and Spotify API secret.

```python
import spotdl.utils.spotify
spotify.Spotify.init(client_id, client_secret)
```
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple, Union
from datetime import datetime

import requests
from spotipy import Spotify
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from spotdl.utils.config import get_cache_path, get_spotify_cache_path

__all__ = [
    "SpotifyError",
    "SpotifyClient",
    "save_spotify_cache",
]

logger = logging.getLogger(__name__)


class SpotifyError(Exception):
    """
    Base class for all exceptions related to SpotifyClient.
    """


class RateLimitHandler:
    """
    Handles rate limiting for Spotify API requests
    """
    def __init__(self):
        self.rate_limits = {}
        self.requests_timestamp = []
        # Spotify's default rate limits
        self.max_requests_per_window = 100
        self.window_size = 30  # seconds

    def update_limits(self, response: Union[requests.Response, Dict]) -> None:
        """Update rate limit information from response headers or error dict"""
        if isinstance(response, requests.Response):
            headers = response.headers
            self.rate_limits = {
                'remaining': int(headers.get('Retry-After', 0)),
                'reset': int(headers.get('X-RateLimit-Reset', 0)),
                'limit': int(headers.get('X-RateLimit-Limit', self.max_requests_per_window))
            }
        elif isinstance(response, dict) and 'error' in response:
            error = response['error']
            if error.get('status') == 429:
                self.rate_limits = {
                    'remaining': int(error.get('Retry-After', 0)),
                    'reset': int(time.time() + error.get('Retry-After', 0)),
                    'limit': self.max_requests_per_window
                }

    def should_retry(self, response: Union[requests.Response, Dict]) -> Tuple[bool, float]:
        """Determine if request should be retried and how long to wait"""
        # Check if it's a rate limit response
        is_rate_limited = False
        if isinstance(response, requests.Response):
            is_rate_limited = response.status_code == 429
        elif isinstance(response, dict) and 'error' in response:
            is_rate_limited = response['error'].get('status') == 429

        if not is_rate_limited:
            return False, 0

        self.update_limits(response)
        wait_time = self.rate_limits.get('remaining', 1)
        return True, wait_time

    def track_request(self) -> None:
        """Track new request and clean old ones"""
        current_time = time.time()
        self.requests_timestamp = [
            ts for ts in self.requests_timestamp
            if current_time - ts < self.window_size
        ]
        self.requests_timestamp.append(current_time)

    def should_wait(self) -> Tuple[bool, float]:
        """Check if we should wait before making a new request"""
        if len(self.requests_timestamp) < self.max_requests_per_window:
            return False, 0

        oldest_timestamp = self.requests_timestamp[0]
        current_time = time.time()
        time_passed = current_time - oldest_timestamp

        if time_passed < self.window_size:
            wait_time = self.window_size - time_passed
            return True, wait_time
        return False, 0


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
        user_auth: bool = False,
        no_cache: bool = False,
        headless: bool = False,
        max_retries: int = 3,
        use_cache_file: bool = False,
        auth_token: Optional[str] = None,
        cache_path: Optional[str] = None,
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
                redirect_uri="http://127.0.0.1:9900/",
                scope="user-library-read,user-follow-read,playlist-read-private",
                cache_handler=cache_handler,
                open_browser=not headless,
                requests_timeout=10,
            )
        # Use SpotifyClientCredentials as auth manager
        else:
            credential_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
                cache_handler=cache_handler,
                requests_timeout=10,
            )
        if auth_token is not None:
            credential_manager = None

        self.user_auth = user_auth
        self.no_cache = no_cache
        self.max_retries = max_retries
        self.use_cache_file = use_cache_file

        # Create instance
        self._instance = super().__call__(
            auth=auth_token,
            auth_manager=credential_manager,
            status_forcelist=(429, 500, 502, 503, 504, 404),
            retries=0,
            status_retries=0,
            requests_timeout=5,
            backoff_factor=1,
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
    cache: Dict[str, Optional[Dict]] = {}

    def __init__(self, *args, **kwargs):
        """
        Initializes the SpotifyClient.

        ### Arguments
        - auth: The access token to use.
        - auth_manager: The auth manager to use.
        """

        super().__init__(*args, **kwargs)
        self._initialized = True
        self.rate_limit_handler = RateLimitHandler()

        use_cache_file: bool = self.use_cache_file  # type: ignore # pylint: disable=E1101
        cache_file_loc = get_spotify_cache_path()

        if use_cache_file and cache_file_loc.exists():
            with open(cache_file_loc, "r", encoding="utf-8") as cache_file:
                self.cache = json.load(cache_file)
        elif use_cache_file:
            with open(cache_file_loc, "w", encoding="utf-8") as cache_file:
                json.dump(self.cache, cache_file)

    def _get(self, url, args=None, payload=None, **kwargs):
        """
        Overrides the get method of the SpotifyClient.
        Allows us to cache requests and handle rate limiting
        """

        use_cache = not self.no_cache  # type: ignore # pylint: disable=E1101

        if args:
            kwargs.update(args)

        # Check cache first
        cache_key = None
        if use_cache:
            key_obj = dict(kwargs)
            key_obj["url"] = url
            key_obj["data"] = json.dumps(payload)
            cache_key = json.dumps(key_obj)
            if cache_key is None:
                cache_key = url
            if self.cache.get(cache_key) is not None:
                return self.cache[cache_key]

        # Rate limit checking
        should_wait, wait_time = self.rate_limit_handler.should_wait()
        if should_wait:
            logger.debug(f"Rate limit approaching, waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)

        # Wrap in a try-except and retry up to `retries` times.
        response = None
        retries = self.max_retries  # type: ignore # pylint: disable=E1101
        while response is None and retries > 0:
            try:
                self.rate_limit_handler.track_request()
                response = self._internal_call("GET", url, payload, kwargs)

                # Handle rate limit response
                should_retry, retry_after = self.rate_limit_handler.should_retry(response)
                if should_retry:
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    retries -= 1
                    response = None
                    continue

            except (requests.exceptions.Timeout, requests.ConnectionError) as exc:
                retries -= 1
                if retries <= 0:
                    raise exc
                time.sleep(1)  # Basic backoff

        if response is None:
            raise SpotifyError("Max retries exceeded")

        if use_cache and cache_key is not None:
            self.cache[cache_key] = response

        return response

    def get_rate_limit_status(self) -> Dict:
        """
        Get current rate limit status

        ### Returns
        - Dict containing current rate limits and request count
        """
        return {
            'limits': self.rate_limit_handler.rate_limits,
            'requests_in_window': len(self.rate_limit_handler.requests_timestamp),
            'window_size': self.rate_limit_handler.window_size
        }


def save_spotify_cache(cache: Dict[str, Optional[Dict]]):
    """
    Saves the Spotify cache to a file.

    ### Arguments
    - cache: The cache to save.
    """

    cache_file_loc = get_spotify_cache_path()

    logger.debug("Saving Spotify cache to %s", cache_file_loc)

    # Only cache tracks
    cache = {
        key: value
        for key, value in cache.items()
        if value is not None and "tracks/" in key
    }

    with open(cache_file_loc, "w", encoding="utf-8") as cache_file:
        json.dump(cache, cache_file)
