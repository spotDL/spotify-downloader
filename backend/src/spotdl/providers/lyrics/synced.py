"""Synced lyrics provider using syncedlyrics library."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import httpx

from spotdl.providers.lyrics.base import BaseLyricsProvider

logger = logging.getLogger(__name__)


class SyncedLyricsProvider(BaseLyricsProvider):
    """
    Provider for time-synced lyrics (LRC format).

    Uses the syncedlyrics library which fetches from Deezer, NetEase, etc.
    Note: This wraps a sync library in async to avoid blocking.
    """

    name: ClassVar[str] = "Synced"
    max_concurrent_requests: ClassVar[int] = 2

    def __init__(
        self, client: httpx.AsyncClient | None = None, allow_plain: bool = False
    ) -> None:
        """
        Initialize synced lyrics provider.

        Args:
            client: Optional shared httpx client (not used by syncedlyrics)
            allow_plain: Whether to fallback to plain lyrics if synced unavailable
        """
        super().__init__(client)
        self.allow_plain = allow_plain

    async def get_results(
        self, name: str, artists: list[str], **kwargs: Any
    ) -> dict[str, str]:
        """Not implemented - synced provider doesn't search."""
        raise NotImplementedError("SyncedLyricsProvider doesn't use get_results")

    async def extract_lyrics(self, url: str) -> str | None:
        """Not implemented - synced provider doesn't extract from URLs."""
        raise NotImplementedError("SyncedLyricsProvider doesn't use extract_lyrics")

    async def get_lyrics(self, name: str, artists: list[str]) -> str | None:
        """
        Get synced lyrics directly.

        Runs syncedlyrics.search in a thread pool to avoid blocking.
        """
        query = f"{name} - {artists[0]}" if artists else name

        try:
            # Import here to avoid blocking module load
            import syncedlyrics  # type: ignore[import-untyped]

            # Run blocking syncedlyrics.search in thread pool
            loop = asyncio.get_running_loop()
            lyrics = await loop.run_in_executor(
                None,
                lambda: syncedlyrics.search(
                    query,
                    synced_only=not self.allow_plain,
                ),
            )
            return str(lyrics) if lyrics else None

        except ImportError:
            logger.warning(
                "syncedlyrics package not installed. Install with: pip install syncedlyrics"
            )
            return None
        except Exception as exc:
            logger.debug("Synced lyrics search failed for %s: %s", query, exc)
            return None
