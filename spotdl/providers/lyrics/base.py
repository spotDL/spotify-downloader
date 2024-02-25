"""
Base module for all other lyrics providers.
"""

import logging
from typing import Dict, List, Optional

from spotdl.utils.formatter import ratio, slugify
from spotdl.utils.matching import based_sort

__all__ = ["LyricsProvider"]
logger = logging.getLogger(__name__)


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
            "sec-ch-ua": '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "en-US;q=0.8,en;q=0.7",
        }

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
        Returns the lyrics for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """
        try:
            results = self.get_results(name, artists, **kwargs)
        except Exception as exc:
            logger.debug(
                "%s: Failed to get results for %s - %s: %s",
                self.name,
                name,
                ", ".join(artists),
                exc,
            )
            return None

        if not results:
            return None

        results_with_score = {}
        for title, url in results.items():
            result_title = slugify(title)
            match_title = slugify(f"{name} - {', '.join(artists)}")

            res_list, song_list = based_sort(
                result_title.split("-"), match_title.split("-")
            )
            result_title, match_title = "-".join(res_list), "-".join(song_list)

            score = ratio(result_title, match_title)
            results_with_score[score] = url

        if not results_with_score:
            return None

        # Get song url with highest title match
        score, url = max(results_with_score.items(), key=lambda x: x[0])

        # Only return lyrics if the title match is at least 55%
        if score < 55:
            return None

        try:
            return self.extract_lyrics(url, **kwargs)
        except Exception as exc:
            logger.debug(
                "%s: Failed to extract lyrics from %s: %s", self.name, url, exc
            )
            return None

    @property
    def name(self) -> str:
        """
        Returns the name of the lyrics provider.
        """

        return self.__class__.__name__
