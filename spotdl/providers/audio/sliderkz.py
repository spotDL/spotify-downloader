from typing import Any, Dict, List

import logging  # pylint: disable=C0114
import json
import requests


from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["SliderKZ"]
logger = logging.getLogger(__name__)


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

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"
        }
        search_results = ""
        max_retries = 0
        results = []

        while max_retries < 3:
            try:
                search_results = requests.get(
                    url="https://slider.kz/vk_auth.php?q=" + search_term,
                    headers=headers,
                    timeout=5,
                )

                if (
                    len(search_results.text) < 30
                ):  # sometimes slider.kz returns an empty string
                    max_retries += 1
                    raise ConnectionError

                search_results = json.loads(search_results.text)
                break
            except ConnectionError:
                max_retries += 1
        else:
            logger.error("Failed to get results from slider.kz")
            return search_results

        try:
            for result in search_results["audios"][""]:
                # urls from slider.kz sometimes are relative, so we need to add the domain
                if "https://" not in result["url"]:
                    result["url"] = "https://slider.kz/" + result["url"]

                results.append(
                    Result(
                        source="slider",
                        url=result["url"],
                        verified=False,
                        name=result["tit_art"],
                        duration=int(result["duration"]) * 1000,
                        author="slider.kz",
                        result_id=result["id"],
                        views=1,
                    )
                )

        except Exception:
            logger.error("Failed to parse JSON from slider.kz")

        return results
