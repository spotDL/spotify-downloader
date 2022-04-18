"""
Base audio provider module.
"""

from typing import Any, Dict, List, Optional

from yt_dlp import YoutubeDL
from slugify import slugify

from spotdl.utils.providers import match_percentage
from spotdl.types import Song
from spotdl.types.search_result import SearchResult
from spotdl.utils.formatter import (
    create_song_title,
    create_search_query,
)


class AudioProviderError(Exception):
    """
    Base class for all exceptions related to audio searching/downloading.
    """


class YTDLLogger:
    """
    Custom YT-dlp logger.
    """

    def debug(self, msg):  # pylint: disable=R0201
        """
        YTDL uses this to print debug messages.
        """
        pass  # pylint: disable=W0107

    def warning(self, msg):  # pylint: disable=R0201
        """
        YTDL uses this to print warnings.
        """
        pass  # pylint: disable=W0107

    def error(self, msg):  # pylint: disable=R0201
        """
        YTDL uses this to print errors.
        """
        raise Exception(msg)


class AudioProvider:
    """
    Base class for all other providers. Provides some common functionality.
    Handles the yt-dlp audio handler.
    """

    def __init__(
        self,
        output_format: str = "mp3",
        cookie_file: Optional[str] = None,
        search_query: str = "{artists} - {title}",
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
            }
        )

    def search(self, song: Song) -> Optional[str]:
        """
        Search for a song and return best match.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - The url of the best match or None if no match was found.
        """

        raise NotImplementedError

    def get_results(self, search_term: str, **kwargs):
        """
        Get results from audio provider.

        ### Arguments
        - search_term: The search term to use.
        - kwargs: Additional arguments.

        ### Returns
        - A list of results.
        """

        raise NotImplementedError

    def order_results(self, results: List[SearchResult], song: Song) -> Dict[str, Any]:
        """
        Filter results based on the song's metadata.

        ### Arguments
        - results: The results to filter.
        - song: The song to filter by.

        ### Returns
        - A dict of filtered results.
        """

        # Slugify some variables
        slug_song_name = slugify(song.name)
        slug_album_name = slugify(song.album_name)
        slug_song_artist = slugify(song.artist)
        slug_song_title = slugify(
            create_song_title(song.name, song.artists)
            if not self.search_query
            else create_search_query(song, self.search_query, False, None, True)
        )

        # Assign an overall avg match value to each result
        links_with_match_value = {}
        for result in results:
            # Slugify result title
            slug_result_name = slugify(result.name)

            # check for common words in result name
            sentence_words = slug_song_name.replace("-", " ").split(" ")
            common_word = any(
                word != "" and word in slug_result_name for word in sentence_words
            )

            # skip results that have no common words in their name
            if not common_word:
                continue

            # Artist divide number
            artist_divide_number = len(song.artists)

            # Find artist match
            artist_match_number = 0.0
            if result.artists:
                for artist in song.artists:
                    artist_match_number += match_percentage(
                        slugify(artist), slugify(result.artists)
                    )
            else:
                for artist in song.artists:
                    artist_match_number += match_percentage(
                        slugify(artist), slug_result_name
                    )

                # If we didn't find any artist match,
                # we fallback to channel name match
                if artist_match_number <= 50 and result.owner:
                    channel_name_match = match_percentage(
                        slugify(song.artist),
                        slugify(result.owner),
                    )

                    if channel_name_match > artist_match_number:
                        artist_match_number = channel_name_match
                        artist_divide_number = 1

            # skip results with artist match lower than 70%
            artist_match = artist_match_number / artist_divide_number
            if artist_match < 70:
                continue

            if artist_match > 90 and slug_song_artist not in slug_result_name:
                name_match = match_percentage(
                    f"{slug_song_artist}-{slug_result_name}", slug_song_title
                )
            elif slug_song_artist not in slug_result_name:
                name_match = match_percentage(slug_result_name, slug_song_name)
            else:
                name_match = match_percentage(slug_result_name, slug_song_title)

            # Drop results with name match lower than 50%
            if name_match < 50:
                continue

            # Find album match
            album_match = 0.0

            # Calculate album match only for songs
            if result.album:
                album_match = match_percentage(slugify(result.album), slug_album_name)

            # Calculate time match
            delta = result.duration - song.duration
            non_match_value = (delta**2) / song.duration * 100

            time_match = 100 - non_match_value

            if (
                result.album
                and match_percentage(result.album.lower(), result.name.lower()) > 95
                and result.album.lower() != song.album_name.lower()
            ):
                # If the album name is similar to the result song name,
                # But the album name is different from the song album name
                # We don't use album match
                average_match = (artist_match + name_match + time_match) / 3
            elif result.album:
                average_match = (
                    artist_match + album_match + name_match + time_match
                ) / 4
            else:
                # Don't use album match for videos
                average_match = (artist_match + name_match + time_match) / 3

            # the results along with the avg Match
            links_with_match_value[result.link] = average_match

        return links_with_match_value

    def get_download_metadata(self, url: str) -> Dict:
        """
        Get metadata for a download using yt-dlp.

        ### Arguments
        - url: The url to get metadata for.

        ### Returns
        - A dictionary containing the metadata.
        """

        data = self.audio_handler.extract_info(url, download=False)

        if data:
            return data

        raise AudioProviderError(f"No metadata found for the provided url {url}")

    @property
    def name(self) -> str:
        """
        Get the name of the provider.

        ### Returns
        - The name of the provider.
        """

        return self.__class__.__name__
