"""
Module for interacting with Spotify API.
To use this module, you must have a Spotify API key and Spotify API secret.

```python
import spotdl.utils.spotify
spotify.Spotify.init(client_id, client_secret)
```
"""

import atexit
import concurrent.futures
import inspect
import json
import logging
from contextlib import suppress
from functools import lru_cache, partial
from threading import Lock, local
from typing import Any, Dict, Optional

import requests
import spotapi
from spotapi.client import BaseClient
from spotapi.exceptions import BaseClientError, RequestError
from spotapi.http.request import TLSClient
from spotapi.types.alias import _Undefined
from spotapi.utils.strings import combine_chunks, extract_mappings
from spotipy import Spotify
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from SpotipyFree import Spotify as FreeSpotify
from SpotipyFree.Formatter import SpotifyFormatter

from spotdl.utils.config import get_cache_path, get_spotify_cache_path

__all__ = [
    "SpotifyError",
    "SpotifyClient",
    "SpotifyMetadata",
    "save_spotify_cache",
]

logger = logging.getLogger(__name__)

OFFICIAL_API_ONLY_OPTIONS = {
    "auth_token": "--auth-token",
    "user_auth": "--user-auth",
    "use_cache_file": "--use-cache-file",
}


class SpotifyError(Exception):
    """
    Base class for all exceptions related to SpotifyClient.
    """


class _OfficialSpotifyClient(Spotify):
    """
    Spotipy-backed Spotify client used when the official API is requested.
    """

    cache: Dict[str, Optional[Dict]] = {}

    @classmethod
    def init(
        cls,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        no_cache: bool = False,
        headless: bool = False,
        max_retries: int = 3,
        use_cache_file: bool = False,
        auth_token: Optional[str] = None,
        cache_path: Optional[str] = None,
    ) -> "_OfficialSpotifyClient":
        """
        Initializes the official SpotifyClient implementation.
        """

        credential_manager = None

        cache_handler = (
            CacheFileHandler(cache_path or get_cache_path())
            if not no_cache
            else MemoryCacheHandler()
        )
        if user_auth:
            credential_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://127.0.0.1:9900/",
                scope="user-library-read,user-follow-read,playlist-read-private",
                cache_handler=cache_handler,
                open_browser=not headless,
            )
        else:
            credential_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
                cache_handler=cache_handler,
            )

        if auth_token is not None:
            credential_manager = None

        client = cls(
            auth=auth_token,
            auth_manager=credential_manager,
            status_forcelist=(429, 500, 502, 503, 504, 404),
        )
        client.user_auth = user_auth
        client.no_cache = no_cache
        client.max_retries = max_retries
        client.use_cache_file = use_cache_file

        cache_file_loc = get_spotify_cache_path()
        if use_cache_file and cache_file_loc.exists():
            with open(cache_file_loc, "r", encoding="utf-8") as cache_file:
                client.cache = json.load(cache_file)
        elif use_cache_file:
            with open(cache_file_loc, "w", encoding="utf-8") as cache_file:
                json.dump(client.cache, cache_file)

        return client

    def _get(self, url, args=None, payload=None, **kwargs):
        """
        Overrides the get method of the SpotifyClient.
        Allows us to cache requests.
        """

        use_cache = not self.no_cache  # type: ignore # pylint: disable=E1101

        if args:
            kwargs.update(args)

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

        response = None
        retries = self.max_retries  # type: ignore # pylint: disable=E1101
        while response is None:
            try:
                response = self._internal_call("GET", url, payload, kwargs)
            except (requests.exceptions.Timeout, requests.ConnectionError) as exc:
                retries -= 1
                if retries <= 0:
                    raise exc

        if use_cache and cache_key is not None:
            self.cache[cache_key] = response

        return response


