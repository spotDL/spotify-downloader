"""Async image fetching and caching service for cover art."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from spotdl_cli.config import get_settings

logger = logging.getLogger(__name__)

CACHE_SIZE = 50
CACHE_RESOLUTION = (128, 128)


class ImageService:
    """Fetches and caches cover art images.

    Two-level cache:
    - In-memory LRU (bounded OrderedDict)
    - Disk cache under Settings.cache_dir / "covers/"

    Per-URL asyncio.Lock deduplicates concurrent fetches for the same URL.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None
        self._memory_cache: OrderedDict[str, Image.Image] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}
        self._disk_dir = self._settings.cache_dir / "covers"
        self._disk_dir.mkdir(parents=True, exist_ok=True)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                headers={"User-Agent": "SpotDL-CLI/5.0.0"},
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                follow_redirects=True,
            )
        return self._client

    def _url_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _disk_path(self, url: str) -> Path:
        return self._disk_dir / f"{self._url_hash(url)}.png"

    def _get_lock(self, url: str) -> asyncio.Lock:
        if url not in self._locks:
            self._locks[url] = asyncio.Lock()
        return self._locks[url]

    async def get_image(self, url: str) -> Image.Image | None:
        """Fetch a cover art image, returning a PIL Image or None on failure."""
        if not url:
            return None

        # 1. Memory cache
        if url in self._memory_cache:
            self._memory_cache.move_to_end(url)
            return self._memory_cache[url]

        # 2. Disk cache
        disk = self._disk_path(url)
        if disk.exists():
            try:
                img = Image.open(disk).copy()
                self._put_memory(url, img)
                return img
            except Exception:
                disk.unlink(missing_ok=True)

        # 3. Fetch from network (deduplicated per-URL)
        lock = self._get_lock(url)
        async with lock:
            # Re-check memory after acquiring lock
            if url in self._memory_cache:
                self._memory_cache.move_to_end(url)
                return self._memory_cache[url]

            try:
                client = await self._get_client()
                response = await client.get(url)
                response.raise_for_status()

                img = Image.open(BytesIO(response.content))
                img = img.convert("RGB")
                img.thumbnail(CACHE_RESOLUTION, Image.Resampling.LANCZOS)

                # Save to disk
                img.save(disk, "PNG")

                self._put_memory(url, img)
                return img
            except Exception as e:
                logger.debug(f"Failed to fetch cover art: {e}")
                return None

    def _put_memory(self, url: str, img: Image.Image) -> None:
        self._memory_cache[url] = img
        self._memory_cache.move_to_end(url)
        while len(self._memory_cache) > CACHE_SIZE:
            self._memory_cache.popitem(last=False)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


_image_service: ImageService | None = None


def get_image_service() -> ImageService:
    """Get the global ImageService singleton."""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service
