"""
SoundCloud module for downloading and searching songs.
"""

import logging
import re
from itertools import islice
from typing import Any, Dict, List

from soundcloud import SoundCloud as SoundCloudClient
from soundcloud.resource.track import Track

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["SoundCloud"]

logger = logging.getLogger(__name__)


class SoundCloud(AudioProvider):
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
        self.client = SoundCloudClient()

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

        results = list(islice(self.client.search(search_term), 20))
        regex = r"^(.+?)-|(\(\w+[\s\S]*\))"
        # Because anyone can post on soundcloud, we do another search with an edited search
        # The regex removes anything in brackets and the artist(s)'s name(s) if in the name
        edited_search_term = re.sub(regex, "", search_term)
        results.extend(list(islice(self.client.search(edited_search_term), 20)))

        # Simplify results
        simplified_results = []
        for result in results:
            if not isinstance(result, Track):
                continue

            # Ignore results that are not playable
            if "/preview/" in result.media.transcodings[0].url:
                continue

            album = self.client.get_track_albums(result.id)

            try:
                album_name = next(album).title
            except StopIteration:
                album_name = None

            simplified_results.append(
                Result(
                    source="soundcloud",
                    url=result.permalink_url,
                    name=result.title,
                    verified=result.user.verified,
                    duration=result.full_duration,
                    author=result.user.username,
                    result_id=str(result.id),
                    isrc_search=False,
                    search_query=search_term,
                    views=result.playback_count,
                    explicit=False,
                    album=album_name,
                )
            )

        return simplified_results
