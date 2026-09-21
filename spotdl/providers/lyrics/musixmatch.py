"""
MusixMatch lyrics provider.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests
from playwright.async_api import async_playwright

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["MusixMatch"]
logger = logging.getLogger(__name__)


class MusixMatch(LyricsProvider):
    """
    MusixMatch lyrics provider class.
    """

    ## email : Email address used to authenticate using Musixmatch
    ## password: Password used to authenticate using Musixmatch
    ## cookies : Cookies obtained from the authenticated browser session.

    def __init__(self, email: str, password: str):
        """
        ### Notes
        - email: Email address used to authenticate using Musixmatch
        - password: Password used to authenticate using Musixmatch
        - cookies: Cookies obtained from the authenticated browser session.
        """
        super().__init__()
        self.email = email
        self.password = password
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.cookies = loop.run_until_complete(self.login_and_get_cookies())

    async def login_and_get_cookies(self) -> dict[str, str]:
        """
        logs into musixmatch and returns  the autheticated cookies

        Returns :
            A dictionary containing the authenticated session cookies
        """
        async with async_playwright() as p:

            # Going to musixmatch to log in and get cookies for later use

            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.musixmatch.com/")

            await page.click("text= Login")
            card = page.locator("div[tabindex='0']").filter(has_text="Community")
            await card.wait_for(state="visible")
            await card.click()

            email_btn = page.get_by_text("Continue with email")
            await email_btn.wait_for(state="visible")
            await email_btn.click()

            await page.wait_for_selector("input[type='email']", state="visible")
            await page.fill("input[type ='Email']", self.email)
            await page.fill("input[type ='Password']", self.password)
            await page.get_by_text("Sign in", exact=True).click()

            # Waiting for either redirection (success) or a login failed alert (failure)

            failure_locator = (
                page.get_by_text(re.compile("wrong credentials", re.I))
                .or_(
                    page.get_by_text(
                        re.compile("email or password are incorrect", re.I)
                    )
                )
                .or_(page.get_by_text(re.compile("AUTH002", re.I)))
                .or_(page.get_by_text(re.compile("SignIn error", re.I)))
            )
            success = asyncio.ensure_future(
                page.wait_for_url(
                    lambda url: "auth.musixmatch.com" not in url, timeout=10000
                )
            )
            failure = asyncio.ensure_future(
                failure_locator.first.wait_for(timeout=10000)
            )
            done, pending = await asyncio.wait(
                {success, failure}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

            if failure in done and failure.exception() is None:
                raise RuntimeError(
                    "MusixMatch login failed. Invalid email and password: "
                    f"{self.email} {self.password}\n"
                    "Remember that you have to create an account via 'Continue "
                    "with email' at https://auth.musixmatch.com/."
                )

            if success not in done or success.exception() is not None:
                raise RuntimeError("MusixMatch login timed out after 10 seconds.")

            playwright_cookies = await page.context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in playwright_cookies}

            await browser.close()
            return cookies_dict

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        lyrics_resp = requests.get(
            url,
            impersonate="chrome110",
            cookies=self.cookies,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )

        lyrics_soup = BeautifulSoup(lyrics_resp.text, "html.parser")
        script_tag = lyrics_soup.find("script", id="__NEXT_DATA__")
        if not isinstance(script_tag, Tag) or script_tag.string is None:
            return None
        data = json.loads(script_tag.string)
        page_data = data["props"]["pageProps"]["data"]
        track_info = page_data.get("trackInfo", {})
        lyrics = track_info.get("data", {}).get("lyrics", {}).get("body", "")

        return lyrics

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

        artists_str = ", ".join(
            artist for artist in artists if artist.lower() not in name.lower()
        )

        # quote the query so that it's safe to use in a url
        # e.g "Au/Ra" -> "Au%2FRa"
        query = quote(f"{name} - {artists_str}", safe="")

        search_url = f"https://www.musixmatch.com/search?query={query}"
        search_resp = requests.get(
            search_url,
            impersonate="chrome110",
            timeout=10,
            cookies=self.cookies,
            proxies=GlobalConfig.get_parameter("proxies"),
        )

        logger.debug(
            f"Musixmatch search response status code: {search_resp.status_code}"
        )

        if not search_resp.ok:
            raise RuntimeError(
                f"Received HTTP {search_resp.status_code} from {search_url}"
            )

        search_soup = BeautifulSoup(search_resp.text, "html.parser")
        script_tag = search_soup.find("script", id="__NEXT_DATA__")

        if not isinstance(script_tag, Tag) or script_tag.string is None:
            return {}

        data = json.loads(script_tag.string)

        page_data = data["props"]["pageProps"]["data"]
        body = page_data["openSearch"]["data"]["opensearchTrackSearch"]["body"]

        results = {}
        best_match = body.get("bestMatch")
        if best_match:
            title = f"{best_match.get('track_name','')} - {best_match.get('artist_name','')}"

            url = best_match.get("track_share_url")
            if url:
                results[title] = url

        track_list = body.get("tracks", [])
        for track in track_list:

            title = f"{track.get('track_name','')} - {track.get('artist_name','')}"
            url = track.get("track_share_url")
            if url:
                results[title] = url

        return results
