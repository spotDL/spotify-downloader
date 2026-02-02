"""Metadata service for enriching song information."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.provider_preferences import get_enabled_metadata_provider_ids
from spotdl.core.providers_config import ProviderPreference
from spotdl.db.repositories import MetadataSnapshotRepository
from spotdl.providers.metadata import (
    DiscogsProvider,
    MetadataProvider,
    MusicBrainzProvider,
)

if TYPE_CHECKING:
    from spotdl.core.types.song import Song
    from spotdl.db.models.metadata_snapshot import MetadataSnapshot

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
        metadata_preferences: list[ProviderPreference] | None = None,
    ) -> None:
        """
        Initialize the metadata service.

        Args:
            enable_musicbrainz: Enable MusicBrainz lookups (ignored if metadata_preferences provided)
            enable_discogs: Enable Discogs lookups (ignored if metadata_preferences provided)
            discogs_user_token: Optional Discogs user token for higher rate limits
            metadata_preferences: User's metadata source preferences (ordered list with enabled status).
                                If provided, overrides enable_musicbrainz and enable_discogs.
        """
        self._providers: list[MetadataProvider] = []

        # If preferences are provided, use them to determine providers and order
        if metadata_preferences is not None:
            prefs = get_enabled_metadata_provider_ids(metadata_preferences)
            enable_musicbrainz = prefs["enable_musicbrainz"]
            enable_discogs = prefs["enable_discogs"]

            # Initialize providers in user-specified order
            self._init_providers_from_preferences(
                prefs["provider_ids"],
                discogs_user_token,
            )
        else:
            # Legacy initialization: MusicBrainz first, then Discogs
            if enable_musicbrainz:
                try:
                    self._providers.append(MusicBrainzProvider())
                    logger.debug("MusicBrainz provider enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize MusicBrainz provider: {e}")

            if enable_discogs:
                try:
                    self._providers.append(DiscogsProvider(user_token=discogs_user_token))
                    logger.debug(
                        f"Discogs provider enabled "
                        f"(authenticated: {discogs_user_token is not None})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize Discogs provider: {e}")

    def _init_providers_from_preferences(
        self,
        provider_ids: list[str],
        discogs_user_token: str | None = None,
    ) -> None:
        """
        Initialize providers based on user-specified order.

        Args:
            provider_ids: Ordered list of enabled provider IDs
            discogs_user_token: Optional Discogs user token
        """
        for provider_id in provider_ids:
            if provider_id == "musicbrainz":
                try:
                    self._providers.append(MusicBrainzProvider())
                    logger.debug("MusicBrainz provider enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize MusicBrainz provider: {e}")
            elif provider_id == "discogs":
                try:
                    self._providers.append(DiscogsProvider(user_token=discogs_user_token))
                    logger.debug(
                        f"Discogs provider enabled "
                        f"(authenticated: {discogs_user_token is not None})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize Discogs provider: {e}")
            # Note: "spotify" is not a metadata enrichment provider
            # It's the source platform, not a metadata lookup service

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

    async def enrich_song_with_snapshots(
        self,
        song: Song,
        song_id: uuid.UUID,
        session: AsyncSession,
    ) -> tuple[Song, list[MetadataSnapshot]]:
        """
        Enrich a song from ALL providers and save COMPLETE snapshots.

        This method queries all available metadata providers, stores both
        raw API responses and normalized data as MetadataSnapshots, and
        enriches the song object.

        Args:
            song: Song DTO to enrich
            song_id: Database ID of the song (UUID)
            session: Database session for saving snapshots

        Returns:
            Tuple of (enriched Song, list of created MetadataSnapshots)
        """
        snapshots: list[MetadataSnapshot] = []

        if not self._providers:
            return song, snapshots

        snapshot_repo = MetadataSnapshotRepository(session)

        for provider in self._providers:
            try:
                # Get raw response AND parsed result
                raw_response, result = await provider.lookup_with_raw(
                    isrc=song.isrc,
                    name=song.name,
                    artist=song.artist,
                    album_name=song.album_name,
                )

                if result:
                    # Save BOTH raw and normalized data
                    snapshot = await snapshot_repo.upsert(
                        song_id=song_id,
                        source=provider.name,
                        raw_response=raw_response,
                        snapshot_data=result.to_dict(),
                        confidence=result.confidence,
                    )
                    snapshots.append(snapshot)

                    # Merge result into song
                    provider._merge_metadata(song, result)

                    logger.debug(
                        f"Saved {provider.name} snapshot for song {song_id}"
                    )

            except Exception as e:
                logger.debug(f"Provider {provider.name} failed: {e}")
                continue

        return song, snapshots

    async def fetch_all_snapshots(
        self,
        song_id: uuid.UUID,
        isrc: str | None,
        name: str,
        artist: str,
        album_name: str | None,
        session: AsyncSession,
    ) -> list[MetadataSnapshot]:
        """
        Fetch metadata from ALL providers and save snapshots without a Song DTO.

        This is useful when you only have the song's attributes (from DB model)
        but not a Song DTO object.

        Args:
            song_id: Database ID of the song (UUID)
            isrc: ISRC code (optional)
            name: Track name
            artist: Artist name
            album_name: Album name (optional)
            session: Database session for saving snapshots

        Returns:
            List of created MetadataSnapshots
        """
        snapshots: list[MetadataSnapshot] = []

        if not self._providers:
            return snapshots

        snapshot_repo = MetadataSnapshotRepository(session)

        for provider in self._providers:
            try:
                # Get raw response AND parsed result
                raw_response, result = await provider.lookup_with_raw(
                    isrc=isrc,
                    name=name,
                    artist=artist,
                    album_name=album_name,
                )

                if result:
                    # Save BOTH raw and normalized data
                    snapshot = await snapshot_repo.upsert(
                        song_id=song_id,
                        source=provider.name,
                        raw_response=raw_response,
                        snapshot_data=result.to_dict(),
                        confidence=result.confidence,
                    )
                    snapshots.append(snapshot)

                    logger.debug(
                        f"Saved {provider.name} snapshot for song {song_id}"
                    )

            except Exception as e:
                logger.debug(f"Provider {provider.name} failed: {e}")
                continue

        return snapshots

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


# Global service instance (for default preferences)
_metadata_service: MetadataService | None = None


def get_metadata_service(
    enable_musicbrainz: bool = True,
    enable_discogs: bool = True,
    discogs_user_token: str | None = None,
    metadata_preferences: list[ProviderPreference] | None = None,
) -> MetadataService:
    """
    Get a metadata service instance.

    If metadata_preferences is provided, creates a new service with those preferences.
    Otherwise returns the global service with default settings.

    Args:
        enable_musicbrainz: Enable MusicBrainz lookups (ignored if preferences provided)
        enable_discogs: Enable Discogs lookups (ignored if preferences provided)
        discogs_user_token: Optional Discogs user token
        metadata_preferences: User's metadata source preferences

    Returns:
        MetadataService instance configured with the specified preferences
    """
    global _metadata_service

    # If preferences are provided, always create a new service with those preferences
    if metadata_preferences is not None:
        return MetadataService(
            metadata_preferences=metadata_preferences,
            discogs_user_token=discogs_user_token,
        )

    # Otherwise use/create the global default service
    if _metadata_service is None:
        _metadata_service = MetadataService(
            enable_musicbrainz=enable_musicbrainz,
            enable_discogs=enable_discogs,
            discogs_user_token=discogs_user_token,
        )
    return _metadata_service
