"""
YTMusic module for downloading and searching songs.
"""

from typing import Any, Dict, List

from ytmusicapi import YTMusic

from spotdl.providers.audio.base import ISRC_REGEX, AudioProvider
from spotdl.types.result import Result
from spotdl.utils.formatter import parse_duration

__all__ = ["YouTubeMusic"]


class YouTubeMusic(AudioProvider):
    """
    YouTube Music audio provider class
    """

    SUPPORTS_ISRC = True
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [
        {"filter": "songs", "ignore_spelling": True, "limit": 50},
        {"filter": "videos", "ignore_spelling": True, "limit": 50},
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the YouTube Music API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)

        self.client = YTMusic(language="de")

    def get_results(self, search_term: str, **kwargs) -> List[Result]:
        """
        Get results from YouTube Music API and simplify them

        ### Arguments
        - search_term: The search term to search for.
        - kwargs: other keyword arguments passed to the `YTMusic.search` method.

        ### Returns
        - A list of simplified results (dicts)
        """

        is_isrc_result = ISRC_REGEX.search(search_term) is not None
        # if is_isrc_result:
        #     print("FORCEFULLY SETTING FILTER TO SONGS")
        #     kwargs["filter"] = "songs"

        search_results = self.client.search(search_term, **kwargs)

        # Simplify results
        results = []
        for result in search_results:
            if (
                result is None
                or result.get("videoId") is None
                or result.get("artists") in [[], None]
            ):
                continue

            results.append(
                Result(
                    source=self.name,
                    url=(
                        f'https://{"music" if result["resultType"] == "song" else "www"}'
                        f".youtube.com/watch?v={result['videoId']}"
                    ),
                    verified=result.get("resultType") == "song",
                    name=result["title"],
                    result_id=result["videoId"],
                    author=result["artists"][0]["name"],
                    artists=tuple(map(lambda a: a["name"], result["artists"])),
                    duration=parse_duration(result.get("duration")),
                    isrc_search=is_isrc_result,
                    search_query=search_term,
                    explicit=result.get("isExplicit"),
                    album=(
                        result.get("album", {}).get("name")
                        if result.get("album")
                        else None
                    ),
                )
            )

        return results
