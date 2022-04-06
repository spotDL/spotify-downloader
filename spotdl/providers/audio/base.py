"""
Base audio provider module.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from yt_dlp import YoutubeDL

from spotdl.types import Song


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
        output_directory: str,
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
        self.output_directory = Path(output_directory)
        self.progress_hooks: List[Any] = []
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
                "outtmpl": f"{str(self.output_directory)}/%(id)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "encoding": "UTF-8",
                "logger": YTDLLogger(),
                "cookiefile": self.cookie_file,
            }
        )

        if not hasattr(self, "name"):  # type: ignore
            raise NotImplementedError("Provider must have a name attribute.")

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

    def order_results(self, results, song: Song):
        """
        Order results.

        ### Arguments
        - results: The results to order.
        - song: The song to order for.

        ### Returns
        - The ordered results.
        """

        raise NotImplementedError

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
