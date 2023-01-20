"""
Base audio provider module.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from yt_dlp import YoutubeDL

from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.config import get_temp_path
from spotdl.utils.formatter import create_search_query, create_song_title
from spotdl.utils.matching import (
    artists_match_fixup1,
    artists_match_fixup2,
    artists_match_fixup3,
    calc_album_match,
    calc_artists_match,
    calc_main_artist_match,
    calc_name_match,
    calc_time_match,
    check_common_word,
    get_best_matches,
)

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
    ) -> None:
        """
        Base class for audio providers.

        ### Arguments
        - output_directory: The directory to save the downloaded songs to.
        - output_format: The format to save the downloaded songs in.
        - cookie_file: The path to a file containing cookies to be used by YTDL.
        - search_query: The query to use when searching for songs.
        - filter_results: Whether to filter results.

        ### Errors
        - raises `NotImplementedError` if self.name is not set.
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

        self.audio_handler = YoutubeDL(
            {
                "format": ytdl_format,
                "quiet": True,
                "no_warnings": True,
                "encoding": "UTF-8",
                "logger": YTDLLogger(),
                "cookiefile": self.cookie_file,
                "outtmpl": f"{get_temp_path()}/%(id)s.%(ext)s",
                "retries": 5,
            }
        )

        logger.debug("Initialized audio provider %s", self.name)
        logger.debug("Output format: %s", self.output_format)
        logger.debug("Cookie file: %s", self.cookie_file)
        logger.debug("Search query: %s", self.search_query)
        logger.debug("Filter results: %s", self.filter_results)
        logger.debug("YTDL format: %s", ytdl_format)

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

    def search(self, song: Song) -> Optional[str]:
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
            isrc_results = self.get_results(
                song.isrc, filter="songs", ignore_spelling=True
            )

            isrc_urls = [result.url for result in isrc_results]
            sorted_isrc_results = self.order_results(isrc_results, song)

            logger.debug(
                "[%s] Found %d results for ISRC %s",
                song.song_id,
                len(isrc_results),
                song.isrc,
            )

            # get the best result, if the score is above 80 return it
            best_isrc_results = sorted(
                sorted_isrc_results.items(), key=lambda x: x[1], reverse=True
            )

            logger.debug(
                "[%s] Filtered to %d ISRC results", song.song_id, len(best_isrc_results)
            )

            if len(best_isrc_results) > 0:
                best_isrc = best_isrc_results[0]
                if best_isrc[1] > 80.0:
                    logger.debug(
                        "[%s] Best ISRC result is %s with score %f",
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

            logger.debug(
                "[%s] Found %d results for search query %s with options %s",
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
                    "[%s] Best ISRC result is %s for %s",
                    song.song_id,
                    isrc_result.url,
                    song.display_name,
                )

                return isrc_result.url

            if self.filter_results:
                # Order results
                new_results = self.order_results(search_results, song)
            else:
                new_results = {}
                if len(new_results) > 0:
                    new_results = {search_results[0]: 100.0}

            logger.debug("[%s] Filtered to %d results", song.song_id, len(new_results))

            # song type results are always more accurate than video type,
            # so if we get score of 80 or above
            # we are almost 100% sure that this is the correct link
            if len(new_results) != 0:
                # get the result with highest score
                best_url, best_score = self.get_best_match(new_results)

                logger.debug(
                    "[%s] Best result is %s with score %f",
                    song.song_id,
                    best_url,
                    best_score,
                )

                if best_score >= 80:
                    logger.debug(
                        "[%s] Returning best result %s with score %f",
                        song.song_id,
                        best_url,
                        best_score,
                    )

                    return best_url

                # Update final results with new results
                results.update(new_results)

        # No matches found
        if not results:
            logger.debug(
                "[%s] No results found for %s", song.song_id, song.display_name
            )
            return None

        # get the result with highest score
        best_url, best_score = self.get_best_match(results)

        logger.debug(
            "[%s] Best result is %s with score %f from all searches",
            song.song_id,
            best_url,
            best_score,
        )

        return best_url

    def order_results(self, results: List[Result], song: Song) -> Dict[Result, float]:
        """
        Order results.

        ### Arguments
        - results: The results to order.
        - song: The song to order for.

        ### Returns
        - The ordered results.
        """

        # Assign an overall avg match value to each result
        links_with_match_value = {}

        # Iterate over all results
        for result in results:
            # skip results that have no common words in their name
            if not check_common_word(song, result):
                logger.debug(
                    "[%s] Skipping %s because it has no common words with %s",
                    song.song_id,
                    result.url,
                    song.display_name,
                )

                continue

            # Calculate match value for main artist
            artists_match = calc_main_artist_match(song, result)
            logger.debug(
                "[%s] Main artist match for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # Calculate match value for all artists
            artists_match += calc_artists_match(song, result)
            logger.debug(
                "[%s] Artists match for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # Calculate initial artist match value
            artists_match = artists_match / (2 if len(song.artists) > 1 else 1)
            logger.debug(
                "[%s] Initial artists match for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # First attempt to fix artist match
            artists_match = artists_match_fixup1(song, result, artists_match)
            logger.debug(
                "[%s] Artists match after fixup1 for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # Second attempt to fix artist match
            artists_match = artists_match_fixup2(song, result, artists_match)
            logger.debug(
                "[%s] Artists match after fixup2 for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # Third attempt to fix artist match
            artists_match = artists_match_fixup3(song, result, artists_match)
            logger.debug(
                "[%s] Artists match after fixup3 for %s: %f",
                song.song_id,
                result.url,
                artists_match,
            )

            # Calculate name match
            name_match = calc_name_match(song, result, self.search_query)
            logger.debug(
                "[%s] Name match for %s: %f",
                song.song_id,
                result.url,
                name_match,
            )

            # Calculate album match
            album_match = calc_album_match(song, result)
            logger.debug(
                "[%s] Album match for %s: %f",
                song.song_id,
                result.url,
                album_match,
            )

            # Calculate time match
            time_match = calc_time_match(song, result)
            logger.debug(
                "[%s] Time match for %s: %f",
                song.song_id,
                result.url,
                time_match,
            )

            # Ignore results with name match lower than 50%
            if name_match <= 50:
                logger.debug(
                    "[%s] Skipping %s because name match is lower than 50%%",
                    song.song_id,
                    result.url,
                )

                continue

            # Ignore results with artists match lower than 70%
            if artists_match < 70:
                logger.debug(
                    "[%s] Skipping %s because artists match is lower than 70%%",
                    song.song_id,
                    result.url,
                )

                continue

            # Calculate total match
            average_match = (artists_match + name_match) / 2
            logger.debug(
                "[%s] Average match for %s: %f",
                song.song_id,
                result.url,
                average_match,
            )

            if (
                result.verified
                and not result.isrc_search
                and result.album
                and album_match <= 80
            ):
                # we are almost certain that this is the correct result
                # so we add the album match to the average match
                average_match = (average_match + album_match) / 2
                logger.debug(
                    "[%s] Adding album match for %s: %f",
                    song.song_id,
                    result.url,
                    average_match,
                )

            # If the time match is lower than 50%
            # and the average match is lower than 75%
            # we skip the result
            if time_match < 50 and average_match < 75:
                logger.debug(
                    "[%s] Skipping %s because time match is lower "
                    "than 50%% and average match is lower than 75%%",
                    song.song_id,
                    result.url,
                )

                continue

            if not result.isrc_search and average_match <= 75 >= time_match:
                # Don't add time to avg match if average match is not the best
                # (lower than 75%)
                average_match = (average_match + time_match) / 2

                logger.debug(
                    "[%s] Adding time match for %s: %f",
                    song.song_id,
                    result.url,
                    average_match,
                )

            average_match = min(average_match, 100)
            logger.debug(
                "[%s] Final average match for %s: %f",
                song.song_id,
                result.url,
                average_match,
            )

            # the results along with the avg Match
            links_with_match_value[result] = average_match

        return links_with_match_value

    def get_best_match(self, results: Dict[Result, float]) -> Tuple[str, float]:
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
            return best_results[0][0].url, best_results[0][1]

        # Initial best result based on the average match
        best_result = best_results[0]

        # If the best result has a score higher than 90%
        # or if the best result has a score higher than 80%
        # but is a verified result or is an isrc result
        # we return the best result
        if best_result[1] > 90 or (
            best_result[1] > 80
            and best_result[0].verified
            or best_result[0].isrc_search
        ):
            return best_result[0].url, best_result[1]

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

            best_result = best_results[views.index(max(views))]

            return best_result[0].url, best_result[1]

        return best_result[0].url, best_result[1]

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
