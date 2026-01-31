"""MusicBrainz metadata provider.

MusicBrainz is a free, open music encyclopedia that provides
comprehensive metadata for music recordings.

API Documentation: https://musicbrainz.org/doc/MusicBrainz_API
Rate Limit: 1 request per second (enforced by library)
Authentication: None required, just user-agent identification
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from spotdl_cli.providers.base import (
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
)

logger = logging.getLogger(__name__)


class MusicBrainzProvider(MetadataProvider):
    """
    MusicBrainz metadata provider.

    Uses the musicbrainzngs library to query MusicBrainz for
    track metadata, particularly useful for ISRC lookups.
    """

    name = "musicbrainz"
    display_name = "MusicBrainz"
    requests_per_second = 1.0

    def __init__(
        self,
        app_name: str = "spotdl-cli",
        app_version: str = "5.0.0",
        contact: str = "https://github.com/spotDL/spotify-downloader",
    ) -> None:
        """Initialize the MusicBrainz provider."""
        super().__init__()
        self._app_name = app_name
        self._app_version = app_version
        self._contact = contact
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        """Ensure musicbrainzngs is initialized with user-agent."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                import musicbrainzngs

                musicbrainzngs.set_useragent(
                    self._app_name,
                    self._app_version,
                    self._contact,
                )
                self._initialized = True
                logger.debug("MusicBrainz provider initialized")

            except ImportError as e:
                raise MetadataProviderError(
                    "musicbrainzngs library not installed. "
                    "Install with: pip install musicbrainzngs"
                ) from e

    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        """Look up metadata by ISRC code."""
        await self._ensure_initialized()

        try:
            import musicbrainzngs

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: musicbrainzngs.get_recordings_by_isrc(
                    isrc,
                    includes=["artists", "releases", "release-groups"],
                ),
            )

            recordings = result.get("isrc", {}).get("recording-list", [])
            if not recordings:
                return None

            recording = recordings[0]
            return self._parse_recording(recording, isrc=isrc)

        except Exception as e:
            logger.warning(f"MusicBrainz ISRC lookup failed for {isrc}: {e}")
            return None

    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        """Look up metadata by track name and artist."""
        await self._ensure_initialized()

        try:
            import musicbrainzngs

            # Build search query
            query_parts = [
                f'recording:"{track_name}"',
                f'artist:"{artist_name}"',
            ]
            if album_name:
                query_parts.append(f'release:"{album_name}"')

            query = " AND ".join(query_parts)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: musicbrainzngs.search_recordings(
                    query=query,
                    limit=5,
                ),
            )

            recordings = result.get("recording-list", [])
            if not recordings:
                return None

            recording = recordings[0]

            # Check score threshold
            score = int(recording.get("ext:score", 0))
            if score < 80:
                logger.debug(f"MusicBrainz match score too low: {score}")
                return None

            return self._parse_recording(recording)

        except Exception as e:
            logger.warning(
                f"MusicBrainz name lookup failed for {artist_name} - {track_name}: {e}"
            )
            return None

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MetadataResult]:
        """Search for tracks by query."""
        await self._ensure_initialized()

        try:
            import musicbrainzngs

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: musicbrainzngs.search_recordings(
                    query=query,
                    limit=limit,
                ),
            )

            recordings = result.get("recording-list", [])
            results = []

            for recording in recordings:
                try:
                    metadata = self._parse_recording(recording)
                    if metadata:
                        results.append(metadata)
                except Exception as e:
                    logger.debug(f"Failed to parse recording: {e}")
                    continue

            return results

        except Exception as e:
            logger.warning(f"MusicBrainz search failed for '{query}': {e}")
            return []

    async def get_cover_art(self, release_id: str) -> str | None:
        """Get cover art URL from Cover Art Archive."""
        await self._ensure_initialized()

        try:
            import musicbrainzngs

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: musicbrainzngs.get_image_list(release_id),
            )

            images = result.get("images", [])
            if not images:
                return None

            # Prefer front cover
            for image in images:
                if image.get("front"):
                    return image.get("image")

            return images[0].get("image") if images else None

        except Exception as e:
            logger.debug(f"Failed to get cover art for {release_id}: {e}")
            return None

    def _parse_recording(
        self,
        recording: dict[str, Any],
        isrc: str | None = None,
    ) -> MetadataResult | None:
        """Parse a MusicBrainz recording into MetadataResult."""
        try:
            name = recording.get("title")
            if not name:
                return None

            # Extract artists
            artists: list[str] = []
            artist_credit = recording.get("artist-credit", [])
            for credit in artist_credit:
                if isinstance(credit, dict):
                    artist = credit.get("artist", {})
                    artist_name = artist.get("name")
                    if artist_name:
                        artists.append(artist_name)

            # Extract release info
            album_name: str | None = None
            label: str | None = None
            country: str | None = None
            year: int | None = None
            date: str | None = None
            track_number: int | None = None
            disc_number: int | None = None
            total_tracks: int | None = None

            releases = recording.get("release-list", [])
            if releases:
                release = releases[0]
                album_name = release.get("title")
                country = release.get("country")

                # Parse date
                release_date = release.get("date", "")
                if release_date:
                    date = release_date
                    try:
                        year = int(release_date[:4])
                    except (ValueError, IndexError):
                        pass

                # Track info
                medium_list = release.get("medium-list", [])
                if medium_list:
                    medium = medium_list[0]
                    disc_number = medium.get("position")
                    track_list = medium.get("track-list", [])
                    if track_list:
                        track = track_list[0]
                        track_number = track.get("position")
                    total_tracks = medium.get("track-count")

                # Label info
                label_info = release.get("label-info-list", [])
                if label_info:
                    label_data = label_info[0].get("label", {})
                    label = label_data.get("name")

            # Extract duration
            duration_ms: int | None = None
            length = recording.get("length")
            if length:
                try:
                    duration_ms = int(length)
                except (ValueError, TypeError):
                    pass

            # Extract ISRC if not provided
            if not isrc:
                isrc_list = recording.get("isrc-list", [])
                if isrc_list:
                    isrc = isrc_list[0]

            # Extract genres from tags
            genres: list[str] = []
            tags = recording.get("tag-list", [])
            for tag in tags:
                tag_name = tag.get("name")
                if tag_name:
                    genres.append(tag_name)

            return MetadataResult(
                name=name,
                artists=artists if artists else None,
                album_name=album_name,
                isrc=isrc,
                musicbrainz_id=recording.get("id"),
                genres=genres,
                year=year,
                date=date,
                track_number=track_number,
                disc_number=disc_number,
                total_tracks=total_tracks,
                label=label,
                country=country,
                duration_ms=duration_ms,
                source="musicbrainz",
                confidence=0.9,
            )

        except Exception as e:
            logger.debug(f"Failed to parse MusicBrainz recording: {e}")
            return None
