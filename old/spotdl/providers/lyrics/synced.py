"""
Synced lyrics provider using the syncedlyrics library
"""

from typing import Dict, List, Optional

import requests
import syncedlyrics

from spotdl.providers.lyrics.base import LyricsProvider

__all__ = ["Synced"]


class Synced(LyricsProvider):
    """
    Lyrics provider for synced lyrics using the syncedlyrics library
    Currently supported websites: Deezer, NetEase
    """

    def get_results(self, name: str, artists: List[str], **kwargs) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """

        raise NotImplementedError

    def extract_lyrics(self, url: str, **kwargs) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        raise NotImplementedError

    def get_lyrics(self, name: str, artists: List[str], **kwargs) -> Optional[str]:
        """
        Try to get lyrics using syncedlyrics

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        try:
            lyrics = syncedlyrics.search(
                f"{name} - {artists[0]}",
                synced_only=not kwargs.get("allow_plain_format", True),
            )
            return lyrics
        except requests.exceptions.SSLError:
            # Max retries reached
            return None
        except TypeError:
            # Error at syncedlyrics.providers.musixmatch L89 -
            #   Because `body` is occasionally an empty list instead of a dictionary.
            # We get this error when allow_plain_format is set to True,
            #   and there are no synced lyrics present
            # Because its empty, we know there are no lyrics
            return None
