"""
Youtube module for downloading and searching songs.
"""

# import yt_dlp
import logging
from typing import Any, Dict, List, Optional

from pytube import Search
from pytube import YouTube as PyTube
from pytube import innertube

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

logger = logging.getLogger("spotdl")


def get_best_audio_format(video_url: str, cookies_path: Optional[str] = None) -> str:
    """
    Returns the best audio format string for yt_dlp based on Premium availability.
    If Premium formats (high-quality opus) are found, they are prioritized.
    """
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
    }

    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            formats = info.get("formats", [])

            # Look for premium-level audio (opus codec ≥160kbps)
            premium_formats = [
                f
                for f in formats
                if f.get("acodec") == "opus" and f.get("abr", 0) >= 160
            ]

            if premium_formats:
                best = max(premium_formats, key=lambda f: f.get("abr", 0))
                logger.info(
                    f"YouTube Premium detected — downloading high-quality audio ({best.get('abr')}kbps)."
                )
                return f"{best['format_id']}/bestaudio/best"

            # Fallback to normal formats
            logger.info("Regular YouTube account — downloading standard audio.")
            return "bestaudio/best"

    except Exception as e:
        logger.debug(f"Premium format detection failed for {video_url}: {e}")
        return "bestaudio/best"


__all__ = ["YouTube"]


class YouTube(AudioProvider):
    """
    YouTube audio provider class
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the YouTube audio provider
        """
        super().__init__(*args, **kwargs)

        # Set the client version to a specific version to avoid issues with pytube
        # See #2323 or https://github.com/pytube/pytube/issues/296
        innertube._default_clients["WEB"]["context"]["client"][
            "clientVersion"
        ] = "2.20230427.04.00"

    def get_results(
        self, search_term: str, *_args, **_kwargs
    ) -> List[Result]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of YouTube results if found, None otherwise.
        """

        search_results: Optional[List[PyTube]] = Search(search_term).results

        if not search_results:
            return []

        results = []
        for result in search_results:
            if result.watch_url:
                try:
                    duration = result.length
                except Exception:
                    duration = 0

                try:
                    views = result.views
                except Exception:
                    views = 0

                # Dynamically choose best format
                format_string = get_best_audio_format(
                    result.watch_url, getattr(self, "cookie_file", None)
                )

                results.append(
                    Result(
                        source=self.name,
                        url=result.watch_url,
                        verified=False,
                        name=result.title,
                        duration=duration,
                        author=result.author,
                        search_query=search_term,
                        views=views,
                        result_id=result.video_id,
                        additional_info={"format_string": format_string},
                    )
                )

        return results
