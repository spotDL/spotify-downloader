"""
SliderKZ module for downloading and searching songs.
"""

import logging
from typing import Any, Dict, List

import requests

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["SliderKZ"]

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"
}


class SliderKZ(AudioProvider):
    """
    Slider.kz audio provider class
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def get_results(self, search_term: str, *_args, **_kwargs) -> List[Result]:
        """
        Get results from slider.kz

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of slider.kz results if found, None otherwise.
        """

        search_results = None
        max_retries = 0

        while not search_results and max_retries < 3:
            try:
                search_response = requests.get(
                    url="https://slider.kz/vk_auth.php?q=" + search_term,
                    headers=HEADERS,
                    timeout=5,
                )

                # Check if the response is valid
                if len(search_response.text) > 30:
                    # Set the search results to the json response
                    # effectively breaking out of the loop
                    search_results = search_response.json()

            except Exception as exc:
                logger.debug(
                    "Slider.kz search failed for query %s with error: %s. Retrying...",
                    search_term,
                    exc,
                )

            max_retries += 1

        if not search_results:
            logger.debug("Slider.kz search failed for query %s", search_term)
            return []

        results = []
        for result in search_results["audios"][""]:
            # urls from slider.kz sometimes are relative, so we need to add the domain
            if "https://" not in result["url"]:
                result["url"] = "https://slider.kz/" + result["url"]

            results.append(
                Result(
                    source="slider.kz",
                    url=result.get("url"),
                    verified=False,
                    name=result.get("tit_art"),
                    duration=int(result.get("duration", -9999)),
                    author="slider.kz",
                    result_id=result.get("id"),
                    views=1,
                )
            )

        return results
