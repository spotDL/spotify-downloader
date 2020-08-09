import spotipy
import spotipy.oauth2 as oauth2

from spotdl.metadata import ProviderBase
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError

from spotdl.authorize.services import AuthorizeSpotify
from spotdl.authorize import SpotifyAuthorizationError
import spotdl.util

import logging
logger = logging.getLogger(__name__)


class ProviderSpotify(ProviderBase):
    """
    Fetch metadata using Spotify API in standardized form.

    Parameters
    ----------
    spotify: :class:`spotdl.authorize.services.AuthorizeSpotify`, :class:`spotipy.Spotify`, ``None``
        An authorized instance to make API calls to Spotify endpoints.

        If ``None``, it will attempt to reference an already created
        :class:`spotdl.authorize.services.AuthorizeSpotify` instance
        or you can set your own *Client ID* and *Client Secret*
        by calling :func:`ProviderSpotify.set_credentials` later on.

    Examples
    --------
    - Fetching a track's metadata using Spotify URI:

        >>> from spotdl.authorize.services import AuthorizeSpotify
        # It is necessary to authorize Spotify API otherwise API
        # calls won't pass through Spotify. That means we won't
        # be able to fetch metadata from Spotify.
        >>> AuthorizeSpotify(
        ...     client_id="your_spotify_client_id",
        ...     client_secret="your_spotify_client_secret",
        ... )
        >>>
        >>> from spotdl.metadata.providers import ProviderSpotify
        >>> provider = ProviderSpotify()
        >>> metadata = provider.from_url(
        ...     "https://open.spotify.com/track/0aTiUssEOy0Mt69bsavj6K"
        ... )
        >>> metadata["name"]
        'Descending'
    """

    def __init__(self, spotify=None):
        if spotify is None:
            try:
                spotify = AuthorizeSpotify()
            except SpotifyAuthorizationError:
                pass
        self.spotify = spotify

    def set_credentials(self, client_id, client_secret):
        """
        Set your own credentials to authorize with Spotify API.
        This is useful if you initially didn't authorize API calls
        while creating an instance of :class:`ProviderSpotify`.
        """
        token = self._generate_token(client_id, client_secret)
        self.spotify = spotipy.Spotify(auth=token)

    def assert_credentials(self):
        if self.spotify is None:
            raise SpotifyAuthorizationError(
                "You must first setup an AuthorizeSpotify instance, or pass "
                "in client_id and client_secret to the set_credentials method."
            )

    def from_url(self, url):
        self.assert_credentials()
        logger.debug('Fetching Spotify metadata for "{url}".'.format(url=url))
        metadata = self.spotify.track(url)
        return self._metadata_to_standard_form(metadata)

    def from_query(self, query):
        self.assert_credentials()
        tracks = self.search(query)["tracks"]["items"]
        if not tracks:
            raise SpotifyMetadataNotFoundError(
                'Spotify returned no tracks for the search query "{}".'.format(
                    query,
                )
            )
        return self._metadata_to_standard_form(tracks[0])

    def search(self, query):
        self.assert_credentials()
        return self.spotify.search(query)

    def _generate_token(self, client_id, client_secret):
        credentials = oauth2.SpotifyClientCredentials(
            client_secret=client_secret,
        )
        token = credentials.get_access_token()
        return token

    def _metadata_to_standard_form(self, metadata):
        self.assert_credentials()
        artist = self.spotify.artist(metadata["artists"][0]["id"])
        album = self.spotify.album(metadata["album"]["id"])

        try:
            metadata[u"genre"] = spotdl.util.titlecase(artist["genres"][0])
        except IndexError:
            metadata[u"genre"] = None
        try:
            metadata[u"copyright"] = album["copyrights"][0]["text"]
        except IndexError:
            metadata[u"copyright"] = None
        try:
            metadata[u"external_ids"][u"isrc"]
        except KeyError:
            metadata[u"external_ids"][u"isrc"] = None

        metadata[u"release_date"] = album["release_date"]
        metadata[u"publisher"] = album["label"]
        metadata[u"total_tracks"] = album["tracks"]["total"]

        # Some sugar
        metadata["year"], *_ = metadata["release_date"].split("-")
        metadata["duration"] = metadata["duration_ms"] / 1000.0
        metadata["provider"] = "spotify"

        # Remove unwanted parameters
        del metadata["duration_ms"]
        del metadata["available_markets"]
        del metadata["album"]["available_markets"]

        return metadata

