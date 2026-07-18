"""
YouTube module for downloading and searching songs using yt-dlp.
"""

from typing import Any, Dict, List

from yt_dlp import YoutubeDL

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["YouTube"]


class YouTube(AudioProvider):
    """
    YouTube audio provider class using yt-dlp.
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def get_results(
        self, search_term: str, *_args, **_kwargs
    ) -> List[Result]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.

        ### Returns
        - A list of YouTube results, or an empty list if no results are found.
        """
        search_opts: Dict[str, Any] = {
            **self.audio_handler.params,
            "skip_download": True,
        }

        with YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{search_term}", download=False)

        if not info or "entries" not in info:
            return []

        results = []
        for entry in info["entries"]:
            if not entry:
                continue

            video_id = entry.get("id")
            if not video_id:
                continue

            results.append(
                Result(
                    source=self.name,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    verified=False,
                    name=entry.get("title", ""),
                    duration=entry.get("duration") or 0,
                    author=entry.get("uploader") or "",
                    search_query=search_term,
                    views=entry.get("view_count") or 0,
                    result_id=video_id,
                )
            )

        return results
