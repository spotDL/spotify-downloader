from pathlib import Path
from typing import Any, Callable, List, Optional

from spotdl.types import Song


class AudioProviderError(Exception):
    """
    Base class for all exceptions related to audio searching/downloading.
    """


class AudioProvider:
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
        """

        self.output_format = output_format
        self.output_directory = Path(output_directory)
        self.progress_hooks: List[Any] = []
        self.cookie_file = cookie_file
        self.search_query = search_query
        self.filter_results = filter_results

    def search(self, song: Song) -> Optional[str]:
        """
        Search for a song and return best match.
        """

        raise NotImplementedError

    def get_results(self, search_term: str, **kwargs):
        """
        Get results from audio provider.
        """

        raise NotImplementedError

    def order_results(self, results, song: Song):
        """
        Order results.
        """

        raise NotImplementedError

    def perform_audio_download(self, url: str) -> Optional[Path]:
        """
        Perform audio download.
        """

        raise NotImplementedError

    def add_progress_hook(self, hook: Callable) -> None:
        """
        Add a hook to be called when the download progress changes.
        """

        self.progress_hooks.append(hook)
