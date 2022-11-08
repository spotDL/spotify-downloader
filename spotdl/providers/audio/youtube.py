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
                    isrc_result = self.order_results(isrc_results, song)
                    if len(isrc_result) == 1:
                        isrc_link, isrc_score = isrc_result.popitem()

                        if isrc_score > 90:
                            # print(f"# RETURN URL - {isrc_link} - isrc score")
                            return isrc_link

                    # print(f"No results for ISRC: {song.isrc}")

            search_query = create_song_title(song.name, song.artists).lower()

        # Query YTM by songs only first, this way if we get correct result on the first try
        # we don't have to make another request to ytmusic api that could result in us
        # getting rate limited sooner
        results = self.get_results(search_query)

        if results is None:
            return None

        if self.filter_results:
            # Order results
            ordered_results = self.order_results(results, song)
        else:
            ordered_results = {results[0].watch_url: 100}

        # No matches found
        if len(ordered_results) == 0:
            return None

        result_items = list(ordered_results.items())

        # Sort results by highest score
        sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

        last_simlar_index = 1
        best_score, _ = sorted_results[0][1]

        # Get few results with score close to the best score
        for index, (_, (score, _)) in enumerate(sorted_results):
            if (best_score - score) > 8:
                last_simlar_index = index
                break

        # Get the best results from the similar results
        best_results = sorted_results[:last_simlar_index]

        # If we have only one result, return it
        if len(best_results) == 1:
            # print(f"# RETURN URL - {sorted_results[0][0]} - sorted, no best results")
            return sorted_results[0][0]

        # print(f"# best results: {best_results}")

        # If we have more than one result,
        # return the one with the highest score
        # and most views
        views_data = [best_result[1][1] for best_result in best_results]

        # print(f"# views_data: {views_data}")

        best_result = best_results[views_data.index(max(views_data))]

        # print(f"# RETURN URL - {best_result[0]} - sorted, best results")
        return best_result[0]

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
        slug_song_main_artist = slugify(song.artist)
        slug_song_artists = slugify(", ".join(song.artists))
        slug_song_title = slugify(
            create_song_title(song.name, song.artists)
            if not self.search_query
            else create_search_query(song, self.search_query, False, None, True)
        )

        # DEBUG CODE
        # print(f"#############################")
        # print(f"slug_song_name: {slug_song_name}")
        # print(f"slug_song_main_artist: {slug_song_main_artist}")
        # print(f"slug_song_title: {slug_song_title}")
        # print(f"slug_song_duration: {song.duration}")
        # print(f"slug_song_artists: {slug_song_artists}")
        # print(f"#############################")

        for result in results:
            # Skip results without id
            if result.video_id is None:
                continue

            # Slugify result title
            slug_result_name = slugify(result.title)
            slug_result_channel = slugify(result.author)

            # check for common words in result name
            sentence_words = slug_song_name.split("-")
            common_word = any(
                word != "" and word in slug_result_name for word in sentence_words
            )

            # print("-----------------------------")
            # print(f"sentence_words: {sentence_words}")
            # print(f"common_word: {common_word}")
            # print(f"result link: {result.watch_url}")
            # print(f"result duration: {result.length}")
            # print(f"slug_result_name: {slug_result_name}")
            # print(f"slug_result_channel: {slug_result_channel}")
            # print("-----------------------------")

            # skip results that have no common words in their name
            if not common_word:
                continue

            # Find artist match
            artist_match = fuzz.ratio(
                f"{slug_song_artists}-{slug_song_name}", slug_result_name
            )

            # print(f"first artist match: {artist_match}")

            if artist_match < 70:
                # Try to use channel name instead
                # with the main artist name
                main_artist_match = fuzz.ratio(
                    slug_song_main_artist, slug_result_channel
                )

                slug_main_artist = slug_song_main_artist.replace("-", "")

                main_artist_match = slug_main_artist in [
                    slug_result_name.replace("-", ""),
                    slug_result_channel.replace("-", ""),
                ]

                # print(f"main_artist_match: {main_artist_match}")

                # If the main artist name is in the channel name
                # we add 30% to the artist match
                if main_artist_match:
                    artist_match += 30
                    # print(f"new artist_match: {artist_match}")

            # skip results with artist match lower than 70%
            if artist_match < 70:
                # print(f"! artist match lower than 70% {artist_match}, skipping")
                continue

            # print(f"final artist_match: {artist_match}")

            # Calculate name match
            test_str1 = slug_result_name
            test_str2 = slug_song_title

            # check if the artist is in the song name
            # but not in the result name
            # if it is, we add the artist to the result name
            for artist in song.artists:
                slug_song_artist = slugify(artist)
                if slug_song_artist in test_str2 and not slug_song_artist in test_str1:
                    test_str1 += f"-{slug_song_artist}"

            # same thing for for song name
            for artist in song.artists:
                slug_result_artist = slugify(artist)
                if (
                    slug_result_artist in test_str1
                    and not slug_result_artist in test_str2
                ):
                    test_str2 += f"-{slug_result_artist}"

            # calculate the name match
            name_match = fuzz.ratio(test_str1, test_str2)

            # Drop results with name match lower than 50%
            if name_match < 50:
                # print("! name_match < 50, skipping")
                continue

            # print(f"name_match: {name_match}")

            # Calculate time match
            time_match = 100 - (
                ((result.length - song.duration) ** 2) / song.duration * 100
            )

            # print(f"time_match: {time_match}")

            # Drop results with time match lower than 50%
            if time_match < 50:
                # print("! time_match < 50, skipping")
                continue

            average_match = (artist_match + name_match + time_match) / 3

            # print(f"average_match: {average_match}")

            # the results along with the avg Match
            links_with_match_value[result.watch_url] = (average_match, result.views)

        return links_with_match_value
