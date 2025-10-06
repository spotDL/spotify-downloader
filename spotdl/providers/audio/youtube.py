"""
YouTube module for downloading and searching songs using yt-dlp.
"""

from typing import Any, Dict, List, Optional
from yt_dlp import YoutubeDL

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["YouTube"]


class YouTube(AudioProvider):
    """
    YouTube audio provider class using yt-dlp
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the YouTube audio provider
        """
        super().__init__(*args, **kwargs)

        # yt-dlp options
        self.ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",  # only get metadata, not full video
        }

    def get_results(
        self, search_term: str, *_args, **_kwargs
    ) -> List[Result]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.

        ### Returns
        - A list of YouTube results if found, None otherwise.
        """
        results = []

        with YoutubeDL(self.ydl_opts) as ydl:
            # Search for videos — ytsearch5 limits to top 5 results
            search_query = f"ytsearch5:{search_term}"
            try:
                info = ydl.extract_info(search_query, download=False)
            except Exception:
                return []

        if not info or "entries" not in info:
            return []

        for entry in info["entries"]:
            if not entry:
                continue

            results.append(
                Result(
                    source=self.name,
                    url=f"https://www.youtube.com/watch?v={entry.get('id')}",
                    verified=False,
                    name=entry.get("title", ""),
                    duration=entry.get("duration", 0),
                    author=entry.get("uploader", ""),
                    search_query=search_term,
                    views=entry.get("view_count", 0),
                    result_id=entry.get("id", ""),
                )
            )

        return results
