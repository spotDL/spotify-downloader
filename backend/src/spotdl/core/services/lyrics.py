"""Lyrics service for coordinating multiple providers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.provider_preferences import get_enabled_lyrics_provider_ids
from spotdl.core.providers_config import ProviderPreference
from spotdl.db.models.lyrics import Lyrics as LyricsModel
from spotdl.db.repositories import LyricsRepository
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
    - Respects user-configured provider order
    """

    def __init__(
        self,
        session: AsyncSession,
        genius_token: str | None = None,
        enable_cache: bool = True,
        lyrics_preferences: list[ProviderPreference] | None = None,
    ) -> None:
        """
        Initialize lyrics service.

        Args:
            session: Database session
            genius_token: Genius API token (optional)
            enable_cache: Whether to cache lyrics to database
            lyrics_preferences: User's lyrics source preferences (ordered list with enabled status).
                              If provided, determines provider order and which providers to use.
        """
        self.session = session
        self.genius_token = genius_token
        self.enable_cache = enable_cache
        self._lyrics_preferences = lyrics_preferences

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
        """Get enabled providers in user-specified priority order."""
        # If no preferences, use default order
        if self._lyrics_preferences is None:
            return self._get_default_providers()

        # Get enabled providers in user's order
        prefs = get_enabled_lyrics_provider_ids(self._lyrics_preferences)
        provider_order = prefs["provider_order"]

        providers: list[BaseLyricsProvider] = []

        for provider_id in provider_order:
            provider = self._create_provider(provider_id)
            if provider is not None:
                providers.append(provider)

        # If no providers enabled after processing, use defaults
        if not providers:
            return self._get_default_providers()

        return providers

    def _get_default_providers(self) -> list[BaseLyricsProvider]:
        """Get default provider list (legacy order)."""
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

    def _create_provider(self, provider_id: str) -> BaseLyricsProvider | None:
        """
        Create a provider instance by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            Provider instance or None if unknown
        """
        if provider_id == "synced":
            return SyncedLyricsProvider(client=self._client, allow_plain=False)
        elif provider_id == "genius":
            if self.genius_token:
                return GeniusProvider(self.genius_token, client=self._client)
            else:
                return GeniusWebProvider(client=self._client)
        elif provider_id == "musixmatch":
            return MusixMatchProvider(client=self._client)
        elif provider_id == "azlyrics":
            return AZLyricsProvider(client=self._client)
        else:
            logger.warning(f"Unknown lyrics provider ID: {provider_id}")
            return None

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

    async def fetch_all_lyrics(
        self,
        song_id: uuid.UUID,
        name: str,
        artists: list[str],
        album_name: str | None = None,
        duration: int | None = None,
    ) -> list[LyricsResult]:
        """
        Fetch lyrics from ALL providers and store each result.

        Unlike fetch_lyrics which returns the first result, this method
        fetches from ALL providers in parallel and stores each result
        separately, allowing users to compare lyrics from different sources.

        Args:
            song_id: Internal song UUID
            name: Song name
            artists: Artist names
            album_name: Album name (optional, helps with matching)
            duration: Duration in seconds (required for LRCLIB)

        Returns:
            List of all LyricsResult objects (one per successful provider)
        """
        providers = self._get_providers()

        if not providers:
            logger.warning("No lyrics providers configured")
            return []

        # Initialize all providers
        for provider in providers:
            await provider.__aenter__()

        results: list[LyricsResult] = []
        lyrics_repo = LyricsRepository(self.session)

        try:
            # Fetch from all providers concurrently
            tasks = [provider.get_lyrics(name, artists) for provider in providers]
            fetched = await asyncio.gather(*tasks, return_exceptions=True)

            for provider, result in zip(providers, fetched):
                if isinstance(result, Exception):
                    logger.debug(
                        "%s provider failed: %s",
                        provider.name,
                        result,
                    )
                    continue

                if result:
                    # Determine if synced
                    is_synced = isinstance(provider, SyncedLyricsProvider)
                    lyrics_synced = None
                    lyrics_text = result

                    if is_synced or self._is_lrc_format(result):
                        lyrics_synced = result
                        lyrics_text = self._lrc_to_plain(result)

                    # Calculate quality score
                    quality_score = self._calculate_quality_score(
                        lyrics_text=lyrics_text,
                        lyrics_synced=lyrics_synced,
                        source=provider.name.lower(),
                    )

                    # Calculate content hash for deduplication
                    content_hash = hashlib.sha256(
                        lyrics_text.encode("utf-8")
                    ).hexdigest()

                    # Count lines
                    line_count = len(
                        [line for line in lyrics_text.split("\n") if line.strip()]
                    )

                    # Save to database using repository
                    try:
                        await lyrics_repo.upsert(
                            song_id=song_id,
                            source=provider.name.lower(),
                            lyrics_text=lyrics_text,
                            lyrics_synced=lyrics_synced,
                            quality_score=quality_score,
                            line_count=line_count,
                            content_hash=content_hash,
                        )

                        logger.debug(
                            "Saved %s lyrics for song %s (quality=%.2f)",
                            provider.name,
                            song_id,
                            quality_score,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to save %s lyrics: %s", provider.name, e
                        )

                    results.append(
                        LyricsResult(
                            lyrics_text=lyrics_text,
                            lyrics_synced=lyrics_synced,
                            source=provider.name.lower(),
                            from_cache=False,
                        )
                    )

            return results

        finally:
            # Clean up providers
            for provider in providers:
                await provider.__aexit__(None, None, None)

    async def get_all_lyrics_for_song(
        self, song_id: uuid.UUID
    ) -> list[LyricsResult]:
        """
        Get ALL cached lyrics for a song from all sources.

        Args:
            song_id: Internal song UUID

        Returns:
            List of LyricsResult from all cached sources
        """
        lyrics_repo = LyricsRepository(self.session)
        all_lyrics = await lyrics_repo.get_all_for_song(song_id)

        return [
            LyricsResult(
                lyrics_text=lyrics.lyrics_text,
                lyrics_synced=lyrics.lyrics_synced,
                source=lyrics.source,
                from_cache=True,
            )
            for lyrics in all_lyrics
        ]

    def _calculate_quality_score(
        self,
        lyrics_text: str,
        lyrics_synced: str | None,
        source: str,
    ) -> float:
        """
        Calculate quality score based on lyrics completeness.

        Score factors:
        - Base score: 0.5
        - Synced lyrics: +0.3
        - Length (>100 chars): +0.1
        - Reliable source: +0.1

        Args:
            lyrics_text: Plain text lyrics
            lyrics_synced: LRC format synced lyrics (optional)
            source: Provider source name

        Returns:
            Quality score from 0.0 to 1.0
        """
        score = 0.5  # Base score

        # Synced lyrics are higher quality
        if lyrics_synced:
            score += 0.3

        # Longer lyrics are likely more complete
        if lyrics_text and len(lyrics_text) > 100:
            score += 0.1

        # Known reliable sources get a bonus
        reliable_sources = {"genius", "musixmatch", "synced"}
        if source.lower() in reliable_sources:
            score += 0.1

        return min(score, 1.0)


def get_lyrics_service(
    session: AsyncSession,
    genius_token: str | None = None,
    enable_cache: bool = True,
    lyrics_preferences: list[ProviderPreference] | None = None,
) -> LyricsService:
    """
    Factory function to create a LyricsService.

    Args:
        session: Database session
        genius_token: Optional Genius API token
        enable_cache: Whether to cache lyrics
        lyrics_preferences: User's lyrics source preferences

    Returns:
        Configured LyricsService instance
    """
    return LyricsService(
        session=session,
        genius_token=genius_token,
        enable_cache=enable_cache,
        lyrics_preferences=lyrics_preferences,
    )
