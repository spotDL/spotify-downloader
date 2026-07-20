"""
BandCamp module for downloading and searching songs.
"""

import logging
from collections.abc import Mapping
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.exceptions import JSONDecodeError

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result
from spotdl.utils.config import GlobalConfig

__all__ = ["BandCamp"]

logger = logging.getLogger(__name__)


class BandCampTrack:
    """
    BandCamp track class based on the bandcamp_api library
    """

    def __init__(self, artist_id: int, track_id: int):
        # object info
        self.type = "track"

        # track information
        self.track_id: int = 0
        self.track_title: str = ""
        self.track_number: int = 0
        self.track_duration_seconds: float = 0.00
        self.track_streamable: Optional[bool] = None
        self.has_lyrics: Optional[bool] = None
        self.lyrics: str = ""
        self.is_price_set: Optional[bool] = None
        self.price: dict = {}
        self.require_email: Optional[bool] = None
        self.is_purchasable: Optional[bool] = None
        self.is_free: Optional[bool] = None
        self.is_preorder: Optional[bool] = None
        self.tags: list = []
        self.track_url: str = ""

        # art
        self.art_id: int = 0
        self.art_url: str = ""

        # artist information
        self.artist_id: int = 0
        self.artist_title: str = ""

        # album information
        self.album_id: int = 0
        self.album_title: str = ""

        # label
        self.label_id: int = 0
        self.label_title: str = ""

        # about
        self.about: str = ""
        self.credits: str = ""
        self.date_released_unix: int = 0

        # advanced
        self.date_last_modified_unix: int = 0
        self.date_published_unix: int = 0
        self.supporters: list = []

        response = requests.get(
            url="https://bandcamp.com/api/mobile/25/tralbum_details?band_id="
            + str(artist_id)
            + "&tralbum_id="
            + str(track_id)
            + "&tralbum_type=t",
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        result = response.json()
        self.track_id = result["id"]
        self.track_title = result["title"]
        self.track_number = result["tracks"][0]["track_num"]
        self.track_duration_seconds = result["tracks"][0]["duration"]
        self.track_streamable = result["tracks"][0]["is_streamable"]
        self.has_lyrics = result["tracks"][0]["has_lyrics"]

        # getting lyrics, if there is any
        if self.has_lyrics is True:
            try:
                resp = requests.get(
                    "https://bandcamp.com/api/mobile/25/tralbum_lyrics?tralbum_id="
                    + str(self.track_id)
                    + "&tralbum_type=t",
                    timeout=10,
                    proxies=GlobalConfig.get_parameter("proxies"),
                )
                rjson = resp.json()
                lyrics = rjson["lyrics"]
                if isinstance(lyrics, Mapping):
                    self.lyrics = lyrics.get(str(self.track_id)) or ""
            except (
                requests.RequestException,
                JSONDecodeError,
                KeyError,
                TypeError,
            ) as exc:
                logger.debug(
                    "Failed to get lyrics for BandCamp track %s: %s",
                    self.track_id,
                    exc,
                )
                self.lyrics = ""

        self.is_price_set = result.get("is_set_price")
        self.price = {
            "currency": result.get("currency"),
            "amount": result.get("price"),
        }
        self.require_email = result.get("require_email")
        self.is_purchasable = result.get("is_purchasable")
        self.is_free = result.get("free_download")
        self.is_preorder = result.get("is_preorder")

        tags = result.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, Mapping) and "name" in tag:
                    self.tags.append(tag["name"])

        self.art_id = result.get("art_id") or 0
        self.art_url = "https://f4.bcbits.com/img/a" + str(self.art_id) + "_0.jpg"

        self.artist_id = result["band"]["band_id"]
        self.artist_title = result["band"]["name"]

        self.album_id = result["album_id"]
        self.album_title = result["album_title"]

        self.label_id = result.get("label_id") or 0
        self.label_title = result.get("label") or ""

        self.about = result.get("about") or ""
        self.credits = result.get("credits") or ""

        self.date_released_unix = result.get("release_date") or 0

        self.track_url = result["bandcamp_url"]


def search(search_string: str = ""):
    """
    I got this api url from the iOS app
    needs a way of removing characters
    that will screw up an url
    keep url safe characters

    ### Arguments
    - search_string: The search term to search for.

    ### Returns
    - A list of artist and track ids if found
    """

    try:
        response = requests.get(
            "https://bandcamp.com/api/fuzzysearch/2/app_autocomplete?q="
            + search_string
            + "&param_with_locations=true",
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        results = response.json()["results"]
    except (requests.RequestException, JSONDecodeError, KeyError, TypeError) as exc:
        logger.debug("BandCamp search failed for query %s: %s", search_string, exc)
        return []

    return_results: List[Tuple[str, str]] = []

    for item in results:
        if not isinstance(item, Mapping):
            continue

        if item.get("type") == "t":
            try:
                return_results.append((item["band_id"], item["id"]))
            except KeyError:
                continue

    return return_results


class BandCamp(AudioProvider):
    """
    SoundCloud audio provider class
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def get_results(self, search_term: str, *_args, **_kwargs) -> List[Result]:
        """
        Get results from BandCamp

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of BandCamp results if found, None otherwise.
        """

        try:
            results = search(search_term)
        except Exception as exc:
            logger.error("Failed to get results from BandCamp", exc_info=exc)
            return []

        simplified_results: List[Result] = []
        for result in results:
            try:
                track = BandCampTrack(int(result[0]), int(result[1]))
            except (
                requests.RequestException,
                JSONDecodeError,
                KeyError,
                IndexError,
                TypeError,
                ValueError,
            ) as exc:
                logger.debug("Failed to get BandCamp track %s: %s", result, exc)
                continue

            if not all(
                isinstance(value, str)
                for value in (track.track_url, track.track_title, track.artist_title)
            ):
                continue

            if not isinstance(track.track_duration_seconds, (int, float)):
                continue

            simplified_results.append(
                Result(
                    source="bandcamp",
                    url=track.track_url,
                    verified=False,
                    name=track.track_title,
                    duration=track.track_duration_seconds,
                    author=track.artist_title,
                    result_id=track.track_url,
                    search_query=search_term,
                    album=track.album_title,
                    artists=tuple(track.artist_title.split(", ")),
                )
            )

        return simplified_results
