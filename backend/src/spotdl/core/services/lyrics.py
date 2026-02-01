"""Lyrics service for coordinating multiple providers."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.lyrics import Lyrics as LyricsModel
from spotdl.providers.lyrics.azlyrics import AZLyricsProvider
from spotdl.providers.lyrics.genius import GeniusProvider, GeniusWebProvider
from spotdl.providers.lyrics.musixmatch import MusixMatchProvider
from spotdl.providers.lyrics.synced import SyncedLyricsProvider

if TYPE_CHECKING:
    from spotdl.providers.lyrics.base import BaseLyricsProvider

logger = logging.getLogger(__name__)


@dataclass
class LyricsResult:
    """Result from lyrics fetch operation."""

    lyrics_text: str
    lyrics_synced: str | None
    source: str
    from_cache: bool = False


class LyricsServiceError(Exception):
    """Base exception for lyrics service errors."""

    pass


class LyricsService:
    """
    Service for fetching lyrics from multiple providers.

    Features:
    - Parallel provider fetching with asyncio.gather
    - Prioritizes synced lyrics over plain lyrics
    - Caches results to database
    - Handles provider failures gracefully
    """

    def __init__(
        self,
        session: AsyncSession,
        genius_token: str | None = None,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize lyrics service.

        Args:
            session: Database session
            genius_token: Genius API token (optional)
            enable_cache: Whether to cache lyrics to database
        """
        self.session = session
        self.genius_token = genius_token
        self.enable_cache = enable_cache

        # Shared HTTP client for connection pooling
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LyricsService:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_providers(self) -> list[BaseLyricsProvider]:
        """Get enabled providers in priority order."""
        providers: list[BaseLyricsProvider] = []

        # Priority 1: Synced lyrics (LRC format)
        providers.append(SyncedLyricsProvider(client=self._client, allow_plain=False))

        # Priority 2: Plain lyrics providers
        if self.genius_token:
            providers.append(GeniusProvider(self.genius_token, client=self._client))
        else:
            # Fall back to web scraping if no API token
            providers.append(GeniusWebProvider(client=self._client))

        providers.append(MusixMatchProvider(client=self._client))
        providers.append(AZLyricsProvider(client=self._client))

        return providers

    async def fetch_lyrics(
        self,
        song_id: uuid.UUID,
        name: str,
        artists: list[str],
        force_refresh: bool = False,
    ) -> LyricsResult | None:
        """
        Fetch lyrics for a song.

        Args:
            song_id: Internal song UUID
            name: Song name
            artists: Artist names
            force_refresh: Skip cache and fetch fresh lyrics

        Returns:
            LyricsResult or None if no lyrics found
        """
        # Check cache first
        if self.enable_cache and not force_refresh:
            cached = await self._get_from_cache(song_id)
            if cached:
                return cached

        # Fetch from providers in parallel
        result = await self._fetch_from_providers(name, artists)

        if result and self.enable_cache:
            await self._save_to_cache(song_id, result)

        return result

    async def _get_from_cache(self, song_id: uuid.UUID) -> LyricsResult | None:
        """Get lyrics from database cache."""
        # Prefer synced lyrics, fall back to any lyrics
        stmt = (
            select(LyricsModel)
            .where(LyricsModel.song_id == song_id)
            .order_by(
                # Prefer synced lyrics (lyrics_synced IS NOT NULL first)
                LyricsModel.lyrics_synced.is_(None),
                LyricsModel.fetched_at.desc(),
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        lyrics_model = result.scalar_one_or_none()

        if not lyrics_model:
            return None

        return LyricsResult(
            lyrics_text=lyrics_model.lyrics_text,
            lyrics_synced=lyrics_model.lyrics_synced,
            source=lyrics_model.source,
            from_cache=True,
        )

    async def _fetch_from_providers(
        self, name: str, artists: list[str]
    ) -> LyricsResult | None:
        """
        Fetch lyrics from all providers in parallel.

        Returns the first successful result, prioritizing synced lyrics.
        """
        providers = self._get_providers()

        if not providers:
            logger.warning("No lyrics providers configured")
            return None

        # Initialize all providers
        for provider in providers:
            await provider.__aenter__()

        try:
            # Fetch from all providers concurrently
            tasks = [provider.get_lyrics(name, artists) for provider in providers]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results in order (synced first)
            for provider, result in zip(providers, results):
                if isinstance(result, Exception):
                    logger.debug(
                        "%s provider failed: %s",
                        provider.name,
                        result,
                    )
                    continue

                if result:
                    is_synced = isinstance(provider, SyncedLyricsProvider)
                    logger.info(
                        "Found lyrics from %s (synced=%s) for %s - %s",
                        provider.name,
                        is_synced,
                        name,
                        ", ".join(artists),
                    )

                    # Check if LRC format (synced)
                    lyrics_synced = None
                    if is_synced or self._is_lrc_format(result):
                        lyrics_synced = result
                        # Also extract plain text
                        lyrics_text = self._lrc_to_plain(result)
                    else:
                        lyrics_text = result

                    return LyricsResult(
                        lyrics_text=lyrics_text,
                        lyrics_synced=lyrics_synced,
                        source=provider.name.lower(),
                    )

            logger.info("No lyrics found for %s - %s", name, ", ".join(artists))
            return None

        finally:
            # Clean up providers
            for provider in providers:
                await provider.__aexit__(None, None, None)

    def _is_lrc_format(self, text: str) -> bool:
        """Check if text is in LRC format."""
        import re

        # LRC format has timestamp tags like [mm:ss.xx]
        lrc_pattern = r"^\[\d{2}:\d{2}\.\d{2,3}\]"
        return bool(re.search(lrc_pattern, text, re.MULTILINE))

    def _lrc_to_plain(self, lrc_text: str) -> str:
        """Convert LRC format to plain text."""
        import re

        # Remove timestamp tags
        plain = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", lrc_text)
        # Clean up extra whitespace
        lines = [line.strip() for line in plain.split("\n") if line.strip()]
        return "\n".join(lines)

    async def _save_to_cache(self, song_id: uuid.UUID, result: LyricsResult) -> None:
        """Save lyrics to database cache."""
        try:
            # Check if already exists for this source
            stmt = select(LyricsModel).where(
                LyricsModel.song_id == song_id,
                LyricsModel.source == result.source,
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()

            if existing:
                # Update existing
                existing.lyrics_text = result.lyrics_text
                existing.lyrics_synced = result.lyrics_synced
            else:
                # Create new
                lyrics = LyricsModel(
                    song_id=song_id,
                    lyrics_text=result.lyrics_text,
                    lyrics_synced=result.lyrics_synced,
                    source=result.source,
                )
                self.session.add(lyrics)

            await self.session.flush()

        except Exception as exc:
            logger.warning("Failed to cache lyrics: %s", exc)

    async def get_lyrics_for_song(
        self, song_id: uuid.UUID
    ) -> LyricsResult | None:
        """
        Get cached lyrics for a song (no fetching).

        Args:
            song_id: Internal song UUID

        Returns:
            LyricsResult if found in cache, None otherwise
        """
        return await self._get_from_cache(song_id)


def get_lyrics_service(
    session: AsyncSession,
    genius_token: str | None = None,
    enable_cache: bool = True,
) -> LyricsService:
    """
    Factory function to create a LyricsService.

    Args:
        session: Database session
        genius_token: Optional Genius API token
        enable_cache: Whether to cache lyrics

    Returns:
        Configured LyricsService instance
    """
    return LyricsService(
        session=session,
        genius_token=genius_token,
        enable_cache=enable_cache,
    )
