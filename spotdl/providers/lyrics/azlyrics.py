"""
AZLyrics lyrics module.
"""

import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from spotdl.providers.lyrics.base import LyricsProvider

__all__ = ["AzLyrics"]
logger = logging.getLogger(__name__)
# mypy: disable-error-code="union-attr"


class AzLyrics(LyricsProvider):
    """
    AZLyrics lyrics provider class.
    """

    def __init__(self):
        super().__init__()

        self.session = requests.Session()
        # No User-Agent override: AZLyrics traps requests claiming to be a
        # browser in a redirect loop, while requests' default UA is served
        # normally (see #2682). A `Host` header also causes a redirect loop.
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Priority": "u=0, i",
            }
        )

        self.x_code = None
        self._is_blocked = False

    @staticmethod
    def _blocked(response: requests.Response) -> bool:
        """Return True when AZLyrics answered with its bot-check interstitial.

        AZLyrics answers requests from flagged networks with a
        "request for access" page on the b.azlyrics.com subnet instead of
        real content. Detect it so we fail fast instead of retrying a page
        that contains no results.
        """
        if (
            any(
                urlparse(hop.url).hostname == "b.azlyrics.com"
                for hop in response.history
            )
            or urlparse(response.url).hostname == "b.azlyrics.com"
        ):
            return True
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text().lower() if soup.title else ""
        return (
            "request for access" in title
            or "detected unusual activity" in title
            or "az_unblock" in response.text
        )

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Fetch through the session; None when the bot wall was served."""

        if self._is_blocked:
            return None

        try:
            response = self.session.get(url, **kwargs)
        except (requests.ConnectionError, requests.TooManyRedirects):
            logger.debug("AZLyrics: request failed: %s", url)
            return None

        if self._blocked(response):
            self._is_blocked = True
            logger.debug(
                "AZLyrics: bot-check interstitial present (%s), aborting.", response.url
            )
            return None

        return response

    def get_results(self, name: str, artists: List[str], **_) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """

        if self.x_code is None:
            self.x_code = self._get_x_code()

        if self.x_code is None:
            return {}

        params = {
            "q": f"{name.strip().replace(' ', '+')}+{artists[0].strip().replace(' ', '+')}",
            "x": self.x_code,
        }

        soup = None
        for i in range(4):  # Retry up to 4 times
            response = self._get("https://www.azlyrics.com/search/", params=params)

            if response is None:
                if self._is_blocked:
                    break
                continue

            if not response.ok:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            break

        if soup is None:
            return {}

        td_tags = soup.find_all("td")
        if len(td_tags) == 0:
            return {}

        results = {}
        for td_tag in td_tags:

            # Ensure td_tag is a Tag object before calling find_all
            if not isinstance(td_tag, Tag):
                continue

            a_tags = td_tag.find_all("a", href=True)

            if len(a_tags) == 0:
                continue

            a_tag = a_tags[0]
            url = a_tag.get("href", "").strip()

            if url == "":
                continue

            title = td_tag.find("span").get_text().strip()
            artist = td_tag.find("b").get_text().strip()

            results[f"{artist} - {title}"] = url

        return results

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        response = self._get(url)
        if response is None:
            return None

        # Find all divs that don't have a class
        soup = BeautifulSoup(response.text, "html.parser")
        div_tags = soup.find_all("div", class_=False, id_=False)

        # Find the div with the longest text
        lyrics_div = sorted(div_tags, key=lambda x: len(x.text))[-1]

        # extract lyrics from div and clean it up
        lyrics = lyrics_div.get_text().strip()

        return lyrics

    def _get_x_code(self) -> Optional[str]:
        """
        Returns the x_code used by AZLyrics.
        This is needed for AZLyrics to respond properly.

        ### Returns
        - The x_code used by AZLyrics or None if it couldn't be retrieved.
        """

        home = self._get("https://www.azlyrics.com/")
        if home is None:
            return None

        resp = self._get("https://www.azlyrics.com/geo.js")
        if resp is None:
            return None

        js_code = resp.text

        # /geo.js returns a JS script, in which that 'x' code is located. e.g.
        # var az_country_code;
        # az_country_code = "HN";
        # (function() {
        #     var ep = document.createElement("input");
        #     ep.setAttribute("type", "hidden");
        #     ep.setAttribute("name", "x");
        #     ep.setAttribute("value", "x code goes here");
        #     var els = document.querySelectorAll('form.search');
        #     for (var n = 0; n < els.length; n++) {
        #         els[n].appendChild(ep.cloneNode());
        #     }
        # })();

        # We now filter the string so we can extract the x code.
        start_index = js_code.find('value"') + 9
        end_index = js_code[start_index:].find('");')

        x_code = js_code[start_index : start_index + end_index]

        if x_code:
            return x_code.strip()

        logger.debug("AZLyrics: Failed to retrieve x_code.")
        return None
