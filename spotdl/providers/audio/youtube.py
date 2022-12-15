"""
Youtube module for downloading and searching songs.
"""

from typing import Any, Dict, List, Optional

from pytube import YouTube as PyTube, Search

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result


class YouTube(AudioProvider):
    """
    YouTube audio provider class
    """

    SUPPORTS_ISRC = True
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

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
                results.append(
                    Result(
                        source=self.name,
                        url=result.watch_url,
                        verified=False,
                        name=result.title,
                        duration=result.length,
                        author=result.author,
                        search_query=search_term,
                        views=result.views,
                    )
                )

        return results