@lru_cache(maxsize=2)
def _load_query_definitions(player_url: str) -> str:
    # These CDN requests carry no Spotify authentication or user metadata.
    with TLSClient("chrome120", "", auto_retries=3) as transport:
        atexit.unregister(transport.close)

        def fetch(url: str) -> str:
            response = transport.get(url)
            if response.fail:
                raise BaseClientError(
                    "Could not get general hashes", error=response.error.string
                )
            return str(response.response)

        player = fetch(player_url)
        names, hashes = extract_mappings(player)
        urls = [
            f"https://open.spotifycdn.com/cdn/build/web-player/{chunk}"
            for chunk in combine_chunks(hashes, names)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            return player + "".join(executor.map(fetch, urls))


_SHARED_TLS_CLIENTS = {
    kwdefaults["client"]
    for cls in (
        spotapi.Song,
        spotapi.PublicAlbum,
        spotapi.Artist,
        spotapi.PublicPlaylist,
    )
    if (kwdefaults := inspect.unwrap(cls.__init__).__kwdefaults__)
    and kwdefaults.get("client") is not None
}
_ORIG_BASE_INIT = BaseClient.__init__
_thread_local = local()
_session_lock = Lock()


class _ThreadTLSClient(TLSClient):
    """Per-thread TLSClient that resets its connection pool after a request error."""

    def build_request(self, method, url, **kwargs):
        """Discard the transport after exhausted retries."""
        try:
            return super().build_request(method, url, **kwargs)
        except RequestError:
            if getattr(_thread_local, "client", None) is self:
                del _thread_local.client
            with suppress(Exception):
                self.close()
            raise


@lru_cache(maxsize=1)
def _anonymous_session() -> BaseClient:
    transport = TLSClient("chrome120", "", auto_retries=3)
    atexit.unregister(transport.close)
    return BaseClient(transport)


def _reuse_query_definitions(base: BaseClient) -> None:
    with _session_lock:
        session = _anonymous_session()
        if session.js_pack is _Undefined:
            session.get_session()
        if session.raw_hashes is _Undefined:
            session.raw_hashes = _load_query_definitions(str(session.js_pack))
        base.raw_hashes = session.raw_hashes


def _init_base_client(
    self: BaseClient, client: TLSClient, language: str = "en"
) -> None:
    if client not in _SHARED_TLS_CLIENTS:
        _ORIG_BASE_INIT(self, client, language=language)
        return

    # SpotAPI's public endpoints share transport callbacks. Isolate them by thread.
    if not hasattr(_thread_local, "client"):
        _thread_local.client = _ThreadTLSClient("chrome120", "", auto_retries=3)
    client = _thread_local.client
    _ORIG_BASE_INIT(self, client, language=language)
    atexit.unregister(client.close)
    sent_token = None

    def authenticate(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal sent_token
        with _session_lock:
            session = _anonymous_session()
            # pylint: disable-next=protected-access
            kwargs = session._auth_rule(kwargs)
            sent_token = session.access_token
        kwargs["headers"]["Accept-Language"] = language
        return kwargs

    def on_auth_failure(resp: Any) -> bool:
        with _session_lock:
            session = _anonymous_session()
            if (
                resp.status_code == 401
                and sent_token is not None
                and sent_token != session.access_token
            ):
                return True
            # pylint: disable-next=protected-access
            return session._handle_auth_failure(resp)

    self.get_sha256_hash = partial(_reuse_query_definitions, self)  # type: ignore[method-assign]
    client.authenticate = authenticate
    client.on_auth_failure = on_auth_failure


class _FreeSpotifyClient(FreeSpotify):
    """Use full discography queries instead of the ten-release artist overview."""

    # Match the SpotipyFree signature, including its unused paging arguments.
    def artist_albums(  # pylint: disable=invalid-name,unused-argument,keyword-arg-before-vararg
        self, artistId, limit=-1, offset=0, include_groups="album", *args, **kwargs
    ) -> Dict[str, Any]:
        """Return every release in the requested discography sections."""
        artist_id = self.urlToId(artistId.partition("?")[0].rstrip("/")).rsplit(":", 1)[
            -1
        ]
        requested = set(include_groups.split(","))
        api = spotapi.Artist()
        sections = (
            ("album", "albums"),
            ("single", "singles"),
            ("compilation", "compilations"),
        )
        release_ids: Dict[str, None] = {}
        for group, section in sections:
            if group in requested:
                for page in api.paginate_artist_discography(artist_id, section=section):
                    for item in page:
                        for release in item["releases"]["items"]:
                            release_ids[release["id"]] = None

        releases = []
        for release_id in release_ids:
            album = self.album(release_id)
            if not album:
                raise ValueError(f"Could not get artist release: {release_id}")
            releases.append(album)
        return SpotifyFormatter.addChunkInfo(releases)


def _init_official_spotify_client(**kwargs) -> _OfficialSpotifyClient:
    """
    Initialize the official Spotipy client.
    """

    return _OfficialSpotifyClient.init(**kwargs)


def _init_free_spotify_client(**kwargs) -> Any:
    """
    Initialize the default SpotipyFree client.
    """

    BaseClient.__init__ = _init_base_client  # type: ignore[method-assign]
    return _FreeSpotifyClient(**kwargs)


class SpotifyClient:
    """
    Runtime-selected Spotify client facade.
    """

    _instance: Optional[Any] = None
    _use_official_api = False

    def __new__(cls):
        """
        Return the initialized Spotify client implementation.
        """

        if cls._instance is None:
            raise SpotifyError(
                "Spotify client not created. Call SpotifyClient.init"
                "("
                "client_id, client_secret, user_auth=False, no_cache=False, "
                "headless=False, max_retries=3, use_cache_file=False, "
                "use_official_api=False, auth_token=None, cache_path=None"
                ") first."
            )

        return cls._instance

    def __getattr__(self, name: str) -> Any:
        """
        The selected backend provides Spotify API methods at runtime.
        """

        raise AttributeError(name)

    @classmethod
    def is_using_official_api(cls) -> bool:
        """
        Returns whether the active client uses the official Spotify Web API.
        """

        return cls._use_official_api

    @classmethod
    def init(
        cls,
        client_id: str,
        client_secret: str,
        user_auth: bool = False,
        no_cache: bool = False,
        headless: bool = False,
        max_retries: int = 3,
        use_cache_file: bool = False,
        use_official_api: bool = False,
        auth_token: Optional[str] = None,
        cache_path: Optional[str] = None,
    ) -> Any:
        """
        Initializes the selected SpotifyClient implementation.
        """

        if cls._instance is not None:
            raise SpotifyError("A spotify client has already been initialized")

        kwargs = {
            "client_id": client_id,
            "client_secret": client_secret,
            "user_auth": user_auth,
            "no_cache": no_cache,
            "headless": headless,
            "max_retries": max_retries,
            "use_cache_file": use_cache_file,
            "auth_token": auth_token,
            "cache_path": cache_path,
        }

        official_only_options = [
            option for key, option in OFFICIAL_API_ONLY_OPTIONS.items() if kwargs[key]
        ]
        if official_only_options and not use_official_api:
            logger.info(
                "Using the official Spotify Web API because %s %s requested.",
                ", ".join(official_only_options),
                "was" if len(official_only_options) == 1 else "were",
            )
            use_official_api = True

        if use_official_api:
            cls._instance = _init_official_spotify_client(**kwargs)
        else:
            cls._instance = _init_free_spotify_client(**kwargs)

        cls._use_official_api = use_official_api

        return cls._instance


class SpotifyMetadata:
    """Reuse read-only track, album and artist responses within one parse."""

    def __init__(self):
        cache = lru_cache(maxsize=128)
        self.track = cache(lambda url: SpotifyClient().track(url))
        self.artist = cache(lambda artist_id: SpotifyClient().artist(artist_id))
        self.album = cache(lambda album_id: SpotifyClient().album(album_id))


def save_spotify_cache(cache: Dict[str, Optional[Dict]]):
    """
    Saves the Spotify cache to a file when the official API client is active.

    ### Arguments
    - cache: The cache to save.
    """

    if not SpotifyClient.is_using_official_api():
        return

    cache_file_loc = get_spotify_cache_path()

    logger.debug("Saving Spotify cache to %s", cache_file_loc)

    cache = {
        key: value
        for key, value in cache.items()
        if value is not None and "tracks/" in key
    }

    with open(cache_file_loc, "w", encoding="utf-8") as cache_file:
        json.dump(cache, cache_file)
