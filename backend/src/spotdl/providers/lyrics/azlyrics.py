"""AZLyrics provider (async)."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import httpx
from bs4 import BeautifulSoup, Tag

from spotdl.providers.lyrics.base import BaseLyricsProvider

logger = logging.getLogger(__name__)


class AZLyricsProvider(BaseLyricsProvider):
    """AZLyrics provider with x_code authentication."""

    name: ClassVar[str] = "AZLyrics"
    max_concurrent_requests: ClassVar[int] = 1  # Be gentle

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self.x_code: str | None = None
        # Update headers for AZLyrics
        self.headers.update(
            {
                "Host": "www.azlyrics.com",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )

    async def _ensure_x_code(self) -> bool:
        """Fetch and cache the x_code for authentication."""
        if self.x_code:
            return True

        try:
            # Visit homepage first
            await self.client.get("https://www.azlyrics.com/", headers=self.headers)

            # Get geo.js which contains x_code
            geo_response = await self.client.get(
                "https://www.azlyrics.com/geo.js", headers=self.headers
            )
            js_code = geo_response.text

            # Extract x_code from JavaScript
            start_index = js_code.find('value"') + 9
            end_index = js_code[start_index:].find('");')
            self.x_code = js_code[start_index : start_index + end_index].strip()

            return bool(self.x_code)

        except Exception as exc:
            logger.debug("Failed to get AZLyrics x_code: %s", exc)
            return False

    async def get_results(self, name: str, artists: list[str], **kwargs: Any) -> dict[str, str]:
        """Search AZLyrics."""
        if not await self._ensure_x_code():
            return {}

        query_parts = [name.strip().replace(" ", "+")]
        if artists:
            query_parts.append(artists[0].strip().replace(" ", "+"))

        params = {
            "q": "+".join(query_parts),
            "x": self.x_code,
        }

        for attempt in range(3):
            try:
                response = await self.client.get(
                    "https://www.azlyrics.com/search/", params=params, headers=self.headers
                )
                if not response.is_success:
                    continue

                soup = BeautifulSoup(response.content, "html.parser")
                td_tags = soup.find_all("td")

                if not td_tags:
                    return {}

                results: dict[str, str] = {}
                for td_tag in td_tags:
                    if not isinstance(td_tag, Tag):
                        continue

                    a_tags = td_tag.find_all("a", href=True)
                    if not a_tags:
                        continue

                    url = str(a_tags[0].get("href", "")).strip()
                    if not url:
                        continue

                    title_tag = td_tag.find("span")
                    artist_tag = td_tag.find("b")
                    if title_tag and artist_tag:
                        title = title_tag.get_text(strip=True)
                        artist = artist_tag.get_text(strip=True)
                        results[f"{artist} - {title}"] = url

                return results

            except Exception as exc:
                logger.debug("AZLyrics search attempt %d failed: %s", attempt + 1, exc)
                continue

        return {}

    async def extract_lyrics(self, url: str) -> str | None:
        """Extract lyrics from AZLyrics page."""
        try:
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find divs without class/id (lyrics container)
            div_tags = soup.find_all("div", class_=False, id_=False)

            # Get the longest div (usually lyrics)
            if not div_tags:
                return None

            lyrics_div = max(div_tags, key=lambda x: len(x.text))
            lyrics = lyrics_div.get_text(strip=True)

            return lyrics if lyrics else None

        except Exception as exc:
            logger.debug("AZLyrics extraction failed: %s", exc)
            return None
