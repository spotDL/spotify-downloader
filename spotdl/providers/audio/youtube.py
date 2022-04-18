"""
Youtube module for downloading and searching songs.
"""

from typing import List, Optional

from pytube import Search

from spotdl.utils.formatter import create_song_title, create_search_query
from spotdl.providers.audio.base import AudioProvider
from spotdl.types import Song
from spotdl.types.search_result import SearchResult


class YouTube(AudioProvider):
    """
    YouTube audio provider class
    """

    def search(self, song: Song) -> Optional[str]:
        """
        Search for a video on YouTube.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - The url of the best match or None if no match was found.
        """

        if self.search_query:
            search_query = create_search_query(
                song, self.search_query, False, None, True
            )
        else:
            # if isrc is not None then we try to find song with it
            if song.isrc:
                isrc_results = self.get_results(song.isrc)

                if isrc_results and len(isrc_results) == 1:
                    isrc_result = isrc_results[0]

                    if isrc_result and isrc_result.link is not None:
                        return isrc_result.link

            search_query = create_song_title(song.name, song.artists).lower()

        # Query YTM by songs only first, this way if we get correct result on the first try
        # we don't have to make another request to ytmusic api that could result in us
        # getting rate limited sooner
        results = self.get_results(search_query)

        if results is None:
            return None

        if self.filter_results:
            ordered_results = {results[0].link: 100}
        else:
            # Order results
            ordered_results = self.order_results(results, song)

        # No matches found
        if len(ordered_results) == 0:
            return None

        result_items = list(ordered_results.items())

        # Sort results by highest score
        sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

        # Return the first result
        return sorted_results[0][0]

    @staticmethod
    def get_results(
        search_term: str, *_args, **_kwargs
    ) -> List[SearchResult]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of YouTube results if found, None otherwise.
        """

        return [
            SearchResult(
                name=result.title,
                link=result.watch_url,
                duration=result.length,
                provider="youtube",
                artists=None,
                album=None,
                owner=result.author,
            )
            for result in Search(search_term).results
        ]
