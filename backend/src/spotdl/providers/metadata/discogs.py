"""Discogs metadata provider.

Discogs is a crowd-sourced database of music releases with
detailed metadata including release information, labels, and genres.

API Documentation: https://www.discogs.com/developers
Rate Limits:
- Unauthenticated: 25 requests/minute
- Authenticated (user-token): 60 requests/minute

Authentication: Optional user-token (recommended for higher rate limits)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from spotdl.providers.metadata.base import (
    MetadataProvider,
    MetadataProviderError,
    MetadataResult,
)

logger = logging.getLogger(__name__)


class DiscogsProvider(MetadataProvider):
    """
    Discogs metadata provider.

    Uses the python3-discogs-client library to query Discogs for
    release metadata, particularly useful for vinyl/physical release info.

    Features:
    - Detailed release information
    - Genre and style tags
    - Label information
    - Cover art
    - Optional authentication for higher rate limits

    Note: Works unauthenticated (25 req/min) or with user-token (60 req/min).
    User-token is easy to obtain from Discogs settings.
    """

    name = "discogs"
    display_name = "Discogs"
    requests_per_second = 0.4  # 25 per minute = ~0.4/sec (conservative)

    def __init__(
        self,
        user_token: str | None = None,
        user_agent: str = "spotdl/5.0.0 +https://github.com/spotDL/spotify-downloader",
    ) -> None:
        """
        Initialize the Discogs provider.

        Args:
            user_token: Optional Discogs user token for higher rate limits.
                       Get one from https://www.discogs.com/settings/developers
            user_agent: User agent string for API requests
        """
        super().__init__()
        self._user_token = user_token
        self._user_agent = user_agent
        self._client: Any | None = None
        self._lock = asyncio.Lock()

        # Higher rate limit if authenticated
        if user_token:
            self.requests_per_second = 1.0  # 60 per minute

    async def _ensure_client(self) -> Any:
        """Ensure Discogs client is initialized."""
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client

            try:
                import discogs_client

                self._client = discogs_client.Client(
                    self._user_agent,
                    user_token=self._user_token,
                )
                logger.debug(
                    f"Discogs provider initialized "
                    f"(authenticated: {self._user_token is not None})"
                )
                return self._client

            except ImportError as e:
                raise MetadataProviderError(
                    "python3-discogs-client library not installed. "
                    "Install with: pip install python3-discogs-client"
                ) from e

    async def lookup_by_isrc(self, isrc: str) -> MetadataResult | None:
        """
        Look up metadata by ISRC code.

        Note: Discogs doesn't directly support ISRC lookup,
        so this falls back to search.

        Args:
            isrc: ISRC code

        Returns:
            MetadataResult if found, None otherwise
        """
        # Discogs doesn't support ISRC directly
        # Could potentially search by barcode/catalog number
        logger.debug(f"Discogs doesn't support ISRC lookup, skipping: {isrc}")
        return None

    async def lookup_by_name(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> MetadataResult | None:
        """
        Look up metadata by track name and artist.

        Args:
            track_name: Track name
            artist_name: Artist name
            album_name: Optional album name for better matching

        Returns:
            MetadataResult if found, None otherwise
        """
        _, result = await self._lookup_by_name_with_raw(track_name, artist_name, album_name)
        return result

    async def _lookup_by_name_with_raw(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
    ) -> tuple[dict[str, Any] | None, MetadataResult | None]:
        """
        Look up metadata by name and return both raw response and parsed result.

        Args:
            track_name: Track name
            artist_name: Artist name
            album_name: Optional album name

        Returns:
            Tuple of (raw_response, MetadataResult)
        """
        client = await self._ensure_client()

        try:
            # Build search query
            query = f"{artist_name} {track_name}"
            if album_name:
                query = f"{artist_name} {album_name}"

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: client.search(query, type="release"),
            )

            # Get first few results
            releases = []
            for i, result in enumerate(results):
                if i >= 5:
                    break
                releases.append(result)

            if not releases:
                return None, None

            # Find best match
            best_match = None
            best_score: float = 0.0

            for release in releases:
                score = self._calculate_match_score(
                    release, track_name, artist_name, album_name
                )
                if score > best_score:
                    best_score = score
                    best_match = release

            if best_match and best_score >= 50:
                # Extract raw data from the release object
                raw_response = self._extract_raw_response(best_match)
                parsed_result = await self._parse_release(best_match, track_name)
                return raw_response, parsed_result

            return None, None

        except Exception as e:
            logger.warning(
                f"Discogs lookup failed for {artist_name} - {track_name}: {e}"
            )
            return None, None

    async def lookup_with_raw(
        self,
        isrc: str | None = None,
        name: str | None = None,
        artist: str | None = None,
        album_name: str | None = None,
    ) -> tuple[dict[str, Any] | None, MetadataResult | None]:
        """
        Look up metadata and return both raw API response AND parsed result.

        Note: Discogs doesn't support ISRC lookup, so it only uses name/artist.

        Args:
            isrc: ISRC code (ignored - Discogs doesn't support ISRC)
            name: Track name
            artist: Artist name
            album_name: Album name (optional)

        Returns:
            Tuple of (raw_response, MetadataResult)
        """
        # Discogs doesn't support ISRC lookup
        if name and artist:
            return await self._lookup_by_name_with_raw(name, artist, album_name)

        return None, None

    def _extract_raw_response(self, release: Any) -> dict[str, Any]:
        """
        Extract raw data from a Discogs release object.

        Args:
            release: Discogs release object

        Returns:
            Dictionary with raw release data
        """
        raw: dict[str, Any] = {
            "id": getattr(release, "id", None),
            "title": getattr(release, "title", None),
            "year": getattr(release, "year", None),
            "country": getattr(release, "country", None),
        }

        # Artists
        artists_attr = getattr(release, "artists", None)
        if artists_attr:
            raw["artists"] = [
                {
                    "id": getattr(a, "id", None),
                    "name": getattr(a, "name", None),
                }
                for a in artists_attr
            ]

        # Genres and styles
        raw["genres"] = getattr(release, "genres", None)
        raw["styles"] = getattr(release, "styles", None)

        # Labels
        labels_attr = getattr(release, "labels", None)
        if labels_attr:
            raw["labels"] = [
                {
                    "id": getattr(l, "id", None),
                    "name": getattr(l, "name", None),
                    "catno": getattr(l, "catno", None),
                }
                for l in labels_attr
            ]

        # Tracklist
        tracklist = getattr(release, "tracklist", None)
        if tracklist:
            raw["tracklist"] = [
                {
                    "position": getattr(t, "position", None),
                    "title": getattr(t, "title", None),
                    "duration": getattr(t, "duration", None),
                }
                for t in tracklist
            ]

        # Formats
        formats = getattr(release, "formats", None)
        if formats:
            raw["formats"] = [
                {
                    "name": getattr(f, "name", None),
                    "qty": getattr(f, "qty", None),
                    "descriptions": getattr(f, "descriptions", None),
                }
                for f in formats
            ]

        # Images
        images = getattr(release, "images", None)
        if images:
            raw["images"] = [
                {
                    "type": getattr(i, "type", None),
                    "uri": getattr(i, "uri", None),
                    "width": getattr(i, "width", None),
                    "height": getattr(i, "height", None),
                }
                for i in images
            ]

        # Master release info
        raw["master_id"] = getattr(release, "master_id", None)
        raw["data_quality"] = getattr(release, "data_quality", None)

        return raw

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MetadataResult]:
        """
        Search for releases by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of MetadataResult objects
        """
        client = await self._ensure_client()

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: client.search(query, type="release"),
            )

            metadata_results = []
            for i, release in enumerate(results):
                if i >= limit:
                    break

                try:
                    result = await self._parse_release(release)
                    if result:
                        metadata_results.append(result)
                except Exception as e:
                    logger.debug(f"Failed to parse Discogs release: {e}")
                    continue

            return metadata_results

        except Exception as e:
            logger.warning(f"Discogs search failed for '{query}': {e}")
            return []

    async def lookup_release(self, release_id: int) -> MetadataResult | None:
        """
        Look up a specific release by Discogs ID.

        Args:
            release_id: Discogs release ID

        Returns:
            MetadataResult if found, None otherwise
        """
        client = await self._ensure_client()

        try:
            loop = asyncio.get_event_loop()
            release = await loop.run_in_executor(
                None,
                lambda: client.release(release_id),
            )

            return await self._parse_release(release)

        except Exception as e:
            logger.warning(f"Discogs release lookup failed for {release_id}: {e}")
            return None

    def _calculate_match_score(
        self,
        release: Any,
        track_name: str,
        artist_name: str,
        album_name: str | None,
    ) -> float:
        """
        Calculate a match score for a release.

        Args:
            release: Discogs release object
            track_name: Expected track name
            artist_name: Expected artist name
            album_name: Expected album name

        Returns:
            Score from 0-100
        """
        try:
            score = 0.0

            # Get release info
            release_title = getattr(release, "title", "") or ""
            release_artists = []

            artists_attr = getattr(release, "artists", None)
            if artists_attr:
                for artist in artists_attr:
                    name = getattr(artist, "name", None)
                    if name:
                        release_artists.append(name.lower())

            # Artist match (40 points)
            artist_lower = artist_name.lower()
            for r_artist in release_artists:
                if artist_lower in r_artist or r_artist in artist_lower:
                    score += 40
                    break

            # Album match (30 points)
            if album_name:
                album_lower = album_name.lower()
                title_lower = release_title.lower()
                if album_lower in title_lower or title_lower in album_lower:
                    score += 30

            # Track presence (30 points)
            tracklist = getattr(release, "tracklist", []) or []
            track_lower = track_name.lower()
            for track in tracklist:
                track_title = getattr(track, "title", "") or ""
                if track_lower in track_title.lower():
                    score += 30
                    break

            return score

        except Exception:
            return 0.0

    async def _parse_release(
        self,
        release: Any,
        track_name: str | None = None,
    ) -> MetadataResult | None:
        """
        Parse a Discogs release into MetadataResult.

        Args:
            release: Discogs release object
            track_name: Optional track name to find specific track info

        Returns:
            MetadataResult or None
        """
        try:
            # Get basic release info
            title = getattr(release, "title", None)
            if not title:
                return None

            # Get artists
            artists: list[str] = []
            artists_attr = getattr(release, "artists", None)
            if artists_attr:
                for artist in artists_attr:
                    name = getattr(artist, "name", None)
                    if name:
                        # Clean up Discogs artist name format
                        # (removes trailing numbers like "Artist (2)")
                        clean_name = name.split(" (")[0].strip()
                        artists.append(clean_name)

            # Get year
            year = getattr(release, "year", None)
            if year:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None

            # Get genres and styles
            genres: list[str] = []

            release_genres = getattr(release, "genres", None)
            if release_genres:
                genres.extend(release_genres)

            release_styles = getattr(release, "styles", None)
            if release_styles:
                genres.extend(release_styles)

            # Get labels
            label: str | None = None
            labels = getattr(release, "labels", None)
            if labels:
                first_label = labels[0] if labels else None
                if first_label:
                    label = getattr(first_label, "name", None)

            # Get country
            country = getattr(release, "country", None)

            # Get cover art
            images = getattr(release, "images", None)
            album_art_url: str | None = None
            if images:
                # Prefer primary image
                for img in images:
                    if getattr(img, "type", "") == "primary":
                        album_art_url = getattr(img, "uri", None)
                        break
                if not album_art_url and images:
                    album_art_url = getattr(images[0], "uri", None)

            # Get track info if track_name provided
            track_number: int | None = None
            name = title  # Default to album name

            if track_name:
                tracklist = getattr(release, "tracklist", []) or []
                track_lower = track_name.lower()

                for i, track in enumerate(tracklist):
                    track_title = getattr(track, "title", "") or ""
                    if track_lower in track_title.lower():
                        name = track_title
                        position = getattr(track, "position", "")
                        try:
                            # Handle positions like "A1", "B2", "1", "2"
                            pos_str = "".join(c for c in str(position) if c.isdigit())
                            if pos_str:
                                track_number = int(pos_str)
                        except (ValueError, TypeError):
                            track_number = i + 1
                        break

            # Get Discogs ID
            discogs_id = str(getattr(release, "id", ""))

            return MetadataResult(
                name=name,
                artists=artists if artists else None,
                album_name=title,
                discogs_id=discogs_id,
                genres=genres,
                year=year,
                track_number=track_number,
                album_art_url=album_art_url,
                label=label,
                country=country,
                source="discogs",
                confidence=0.8,
            )

        except Exception as e:
            logger.debug(f"Failed to parse Discogs release: {e}")
            return None

    async def close(self) -> None:
        """Close the Discogs client."""
        self._client = None
