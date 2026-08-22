"""
MusixMatch lyrics provider.
"""
import json
import logging
from typing import Dict, List, Optional
from urllib.parse import quote
from playwright.async_api import async_playwright
# import requests
from bs4 import BeautifulSoup
from getpass import getpass 
import time
from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig
from curl_cffi import requests
__all__ = ["MusixMatch"]

import asyncio

class MusixMatch(LyricsProvider):
    """
    MusixMatch lyrics provider class.


    """
    def __init__(self):

        super().__init__()
        self.email=input("enter email for musixmatch ")
        self.password=getpass("Enter Password")
        self.cookies = asyncio.run(self.login_and_get_cookies())

        print(self.cookies)

    async def login_and_get_cookies(self) -> dict:

        async with async_playwright( ) as p:
            browser= await p.chromium.launch(headless=False)
            page= await browser.new_page()

            await page.goto("https://www.musixmatch.com/")

            await page.click("text= Login")

            card = page.locator("div[tabindex='0']").filter(has_text="Community")
            await card.wait_for(state="visible")

            await card.click()

            email_btn=page.get_by_text("Continue with email")

            await email_btn.wait_for(state="visible")

            await email_btn.click()

            await page.wait_for_selector("input[type='email']",state="visible")

            await page.fill("input[type ='Email']", self.email)

            await page.fill("input[type ='Password']", self.password)

            await page.get_by_text("Sign in", exact=True).click()


            await page.wait_for_url(lambda url: "auth.musixmatch.com" not in url, timeout=10000)

            playwright_cookies = await page.context.cookies()

            cookies_dict = {c['name']: c['value'] for c in playwright_cookies}

            await browser.close()
            return cookies_dict
     

    # def extract_lyrics(self, url: str, **_) -> Optional[str]:
    #     """
    #     Extracts the lyrics from the given url.

    #     ### Arguments
    #     - url: The url to extract the lyrics from.
    #     - kwargs: Additional arguments.

    #     ### Returns
    #     - The lyrics of the song or None if no lyrics were found.
    #     """

    #     lyrics_resp = requests.get(
    #         url,
    #         impersonate=chrome110,
    #         # headers=self.headers,
    #         timeout=10,
    #         proxies=GlobalConfig.get_parameter("proxies"),

    #     )

    #     lyrics_soup = BeautifulSoup(lyrics_resp.text, "html.parser")
    #     lyrics_paragraphs = lyrics_soup.select("p.mxm-lyrics__content")
    #     lyrics = "\n".join(i.get_text() for i in lyrics_paragraphs)

    #     return lyrics

    def get_results(self, name: str, artists: List[str], **kwargs) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """
        track_search = kwargs.get("track_search", False)
        artists_str = ", ".join(
            artist for artist in artists if artist.lower() not in name.lower()
        )

        # quote the query so that it's safe to use in a url
        # e.g "Au/Ra" -> "Au%2FRa"
        query = quote(f"{name} - {artists_str}", safe="")

        # search the `tracks page` if track_search is True
        # if track_search:
        #     query += "%20tracks"

        search_url = f"https://www.musixmatch.com/search?query={query}"

        search_resp = requests.get(
            search_url,
            impersonate="chrome110",
            timeout=10,
            cookies=self.cookies,
            proxies=GlobalConfig.get_parameter("proxies"),
        )

        print(search_resp.status_code)

        if not search_resp.ok:
            raise RuntimeError(
                f"Received HTTP {search_resp.status_code} from {search_url}"
            )

        soup= BeautifulSoup(search_resp.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")

        if script_tag:
            json_text=script_tag.string

            data =json.loads(json_text)

        print(data)
        page_data = data["props"]["pageProps"]["data"]

        body = page_data["openSearch"]["data"]["opensearchTrackSearch"]["body"]

        best_match = body["bestMatch"]

        print(best_match["track_name"])
        print(best_match["artist_name"])
        print(best_match["lyrics_id"])
        print(best_match["track_share_url"])


        # search_soup = BeautifulSoup(search_resp.text, "html.parser")
        # song_url_tag = search_soup.select("a[href^='/lyrics/']")

        # if not song_url_tag:
        #     # If Musixmatch returned a valid page but no lyrics links, it's likely the unauthenticated SPA
        #     if search_soup.find("script", id="__NEXT_DATA__"):
        #         logger = logging.getLogger(__name__)
        #         logger.warning(
        #             f"MusixMatch: Received {search_resp.status_code} for {name}, but search results are hidden by Musixmatch authentication."
        #         )
        #         return {}

        #     # song_url_tag being None means no results were found on the
        #     # All Results page, therefore, we use `track_search` to
        #     # search the tracks page.

        #     # track_search being True means we are already searching the tracks page.
        #     if track_search:
        #         return {}

        #     return self.get_results(name, artists, track_search=True)

        # results: Dict[str, str] = {}
        # for tag in song_url_tag:
        #     results[tag.get_text()] = "https://www.musixmatch.com" + str(
        #         tag.get("href", "")
        #     )

        # return results

if __name__ == "__main__":
    mxm=MusixMatch()
    mxm.get_results("Lay All Your Love On Me",["ABBA"])
