"""
Base module for all other lyrics providers.
"""

from typing import List, Optional


class LyricsProvider:
    """
    Base class for all other lyrics providers.
    """

    def __init__(self):
        """
        Init the lyrics provider searchand set headers.
        """

        self.headers = {
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
            "Accept": "*/*",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "en-US;q=0.8,en;q=0.7",
        }

    def get_lyrics(self, name: str, artists: List[str], **kwargs) -> Optional[str]:
        """
        Returns the lyrics for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        raise NotImplementedError

    @property
    def name(self) -> str:
        """
        Returns the name of the lyrics provider.
        """

        return self.__class__.__name__
