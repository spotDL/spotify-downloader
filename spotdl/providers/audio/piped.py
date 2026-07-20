"""
Piped module for downloading and searching songs.
"""

import logging
from collections.abc import Mapping
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from requests.exceptions import JSONDecodeError

from spotdl.providers.audio.base import ISRC_REGEX, AudioProvider
from spotdl.types.result import Result
from spotdl.utils.config import GlobalConfig

__all__ = ["Piped"]
logger = logging.getLogger(__name__)

HEADERS = {
    "accept": "*/*",
}
API_BASE_URL = "https://api.piped.private.coffee"


def _legacy_piped_watch_url_to_youtube(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname not in {"piped.video", "www.piped.video"}:
        return url

    if parsed_url.path != "/watch":
        return url

    video_ids = parse_qs(parsed_url.query).get("v")
    if not video_ids:
        return url

    return f"https://www.youtube.com/watch?v={video_ids[0]}"


class Piped(AudioProvider):
    """
    YouTube Music audio provider class
    """

    SUPPORTS_ISRC = True
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [
        {"filter": "music_songs"},
        {"filter": "music_videos"},
    ]

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        output_format: str = "mp3",
        cookie_file: Optional[str] = None,
        search_query: Optional[str] = None,
        filter_results: bool = True,
        yt_dlp_args: Optional[str] = None,
    ) -> None:
        """
        Pipe audio provider class

        ### Arguments
        - output_directory: The directory to save the downloaded songs to.
        - output_format: The format to save the downloaded songs in.
        - cookie_file: The path to a file containing cookies to be used by YTDL.
        - search_query: The query to use when searching for songs.
        - filter_results: Whether to filter results.
        """

        super().__init__(
            output_format=output_format,
            cookie_file=cookie_file,
            search_query=search_query,
            filter_results=filter_results,
            yt_dlp_args=yt_dlp_args,
        )
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

        isrc_result = ISRC_REGEX.search(search_term)

        params = {"q": search_term, **kwargs}
        if params.get("filter") is None:
            params["filter"] = "music_songs" if isrc_result else "music_videos"

        try:
            response = self.session.get(
                f"{API_BASE_URL}/search",
                params=params,
                headers=HEADERS,
                proxies=GlobalConfig.get_parameter("proxies"),
                timeout=20,
            )
        except requests.RequestException as exc:
            logger.debug("Piped search failed for query %s: %s", search_term, exc)
            return []

        if response.status_code != 200:
            logger.debug(
                "Piped search for query %s returned status code %s",
                search_term,
                response.status_code,
            )
            return []

        try:
            search_results = response.json()
        except JSONDecodeError:
            logger.debug("Piped search for query %s returned invalid JSON", search_term)
            return []

        if not isinstance(search_results, Mapping):
            logger.debug(
                "Piped search for query %s returned a malformed response", search_term
            )
            return []

        items = search_results.get("items", [])
        if not isinstance(items, list):
            logger.debug(
                "Piped search for query %s returned a malformed response", search_term
            )
            return []

        results = []
        for result in items:
            if not isinstance(result, Mapping):
                continue

            if result.get("type") != "stream":
                continue

            try:
                result_url = result["url"]
                title = result["title"]
                duration = result["duration"]
                uploader_name = result["uploaderName"]
            except KeyError:
                continue

            if not all(
                isinstance(value, str) for value in (result_url, title, uploader_name)
            ):
                continue

            if not isinstance(duration, (int, float)):
                continue

            result_id = parse_qs(urlparse(result_url).query).get("v")
            if result_id is None:
                continue

            views = result.get("views")
            if views is not None:
                try:
                    views = int(views)
                except (TypeError, ValueError):
                    views = None

            results.append(
                Result(
                    source="piped",
                    url=f"https://www.youtube.com/watch?v={result_id[0]}",
                    verified=params["filter"] == "music_songs",
                    name=title,
                    duration=duration,
                    author=uploader_name,
                    result_id=result_id[0],
                    artists=(
                        (uploader_name,) if params["filter"] == "music_songs" else None
                    ),
                    isrc_search=isrc_result is not None,
                    search_query=search_term,
                    views=views,
                )
            )

        return results

    def get_download_metadata(self, url: str, download: bool = False) -> Dict:
        """
        Get metadata for a download using yt-dlp.

        ### Arguments
        - url: The url to get metadata for.

        ### Returns
        - A dictionary containing the metadata.
        """

        proxies = GlobalConfig.get_parameter("proxies")
        if proxies:
            proxy = proxies.get("https") or proxies.get("http")
            if proxy:
                self.audio_handler.params["proxy"] = proxy

        return super().get_download_metadata(
            _legacy_piped_watch_url_to_youtube(url), download
        )
