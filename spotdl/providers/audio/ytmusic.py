"""
YTMusic module for downloading and searching songs.
"""

from typing import Any, List, Optional

from ytmusicapi import YTMusic

from spotdl.providers.audio.base import AudioProvider, AudioProviderError
from spotdl.types import Song
from spotdl.types.search_result import SearchResult
from spotdl.utils.formatter import (
    create_song_title,
    parse_duration,
    create_search_query,
)


class YouTubeMusic(AudioProvider):
    """
    YouTube Music audio provider class
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the YouTube Music API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)
        self.client = YTMusic()

        # Check if we are getting results from YouTube Music
        test_results = self.get_results("a")
        if len(test_results) == 0:
            raise AudioProviderError(
                "Could not connect to YouTube Music API. Use VPN or other audio provider."
            )

    def search(self, song: Song) -> Optional[str]:
        """
        Search for a song on YouTube Music.

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
            # search for song using isrc if it's available
            if song.isrc:
                isrc_results = self.get_results(song.isrc, filter="songs")

                if len(isrc_results) == 1:
                    isrc_result = isrc_results[0]

                    name_match = isrc_result.name.lower() == song.name.lower()

                    delta = isrc_result.duration - song.duration
                    non_match_value = (delta**2) / song.duration * 100

                    time_match = 100 - non_match_value

                    if (
                        isrc_result
                        and isrc_result.link
                        and name_match > 90
                        and time_match > 90
                    ):
                        return isrc_result.link

            search_query = create_song_title(song.name, song.artists).lower()

        # Query YTM by songs only first, this way if we get correct result on the first try
        # we don't have to make another request
        song_results = self.get_results(search_query, filter="songs")

        if self.filter_results:
            # Order results
            songs = self.order_results(song_results, song)
        else:
            songs = {}
            if len(song_results) > 0:
                songs = {song_results[0].link: 100}

        # song type results are always more accurate than video type,
        # so if we get score of 80 or above
        # we are almost 100% sure that this is the correct link
        if len(songs) != 0:
            # get the result with highest score
            best_result = max(songs, key=lambda k: songs[k])

            if songs[best_result] >= 80:
                return best_result

        # We didn't find the correct song on the first try so now we get video type results
        # add them to song_results, and get the result with highest score
        video_results = self.get_results(search_query, filter="videos")

        if self.filter_results:
            # Order video results
            videos = self.order_results(video_results, song)
        else:
            videos = {}
            if len(video_results) > 0:
                videos = {video_results[0].link: 100}

        # Merge songs and video results
        results = {**songs, **videos}

        # No matches found
        if not results:
            return None

        result_items = list(results.items())

        # Sort results by highest score
        sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

        # Get the result with highest score
        # and return the link
        return sorted_results[0][0]

    def get_results(self, search_term: str, **kwargs) -> List[SearchResult]:
        """
        Get results from YouTube Music API and simplify them

        ### Arguments
        - search_term: The search term to search for.
        - kwargs: other keyword arguments passed to the `YTMusic.search` method.

        ### Returns
        - A list of simplified results (dicts)
        """

        results = self.client.search(search_term, **kwargs)

        # Simplify results
        simplified_results = []
        for result in results:
            if result.get("videoId") is None:
                continue

            simplified_results.append(
                SearchResult(
                    name=result["title"],
                    link=f"https://youtube.com/watch?v={result['videoId']}",
                    duration=parse_duration(result.get("duration")),
                    artists=", ".join(map(lambda a: a["name"], result["artists"])),
                    album=result.get("album", {}).get("name"),
                    provider="ytmusic",
                    owner=None,
                )
            )

        return simplified_results
