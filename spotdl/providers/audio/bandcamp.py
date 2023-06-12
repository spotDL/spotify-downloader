"""
BandCamp module for downloading and searching songs.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import bandcamp_api.search as BandCampSearch
import bandcamp_api.track as BandCampTrack
import requests
from bs4 import BeautifulSoup

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["BandCamp"]

logger = logging.getLogger(__name__)

# Disable logging from bandcamp_api
BandCampTrack.logging.debug = lambda *_: None


class BandCamp(AudioProvider):
    """
    SoundCloud audio provider class
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the SoundCloud API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)

    def search_tracks(self, search_string: str):
        """
        Search for tracks on . Currently broken in
        the bandcamp

        ### Arguments
        - search_string: String to search for on SoundCloud

        ### Returns
        - List of `Result` objects
        """

        link = "https://bandcamp.com/search?q=" + search_string + "&item_type=t"
        try:
            response = requests.get(link, timeout=10)
        except requests.exceptions.MissingSchema:
            pass

        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception:
            soup = BeautifulSoup(response.text, "html.parser")

        results = soup.find("ul", {"class": "result-items"})
        things_to_return: List[BandCampSearch.TrackResults] = []

        if not results:
            return things_to_return

        for item in results.find_all("li"):
            track = BandCampSearch.TrackResults()

            track.track_title = BandCampSearch.clean_string(
                item.find("div", {"class": "heading"}).text
            )

            track.album_title = (
                BandCampSearch.clean_string(item.find("div", {"class": "subhead"}).text)
                .split(" by ", maxsplit=1)[0]
                .replace("from ", "")
            )

            track.artist_title = BandCampSearch.clean_string(
                item.find("div", {"class": "subhead"}).text
            ).split("by ")[1]

            track.date_released = " ".join(
                item.find("div", {"class": "released"}).text.split()
            )[9:]
            track.date_released = datetime.strptime(track.date_released, "%B %d, %Y")
            track.date_released = int(time.mktime(track.date_released.timetuple()))

            track.album_art_url = item.find("img").get("src").split("_")[0] + "_0.jpg"

            track.track_url = BandCampSearch.clean_string(
                item.find("div", {"class": "itemurl"}).text
            )

            things_to_return.append(track)

        return things_to_return

    def get_results(self, search_term: str, *_args, **_kwargs) -> List[Result]:
        """
        Get results from slider.kz

        ### Arguments
        - search_term: The search term to search for.
        - args: Unused.
        - kwargs: Unused.

        ### Returns
        - A list of slider.kz results if found, None otherwise.
        """

        results: List[BandCampSearch.TrackResults] = self.search_tracks(search_term)

        simplified_results: List[Result] = []
        for result in results:
            track = BandCampTrack.Track(result.track_url)

            simplified_results.append(
                Result(
                    source="bandcamp",
                    url=track.track_url,
                    verified=False,
                    name=track.track_title,
                    duration=track.duration_seconds,
                    author=track.artist_title,
                    result_id=track.track_url,
                    search_query=search_term,
                    album=track.album_title,
                    artists=tuple(track.artist_title.split(", ")),
                )
            )

        return simplified_results
