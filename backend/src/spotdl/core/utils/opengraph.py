"""OpenGraph metadata extraction utilities."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _extract_meta_tag(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
        tag = soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
    return None


async def _fetch_open_graph(url: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; SpotDLUnifiedBot/1.0; "
                    "+https://github.com/spotDL/spotify-downloader)"
                )
            },
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        logger.debug("Failed to fetch OpenGraph data from %s: %s", url, exc)
        return None

    if response.status_code >= 400 or not response.text:
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except (ValueError, TypeError) as exc:
        logger.debug("Failed to parse HTML for OpenGraph from %s: %s", url, exc)
        return None

    title = _extract_meta_tag(soup, "og:title", "twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    description = _extract_meta_tag(soup, "og:description", "twitter:description", "description")
    site_name = _extract_meta_tag(soup, "og:site_name")
    image = _extract_meta_tag(soup, "og:image", "twitter:image")
    if image:
        image = urljoin(str(response.url), image)

    if not title and not description and not site_name and not image:
        return None

    return {
        "name": title or "Untitled",
        "artist": site_name or "Unknown",
        "artists": [site_name] if site_name else [],
        "description": description,
        "cover_url": image,
        "url": str(response.url),
        "site_name": site_name,
    }
