"""
BandCamp module for downloading and searching songs.
"""

import logging
from typing import Any, Dict, List

import bandcamp_api.track as BandCampTrack
from bandcamp_api.search import SearchResultsItemTrack, search

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["BandCamp"]

logger = logging.getLogger(__name__)

# Disable logging from bandcamp_api
BandCampTrack.logging.debug = lambda *_: None


class BandCamp(AudioProvider):
    """
    SoundCloud audio provider class
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SoundCloud API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)

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

        try:
            results = search(search_term)
        except KeyError:
            return []
        except Exception as exc:
            logger.error("Failed to get results from BandCamp", exc_info=exc)
            return []

        simplified_results: List[Result] = []
        for result in results:
            if not isinstance(result, SearchResultsItemTrack):
                continue

            track = BandCampTrack.Track(result.artist_id, result.track_id)

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
