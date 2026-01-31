"""Metadata service for enriching song information."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from spotdl.providers.metadata import (
    DiscogsProvider,
    MetadataProvider,
    MusicBrainzProvider,
)

if TYPE_CHECKING:
    from spotdl.core.types.song import Song

logger = logging.getLogger(__name__)


class MetadataServiceError(Exception):
    """Base exception for metadata service errors."""


class MetadataService:
    """
    Service for enriching songs with additional metadata.

    Uses multiple metadata providers (MusicBrainz, Discogs) to
    fill in missing information like ISRC, genres, year, etc.

    All providers used are FREE and require no API costs:
    - MusicBrainz: No auth required, rate limited to 1 req/sec
    - Discogs: Works unauthenticated (25 req/min) or with free user-token (60 req/min)
    """

    def __init__(
        self,
        enable_musicbrainz: bool = True,
        enable_discogs: bool = True,
        discogs_user_token: str | None = None,
    ) -> None:
        """
        Initialize the metadata service.

        Args:
            enable_musicbrainz: Enable MusicBrainz lookups
            enable_discogs: Enable Discogs lookups
            discogs_user_token: Optional Discogs user token for higher rate limits
        """
        self._providers: list[MetadataProvider] = []

        # Initialize providers in order of preference
        # MusicBrainz first (best for ISRC lookups)
        if enable_musicbrainz:
            try:
                self._providers.append(MusicBrainzProvider())
                logger.debug("MusicBrainz provider enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize MusicBrainz provider: {e}")

        # Discogs second (good for genres, labels)
        if enable_discogs:
            try:
                self._providers.append(DiscogsProvider(user_token=discogs_user_token))
                logger.debug(
                    f"Discogs provider enabled "
                    f"(authenticated: {discogs_user_token is not None})"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Discogs provider: {e}")

    @property
    def providers(self) -> list[MetadataProvider]:
        """Get list of active providers."""
        return self._providers

    @property
    def provider_names(self) -> list[str]:
        """Get names of active providers."""
        return [p.name for p in self._providers]

    async def enrich_song(
        self,
        song: Song,
        use_all_providers: bool = False,
    ) -> Song:
        """
        Enrich a song with additional metadata.

        By default, stops after the first provider returns results.
        Set use_all_providers=True to query all providers and merge results.

        Args:
            song: Song to enrich
            use_all_providers: Whether to query all providers

        Returns:
            Enriched Song object (same instance, modified in place)
        """
        if not self._providers:
            return song

        for provider in self._providers:
            try:
                await provider.enrich_song(song)

                # If we got useful data and not using all providers, stop
                if not use_all_providers and (song.isrc or song.album_name):
                    break

            except Exception as e:
                logger.debug(f"Provider {provider.name} failed to enrich song: {e}")
                continue

        return song

    async def enrich_songs(
        self,
        songs: list[Song],
        use_all_providers: bool = False,
        max_concurrent: int = 5,
    ) -> list[Song]:
        """
        Enrich multiple songs with additional metadata.

        Uses semaphore to limit concurrent requests and respect rate limits.

        Args:
            songs: Songs to enrich
            use_all_providers: Whether to query all providers for each song
            max_concurrent: Maximum concurrent enrichment operations

        Returns:
            List of enriched Song objects
        """
        if not self._providers or not songs:
            return songs

        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_limit(song: Song) -> Song:
            async with semaphore:
                return await self.enrich_song(song, use_all_providers)

        # Process songs concurrently with rate limiting
        tasks = [enrich_with_limit(song) for song in songs]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successfully enriched songs
        result = []
        for i, item in enumerate(enriched):
            if isinstance(item, Exception):
                logger.debug(f"Failed to enrich song {songs[i].name}: {item}")
                result.append(songs[i])  # Return original song on failure
            else:
                result.append(item)

        return result

    async def lookup_by_isrc(self, isrc: str) -> dict | None:
        """
        Look up metadata by ISRC code.

        Queries all providers and returns combined results.

        Args:
            isrc: ISRC code

        Returns:
            Combined metadata dict or None if not found
        """
        for provider in self._providers:
            try:
                result = await provider.lookup_by_isrc(isrc)
                if result:
                    return {
                        "source": provider.name,
                        "name": result.name,
                        "artists": result.artists,
                        "album_name": result.album_name,
                        "isrc": result.isrc,
                        "genres": result.genres,
                        "year": result.year,
                        "confidence": result.confidence,
                    }
            except Exception as e:
                logger.debug(f"ISRC lookup failed on {provider.name}: {e}")
                continue

        return None

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search for tracks across all providers.

        Args:
            query: Search query
            limit: Maximum results per provider

        Returns:
            List of metadata dicts from all providers
        """
        results = []

        for provider in self._providers:
            try:
                provider_results = await provider.search(query, limit=limit)
                for result in provider_results:
                    results.append({
                        "source": provider.name,
                        "name": result.name,
                        "artists": result.artists,
                        "album_name": result.album_name,
                        "genres": result.genres,
                        "year": result.year,
                        "confidence": result.confidence,
                    })
            except Exception as e:
                logger.debug(f"Search failed on {provider.name}: {e}")
                continue

        return results

    async def close(self) -> None:
        """Close all providers."""
        for provider in self._providers:
            try:
                await provider.close()
            except Exception as e:
                logger.debug(f"Failed to close provider {provider.name}: {e}")


# Global service instance
_metadata_service: MetadataService | None = None


def get_metadata_service(
    enable_musicbrainz: bool = True,
    enable_discogs: bool = True,
    discogs_user_token: str | None = None,
) -> MetadataService:
    """
    Get the global metadata service instance.

    Args:
        enable_musicbrainz: Enable MusicBrainz lookups
        enable_discogs: Enable Discogs lookups
        discogs_user_token: Optional Discogs user token

    Returns:
        MetadataService instance
    """
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService(
            enable_musicbrainz=enable_musicbrainz,
            enable_discogs=enable_discogs,
            discogs_user_token=discogs_user_token,
        )
    return _metadata_service
