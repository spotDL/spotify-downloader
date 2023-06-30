"""
Piped module for downloading and searching songs.
"""


from typing import Any, Dict, List

import logging
import requests

from spotdl.providers.audio.base import ISRC_REGEX, AudioProvider
from spotdl.types.result import Result

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


    def get_download_metadata(self, url: str, download: bool = False) -> Dict:
        """
        Get metadata for a download using yt-dlp.

        ### Arguments
        - url: The url to get metadata for.

        ### Returns
        - A dictionary containing the metadata.
        """

        url_id = url.split("?v=")[1]
        piped_data = requests.get(f"https://pipedapi.kavin.rocks/streams/{url_id}", timeout=10).json()

        yt_dlp_json = {
            "title": piped_data["title"],
            "description": piped_data["description"],
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
                    "format_id": audio_stream["itag"],
                    "acodec": audio_stream["codec"],
                    "container": "webm_dash" if audio_stream["codec"] == "opus" else "m4a_dash",
                    "abr": audio_stream["bitrate"] / 1000,
                    "resolution": "audio only",
                    "aspect_ratio": None,
                    "audio_ext": "webm" if audio_stream["codec"] == "opus" else "m4a",
                    "vbr": 0,
                    "fps": None,
                    "video_ext": None,
                    "protocol": "https",
                    "tbr": audio_stream["bitrate"] / 1000,
                    "asr": 48000 if audio_stream["codec"] == "opus" else 22050,
                    "filesize": audio_stream["contentLength"],
                    "dynamic_range": None,
                    "audio_channels": 2,
                    "format": f"{audio_stream['itag']} - audio only",
                }
            )

        return self.audio_handler.process_video_result(yt_dlp_json, download=download)
