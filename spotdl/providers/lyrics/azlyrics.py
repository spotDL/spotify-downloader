"""
AZLyrics lyrics module.
"""

import logging
from typing import Dict, List, Optional

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
        self.session.headers.update(
            {
                "Host": "www.azlyrics.com",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
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

        self.x_code = self._get_x_code()

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
            try:
                response = self.session.get(
                    "https://www.azlyrics.com/search/", params=params
                )

                if not response.ok:
                    continue

                soup = BeautifulSoup(response.content, "html.parser")
                break

            except requests.ConnectionError:
                logger.debug(
                    "AZLyrics: ConnectionError on attempt %s with params: %s", i, params
                )
                continue

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

        response = self.session.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all divs that don't have a class
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

        x_code = None

        try:
            self.session.get("https://www.azlyrics.com/")

            resp = self.session.get("https://www.azlyrics.com/geo.js")
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

        except requests.ConnectionError:
            pass

        # We now filter the string so we can extract the x code.
        start_index = js_code.find('value"') + 9
        end_index = js_code[start_index:].find('");')

        x_code = js_code[start_index : start_index + end_index]

        if x_code:
            return x_code.strip()

        logger.debug("AZLyrics: Failed to retrieve x_code.")
        return None
