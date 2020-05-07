import spotipy
import spotipy.oauth2 as oauth2

from spotdl.metadata import ProviderBase
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError

from spotdl.authorize.services import AuthorizeSpotify
import spotdl.util

import logging
logger = logging.getLogger(__name__)


class ProviderSpotify(ProviderBase):
    def __init__(self, spotify=None):
        if spotify is None:
            spotify = AuthorizeSpotify()
        self.spotify = spotify

    def set_credentials(self, client_id, client_secret):
        token = self._generate_token(client_id, client_secret)
        self.spotify = spotipy.Spotify(auth=token)

    def from_url(self, url):
        logger.debug('Fetching Spotify metadata for "{url}".'.format(url=url))
        metadata = self.spotify.track(url)
        return self.metadata_to_standard_form(metadata)

    def from_query(self, query):
        tracks = self.search(query)["tracks"]["items"]
        if not tracks:
            raise SpotifyMetadataNotFoundError(
                'Spotify returned no tracks for the search query "{}".'.format(
                    query,
                )
            )
        return self.metadata_to_standard_form(tracks[0])

    def search(self, query):
        return self.spotify.search(query)

    def _generate_token(self, client_id, client_secret):
        """ Generate the token. """
        credentials = oauth2.SpotifyClientCredentials(
            client_secret=client_secret,
        )
        token = credentials.get_access_token()
        return token

    def metadata_to_standard_form(self, metadata):
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

