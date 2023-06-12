"""
Piped module for downloading and searching songs.
"""


from typing import Any, Dict, List

import requests

from spotdl.providers.audio.base import ISRC_REGEX, AudioProvider
from spotdl.types.result import Result

__all__ = ["Piped"]

HEADERS = {
    "accept": "*/*",
}


class Piped(AudioProvider):
    """
    YouTube Music audio provider class
    """

    SUPPORTS_ISRC = True
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [
        {"filter": "music_songs"},
        {"filter": "music_videos"},
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the YouTube Music API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)

        self.session = requests.Session()

    def get_results(self, search_term: str, **kwargs) -> List[Result]:
        """
        Get results from YouTube Music API and simplify them

        ### Arguments
        - search_term: The search term to search for.
        - kwargs: other keyword arguments passed to the `YTMusic.search` method.

        ### Returns
        - A list of simplified results (dicts)
        """

        if kwargs is None:
            kwargs = {}

        params = {"q": search_term, **kwargs}

        response = self.session.get(
            "https://pipedapi.kavin.rocks/search",
            params=params,
            headers=HEADERS,
            timeout=20,
        )

        search_results = response.json()

        # Simplify results
        results = []
        for result in search_results["items"]:
            isrc_result = ISRC_REGEX.search(search_term)

            results.append(
                Result(
                    source="piped",
                    url=f"https://piped.video{result['url']}",
                    verified=kwargs.get("filter") == "music_songs",
                    name=result["title"],
                    duration=result["duration"],
                    author=result["uploaderName"],
                    result_id=result["url"].split("?v=")[1],
                    artists=(result["uploaderName"],)
                    if kwargs.get("filter") == "music_songs"
                    else None,
                    isrc_search=isrc_result is not None,
                    search_query=search_term,
                )
            )

        return results
