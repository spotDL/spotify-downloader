"""
Youtube module for downloading and searching songs.
"""

from typing import Any, Dict, List, Optional

from pytube import YouTube as PyTube, Search
from rapidfuzz import fuzz
from slugify import slugify

from spotdl.utils.formatter import create_song_title, create_search_query
from spotdl.providers.audio.base import AudioProvider
from spotdl.types import Song


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

                    if isrc_result and isrc_result.watch_url is not None:
                        return isrc_result.watch_url

            search_query = create_song_title(song.name, song.artists).lower()

        # Query YTM by songs only first, this way if we get correct result on the first try
        # we don't have to make another request to ytmusic api that could result in us
        # getting rate limited sooner
        results = self.get_results(search_query)

        if results is None:
            return None

        if self.filter_results:
            ordered_results = {results[0].watch_url: 100}
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
    ) -> Optional[List[PyTube]]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of YouTube results if found, None otherwise.
        """

        return Search(search_term).results

    def order_results(self, results: List[PyTube], song: Song) -> Dict[str, Any]:
        """
        Filter results based on the song's metadata.

        ### Arguments
        - results: The results to order.
        - song: The song to order for.

        ### Returns
        - The ordered results.
        """

        # Assign an overall avg match value to each result
        links_with_match_value = {}

        # Slugify song title
        slug_song_name = slugify(song.name)
        slug_song_title = slugify(
            create_song_title(song.name, song.artists)
            if not self.search_query
            else create_search_query(song, self.search_query, False, None, True)
        )

        for result in results:
            # Skip results without id
            if result.video_id is None:
                continue

            # Slugify some variables
            slug_result_name = slugify(result.title)
            sentence_words = slug_song_name.replace("-", " ").split(" ")

            # Check for common words in result name
            common_word = any(
                word != "" and word in slug_result_name for word in sentence_words
            )

            # skip results that have no common words in their name
            if not common_word:
                continue

            # Find artist match
            artist_match_number = 0.0

            # Calculate artist match for each artist
            # in the song's artist list
            for artist in song.artists:
                artist_match_number += fuzz.partial_token_sort_ratio(
                    slugify(artist), slug_result_name
                )

            # skip results with artist match lower than 70%
            artist_match = artist_match_number / len(song.artists)
            if artist_match < 70:
                continue

            # Calculate name match
            name_match = fuzz.partial_token_sort_ratio(
                slug_result_name, slug_song_title
            )

            # Drop results with name match lower than 50%
            if name_match < 50:
                continue

            # Calculate time match
            time_match = (
                100 - (result.length - song.duration**2) / song.duration * 100
            )

            average_match = (artist_match + name_match + time_match) / 3

            # the results along with the avg Match
            links_with_match_value[result.watch_url] = average_match

        return links_with_match_value
