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

        search_results = requests.get("https://slider.kz/vk_auth.php?q=" + search_term)
        search_results = json.loads(search_results.text)

        results = []
        for result in search_results["audios"][""]:

            results.append(
                Result(
                    source="slider",
                    url=result["url"],
                    verified=False,
                    name=result["tit_art"],
                    duration=result["duration"],
                    author="slider.kz",
                    result_id=result["id"],
                    views=1,
                )
            )

        return results