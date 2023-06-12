"""
Base audio provider module.
"""

import logging
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple

from yt_dlp import YoutubeDL

from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.config import get_temp_path
from spotdl.utils.formatter import (
    args_to_ytdlp_options,
    create_search_query,
    create_song_title,
)
from spotdl.utils.matching import get_best_matches, order_results

__all__ = ["AudioProviderError", "AudioProvider", "ISRC_REGEX", "YTDLLogger"]

logger = logging.getLogger(__name__)


class AudioProviderError(Exception):
    """
    Base class for all exceptions related to audio searching/downloading.
    """


class YTDLLogger:
    """
    Custom YT-dlp logger.
    """

    def debug(self, msg):
        """
        YTDL uses this to print debug messages.
        """

        pass  # pylint: disable=W0107

    def warning(self, msg):
        """
        YTDL uses this to print warnings.
        """

        pass  # pylint: disable=W0107

    def error(self, msg):
        """
        YTDL uses this to print errors.
        """

        raise AudioProviderError(msg)


ISRC_REGEX = re.compile(r"^[A-Z]{2}-?\w{3}-?\d{2}-?\d{5}$")


class AudioProvider:
    """
    Base class for all other providers. Provides some common functionality.
    Handles the yt-dlp audio handler.
    """

    SUPPORTS_ISRC: bool
    GET_RESULTS_OPTS: List[Dict[str, Any]]

    def __init__(
        self,
        output_format: str = "mp3",
        cookie_file: Optional[str] = None,
        search_query: Optional[str] = None,
        filter_results: bool = True,
        yt_dlp_args: Optional[str] = None,
    ) -> None:
        """
        Base class for audio providers.

        ### Arguments
        - output_directory: The directory to save the downloaded songs to.
        - output_format: The format to save the downloaded songs in.
        - cookie_file: The path to a file containing cookies to be used by YTDL.
        - search_query: The query to use when searching for songs.
        - filter_results: Whether to filter results.
        """

        self.output_format = output_format
        self.cookie_file = cookie_file
        self.search_query = search_query
        self.filter_results = filter_results

        if self.output_format == "m4a":
            ytdl_format = "bestaudio[ext=m4a]/bestaudio/best"
        elif self.output_format == "opus":
            ytdl_format = "bestaudio[ext=webm]/bestaudio/best"
        else:
            ytdl_format = "bestaudio"

        yt_dlp_options = {
            "format": ytdl_format,
            "quiet": True,
            "no_warnings": True,
            "encoding": "UTF-8",
            "logger": YTDLLogger(),
            "cookiefile": self.cookie_file,
            "outtmpl": f"{get_temp_path()}/%(id)s.%(ext)s",
            "retries": 5,
        }

        if yt_dlp_args:
            user_options = args_to_ytdlp_options(shlex.split(yt_dlp_args))
            yt_dlp_options.update(user_options)

        self.audio_handler = YoutubeDL(yt_dlp_options)

    def get_results(self, search_term: str, **kwargs) -> List[Result]:
        """
        Get results from audio provider.

        ### Arguments
        - search_term: The search term to use.
        - kwargs: Additional arguments.

        ### Returns
        - A list of results.
        """

        raise NotImplementedError

    def get_views(self, url: str) -> int:
        """
        Get the number of views for a video.

        ### Arguments
        - url: The url of the video.

        ### Returns
        - The number of views.
        """

        data = self.get_download_metadata(url)

        return data["view_count"]

    def search(self, song: Song, only_verified: bool = False) -> Optional[str]:
        """
        Search for a song and return best match.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - The url of the best match or None if no match was found.
        """

        # Create initial search query
        search_query = create_song_title(song.name, song.artists).lower()
        if self.search_query:
            search_query = create_search_query(
                song, self.search_query, False, None, True
            )

        logger.debug("[%s] Searching for %s", song.song_id, search_query)

        isrc_urls: List[str] = []

        # search for song using isrc if it's available
        if song.isrc and self.SUPPORTS_ISRC and not self.search_query:
            isrc_results = self.get_results(song.isrc, **self.GET_RESULTS_OPTS[0])

            if only_verified:
                isrc_results = [result for result in isrc_results if result.verified]

            isrc_urls = [result.url for result in isrc_results]
            sorted_isrc_results = order_results(isrc_results, song, self.search_query)
            logger.debug(
                "[%s] Found %s results for ISRC %s",
                song.song_id,
                len(isrc_results),
                song.isrc,
            )

            if len(isrc_results) > 0:
                # get the best result, if the score is above 80 return it
                best_isrc_results = sorted(
                    sorted_isrc_results.items(), key=lambda x: x[1], reverse=True
                )
                logger.debug(
                    "[%s] Filtered to %s ISRC results",
                    song.song_id,
                    len(best_isrc_results),
                )

                if len(best_isrc_results) > 0:
                    best_isrc = best_isrc_results[0]
                    if best_isrc[1] > 80.0:
                        logger.debug(
                            "[%s] Best ISRC result is %s with score %s",
                            song.song_id,
                            best_isrc[0].url,
                            best_isrc[1],
                        )

                        return best_isrc[0].url

        results: Dict[Result, float] = {}
        for options in self.GET_RESULTS_OPTS:
            # Query YTM by songs only first, this way if we get correct result on the first try
            # we don't have to make another request
            search_results = self.get_results(search_query, **options)

            if only_verified:
                search_results = [
                    result for result in search_results if result.verified
                ]

            logger.debug(
                "[%s] Found %s results for search query %s with options %s",
                song.song_id,
                len(search_results),
                search_query,
                options,
            )

            # Check if any of the search results is in the
            # first isrc results, since they are not hashable we have to check
            # by name
            isrc_result = next(
                (result for result in search_results if result.url in isrc_urls),
                None,
            )

            if isrc_result:
                logger.debug(
                    "[%s] Best ISRC result is %s", song.song_id, isrc_result.url
                )

                return isrc_result.url

            if self.filter_results:
                # Order results
                new_results = order_results(search_results, song, self.search_query)
            else:
                new_results = {}
                if len(new_results) > 0:
                    new_results = {search_results[0]: 100.0}

            logger.debug("[%s] Filtered to %s results", song.song_id, len(new_results))

            # song type results are always more accurate than video type,
            # so if we get score of 80 or above
            # we are almost 100% sure that this is the correct link
            if len(new_results) != 0:
                # get the result with highest score
                best_result, best_score = self.get_best_result(new_results)
                logger.debug(
                    "[%s] Best result is %s with score %s",
                    song.song_id,
                    best_result.url,
                    best_score,
                )

                if best_score >= 80 and best_result.verified:
                    logger.debug(
                        "[%s] Returning verified best result %s with score %s",
                        song.song_id,
                        best_result.url,
                        best_score,
                    )

                    return best_result.url

                # Update final results with new results
                results.update(new_results)

        # No matches found
        if not results:
            logger.debug("[%s] No results found", song.song_id)
            return None

        # get the result with highest score
        best_result, best_score = self.get_best_result(results)
        logger.debug(
            "[%s] Returning best result %s with score %s",
            song.song_id,
            best_result.url,
            best_score,
        )

        return best_result.url

    def get_best_result(self, results: Dict[Result, float]) -> Tuple[Result, float]:
        """
        Get the best match from the results
        using views and average match

        ### Arguments
        - results: A dictionary of results and their scores

        ### Returns
        - The best match URL and its score
        """

        best_results = get_best_matches(results, 8)

        # If we have only one result, return it
        if len(best_results) == 1:
            return best_results[0][0], best_results[0][1]

        # Initial best result based on the average match
        best_result = best_results[0]

        # If the best result has a score higher than 80%
        # and it's a isrc search, return it
        if best_result[1] > 80 and best_result[0].isrc_search:
            return best_result[0], best_result[1]

        # If we have more than one result,
        # return the one with the highest score
        # and most views
        if len(best_results) > 1:
            views = []
            for best_result in best_results:
                if best_result[0].views:
                    views.append(best_result[0].views)
                else:
                    views.append(self.get_views(best_result[0].url))

            highest_views = max(views)
            lowest_views = min(views)

            if highest_views in (0, lowest_views):
                return best_result[0], best_result[1]

            weighted_results: List[Tuple[Result, float]] = []
            for index, best_result in enumerate(best_results):
                result_views = views[index]
                views_score = (
                    (result_views - lowest_views) / (highest_views - lowest_views)
                ) * 15
                score = min(best_result[1] + views_score, 100)
                weighted_results.append((best_result[0], score))

            # Now we return the result with the highest score
            return max(weighted_results, key=lambda x: x[1])

        return best_result[0], best_result[1]

    def get_download_metadata(self, url: str, download: bool = False) -> Dict:
        """
        Get metadata for a download using yt-dlp.

        ### Arguments
        - url: The url to get metadata for.

        ### Returns
        - A dictionary containing the metadata.
        """

        try:
            data = self.audio_handler.extract_info(url, download=download)

            if data:
                return data
        except Exception as exception:
            logger.debug(exception)
            raise AudioProviderError(f"YT-DLP download error - {url}") from exception

        raise AudioProviderError(f"No metadata found for the provided url {url}")

    @property
    def name(self) -> str:
        """
        Get the name of the provider.

        ### Returns
        - The name of the provider.
        """

        return self.__class__.__name__
