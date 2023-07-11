"""
Piped module for downloading and searching songs.
"""


import logging
import shlex
from typing import Any, Dict, List, Optional

import requests
from yt_dlp import YoutubeDL

from spotdl.providers.audio.base import ISRC_REGEX, AudioProvider, YTDLLogger
from spotdl.types.result import Result
from spotdl.utils.config import get_temp_path
from spotdl.utils.formatter import args_to_ytdlp_options

__all__ = ["Piped"]
logger = logging.getLogger(__name__)

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

    def __init__(  # pylint: disable=super-init-not-called
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

        self.output_format = output_format
        self.cookie_file = cookie_file
        self.search_query = search_query
        self.filter_results = filter_results

        if self.output_format == "m4a":
            ytdl_format = "best[ext=m4a]/best"
        elif self.output_format == "opus":
            ytdl_format = "best[ext=webm]/best"
        else:
            ytdl_format = "best"

        yt_dlp_options = {
            "format": ytdl_format,
            "quiet": True,
            "no_warnings": True,
            "encoding": "UTF-8",
            "logger": YTDLLogger(),
            "cookiefile": self.cookie_file,
            "outtmpl": f"{get_temp_path()}/%(id)s.%(ext)s",
            "retries": 5,
        }

        if yt_dlp_args:
            user_options = args_to_ytdlp_options(shlex.split(yt_dlp_args))
            yt_dlp_options.update(user_options)

        self.audio_handler = YoutubeDL(yt_dlp_options)
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

    def get_download_metadata(self, url: str, download: bool = False) -> Dict:
        """
        Get metadata for a download using yt-dlp.

        ### Arguments
        - url: The url to get metadata for.

        ### Returns
        - A dictionary containing the metadata.
        """

        url_id = url.split("?v=")[1]
        piped_data = requests.get(
            f"https://pipedapi.kavin.rocks/streams/{url_id}", timeout=10
        ).json()

        yt_dlp_json = {
            "title": piped_data["title"],
            "id": url_id,
            "view_count": piped_data["views"],
            "extractor": "Generic",
            "formats": [],
        }

        for audio_stream in piped_data["audioStreams"]:
            yt_dlp_json["formats"].append(
                {
                    "url": audio_stream["url"],
                    "ext": "webm" if audio_stream["codec"] == "opus" else "m4a",
                    "abr": audio_stream["quality"].split(" ")[0],
                    "filesize": audio_stream["contentLength"],
                }
            )

        return self.audio_handler.process_video_result(yt_dlp_json, download=download)
