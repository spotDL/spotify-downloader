import requests
import json
import logging

from typing import Any, Dict, List, Optional

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["slider.kz"]
logger = logging.getLogger(__name__)


class SliderKZ(AudioProvider):
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

        search_results = ""
        max_retries = 0
        results = []

        while max_retries < 3:
            try:
                search_results = requests.get(
                    url="https://slider.kz/vk_auth.php?q=" + search_term,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"
                    },
                    timeout=5,
                )

                if (
                    len(search_results.text) < 30
                ):  # sometimes slider.kz returns an empty string
                    max_retries += 1
                    raise Exception("Undefinied error on slider.kz. retrying...")

                search_results = json.loads(search_results.text)
                break
            except Exception as e:
                logger.error(f"Falied to get results from slider.kz: {e}, retrying...")
                max_retries += 1
        else:
            logger.error("Failed to get results from slider.kz, giving up.")
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

        except Exception as e:
            logger.error("Failed to parse JSON from slider.kz")

        return results
