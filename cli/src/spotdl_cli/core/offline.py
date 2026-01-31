"""Offline mode handler for CLI.

Provides local matching and URL resolution when backend is unavailable.
Uses yt-dlp for downloading, providers for searching and URL resolution,
and the matching engine for scoring.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import yt_dlp

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core.types import (
    DownloadResult,
    Platform,
    Song,
    TargetPlatform,
)
from spotdl_cli.matching import order_results
from spotdl_cli.matching.utils import create_search_query

logger = logging.getLogger(__name__)

# YouTube URL regex
YOUTUBE_URL_REGEX = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})"
)

# URL patterns for platform detection
URL_PATTERNS: dict[Platform, list[re.Pattern[str]]] = {
    Platform.SPOTIFY: [
        re.compile(
            r"https?://open\.spotify\.com/(?:intl-\w+/)?"
            r"(track|album|playlist|artist)/([a-zA-Z0-9]+)"
        ),
        re.compile(r"spotify:(track|album|playlist|artist):([a-zA-Z0-9]+)"),
    ],
    Platform.APPLE_MUSIC: [
        re.compile(
            r"https?://music\.apple\.com/\w+/(album|playlist|artist)/[^/]+/"
            r"([a-zA-Z0-9._-]+)"
        ),
    ],
    Platform.DEEZER: [
        re.compile(
            r"https?://(?:www\.)?deezer\.com/(?:\w+/)?(track|album|playlist|artist)/(\d+)"
        ),
        re.compile(r"deezer\.(page\.link|app\.link)/\w+"),
    ],
    Platform.TIDAL: [
        re.compile(
            r"https?://(?:www\.)?tidal\.com/(?:browse/)?"
            r"(track|album|playlist|artist)/(\d+)"
        ),
    ],
    Platform.YOUTUBE_MUSIC: [
        re.compile(r"https?://music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"),
        re.compile(r"https?://music\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"),
        re.compile(r"https?://music\.youtube\.com/channel/([a-zA-Z0-9_-]+)"),
    ],
    Platform.SOUNDCLOUD: [
        re.compile(r"https?://(?:www\.)?soundcloud\.com/([^/]+)/([^/]+)(?:/([^/]+))?"),
    ],
    Platform.BANDCAMP: [
        re.compile(r"https?://([^.]+)\.bandcamp\.com/(track|album)/([^/]+)"),
    ],
}


def detect_platform(url: str) -> Platform | None:
    """Detect the platform from a URL."""
    # Check for standard YouTube URLs
    if "youtube.com" in url or "youtu.be" in url:
        if "music.youtube.com" not in url:
            return Platform.YOUTUBE_MUSIC  # Use YTM for regular YouTube too

    for platform, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(url):
                return platform
    return None


def is_supported_url(url: str) -> bool:
    """Check if a URL is from a supported platform."""
    return detect_platform(url) is not None


class OfflineMatcher:
    """
    Local matching and URL resolution for offline mode.

    Uses providers to search and resolve URLs, and the matching
    engine to find the best result for a song.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the offline matcher."""
        self._settings = settings or get_settings()
        self._providers_initialized = False
        self._deezer_provider: Any = None
        self._ytm_source_provider: Any = None
        self._yt_target_provider: Any = None
        self._ytm_target_provider: Any = None
        self._soundcloud_target_provider: Any = None
        self._bandcamp_target_provider: Any = None
        self._musicbrainz_provider: Any = None

    def _init_providers(self) -> None:
        """Initialize providers lazily."""
        if self._providers_initialized:
            return

        from spotdl_cli.providers import (
            BandcampTargetProvider,
            DeezerProvider,
            MusicBrainzProvider,
            SoundCloudTargetProvider,
            YouTubeMusicSourceProvider,
            YouTubeMusicTargetProvider,
            YouTubeProvider,
        )

        self._deezer_provider = DeezerProvider()
        self._ytm_source_provider = YouTubeMusicSourceProvider()
        self._yt_target_provider = YouTubeProvider(
            cookies_path=(
                str(self._settings.cookies_path)
                if self._settings.cookies_path.exists()
                else None
            )
        )
        self._ytm_target_provider = YouTubeMusicTargetProvider()
        self._soundcloud_target_provider = SoundCloudTargetProvider()
        self._bandcamp_target_provider = BandcampTargetProvider()
        self._musicbrainz_provider = MusicBrainzProvider()
        self._providers_initialized = True

    def _get_yt_dlp_options(self) -> dict[str, Any]:
        """Get yt-dlp options for search."""
        options: dict[str, Any] = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "default_search": "ytsearch",
        }

        if self._settings.cookies_path.exists():
            options["cookiefile"] = str(self._settings.cookies_path)

        return options

    # ============== URL Resolution ==============

    async def resolve_url(self, url: str) -> list[Song]:
        """
        Resolve any supported URL to a list of songs.

        Args:
            url: URL to resolve (Deezer, YouTube Music, etc.)

        Returns:
            List of Song objects
        """
        platform = detect_platform(url)

        if platform is None:
            logger.warning(f"Unsupported URL: {url}")
            return []

        self._init_providers()

        try:
            if platform == Platform.DEEZER:
                return await self._resolve_deezer_url(url)
            elif platform == Platform.YOUTUBE_MUSIC:
                return await self._resolve_youtube_url(url)
            elif platform == Platform.SPOTIFY:
                logger.warning("Spotify URLs require API credentials")
                return []
            elif platform == Platform.APPLE_MUSIC:
                logger.warning("Apple Music URLs not yet supported offline")
                return []
            elif platform == Platform.TIDAL:
                logger.warning("Tidal URLs not yet supported offline")
                return []
            elif platform == Platform.SOUNDCLOUD:
                return await self._resolve_soundcloud_url(url)
            elif platform == Platform.BANDCAMP:
                return await self._resolve_bandcamp_url(url)
            else:
                logger.warning(f"Platform {platform} not yet supported")
                return []
        except Exception as e:
            logger.error(f"Failed to resolve URL {url}: {e}")
            return []

    async def _resolve_deezer_url(self, url: str) -> list[Song]:
        """Resolve a Deezer URL to songs."""
        songs = await self._deezer_provider.get_songs_from_url(url)
        return songs

    async def _resolve_youtube_url(self, url: str) -> list[Song]:
        """Resolve a YouTube/YouTube Music URL to songs."""
        options = self._get_yt_dlp_options()
        options["extract_flat"] = False

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._extract_info,
            url,
            options,
        )

        if not result:
            return []

        songs: list[Song] = []

        # Handle playlist
        if "entries" in result:
            for entry in result.get("entries", []):
                if entry:
                    song = self._yt_entry_to_song(entry)
                    if song:
                        songs.append(song)
        else:
            # Single video
            song = self._yt_entry_to_song(result)
            if song:
                songs.append(song)

        return songs

    async def _resolve_soundcloud_url(self, url: str) -> list[Song]:
        """Resolve a SoundCloud URL to songs."""
        result = await self._soundcloud_target_provider.get_track_info(url)
        if result:
            return [self._result_to_song(result)]
        return []

    async def _resolve_bandcamp_url(self, url: str) -> list[Song]:
        """Resolve a Bandcamp URL to songs."""
        result = await self._bandcamp_target_provider.get_track_info(url)
        if result:
            return [self._result_to_song(result)]
        return []

    def _yt_entry_to_song(self, entry: dict[str, Any]) -> Song | None:
        """Convert yt-dlp entry to Song object."""
        try:
            video_id = entry.get("id", "")
            title = entry.get("title", "")
            duration = entry.get("duration", 0) or 0
            channel = entry.get("channel", "") or entry.get("uploader", "") or "Unknown"

            if not video_id or not title:
                return None

            # Try to parse artist - title format
            artist = channel
            name = title
            if " - " in title:
                parts = title.split(" - ", 1)
                artist = parts[0].strip()
                name = parts[1].strip()

            return Song(
                name=name,
                artists=[artist],
                artist=artist,
                duration=int(duration),
                platform=Platform.YOUTUBE_MUSIC,
                platform_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                album_name=entry.get("album", ""),
                cover_url=entry.get("thumbnail"),
            )
        except Exception as e:
            logger.warning(f"Failed to convert entry to song: {e}")
            return None

    def _result_to_song(self, result: DownloadResult) -> Song:
        """Convert a DownloadResult to a Song."""
        # Map target platform to source platform
        platform_map = {
            TargetPlatform.YOUTUBE: Platform.YOUTUBE_MUSIC,
            TargetPlatform.YOUTUBE_MUSIC: Platform.YOUTUBE_MUSIC,
            TargetPlatform.SOUNDCLOUD: Platform.SOUNDCLOUD,
            TargetPlatform.BANDCAMP: Platform.BANDCAMP,
        }

        return Song(
            name=result.name,
            artists=result.artists,
            artist=result.artist,
            duration=result.duration,
            platform=platform_map.get(result.platform, Platform.YOUTUBE_MUSIC),
            platform_id=result.platform_id,
            url=result.url,
            album_name=result.album_name or "",
            cover_url=result.cover_url,
        )

    # ============== Search ==============

    async def search_all(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Song]:
        """
        Search across all available platforms.

        Args:
            query: Search query
            limit: Maximum results per platform

        Returns:
            List of Song objects from all platforms
        """
        self._init_providers()

        all_songs: list[Song] = []
        seen_ids: set[str] = set()

        # Search Deezer
        try:
            deezer_songs = await self._deezer_provider.search(query, limit)
            for song in deezer_songs:
                if song.platform_id not in seen_ids:
                    seen_ids.add(song.platform_id)
                    all_songs.append(song)
        except Exception as e:
            logger.warning(f"Deezer search failed: {e}")

        # Search YouTube Music
        try:
            ytm_songs = await self._ytm_source_provider.search(query, limit)
            for song in ytm_songs:
                if song.platform_id not in seen_ids:
                    seen_ids.add(song.platform_id)
                    all_songs.append(song)
        except Exception as e:
            logger.warning(f"YouTube Music search failed: {e}")

        # Search YouTube via yt-dlp
        try:
            yt_results = await self.search_youtube(query, limit)
            for result in yt_results:
                if result.platform_id not in seen_ids:
                    seen_ids.add(result.platform_id)
                    all_songs.append(self._result_to_song(result))
        except Exception as e:
            logger.warning(f"YouTube search failed: {e}")

        return all_songs[:limit * 2]  # Return more results from combined search

    async def search_youtube(
        self,
        query: str,
        limit: int = 10,
    ) -> list[DownloadResult]:
        """Search YouTube for videos matching a query."""
        options = self._get_yt_dlp_options()
        search_query = f"ytsearch{limit}:{query}"

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self._extract_info,
            search_query,
            options,
        )

        if not results:
            return []

        download_results = []
        entries = results.get("entries", [])

        for entry in entries:
            if not entry:
                continue

            result = self._entry_to_result(entry, TargetPlatform.YOUTUBE)
            if result:
                download_results.append(result)

        return download_results

    async def search_youtube_music(
        self,
        query: str,
        limit: int = 10,
    ) -> list[DownloadResult]:
        """Search YouTube Music for tracks."""
        options = self._get_yt_dlp_options()
        search_query = f"https://music.youtube.com/search?q={query}"

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self._extract_info,
            search_query,
            options,
        )

        if not results:
            return await self.search_youtube(query, limit)

        download_results = []
        entries = results.get("entries", [])[:limit]

        for entry in entries:
            if not entry:
                continue

            result = self._entry_to_result(entry, TargetPlatform.YOUTUBE_MUSIC)
            if result:
                download_results.append(result)

        return download_results

    def _extract_info(self, url: str, options: dict[str, Any]) -> dict[str, Any] | None:
        """Extract info using yt-dlp (blocking)."""
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"yt-dlp extraction error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}")
            return None

    def _entry_to_result(
        self,
        entry: dict[str, Any],
        platform: TargetPlatform,
    ) -> DownloadResult | None:
        """Convert yt-dlp entry to DownloadResult."""
        try:
            video_id = entry.get("id", "")
            title = entry.get("title", "")
            duration = entry.get("duration", 0) or 0

            if not video_id or not title:
                return None

            channel = entry.get("channel", "") or entry.get("uploader", "") or ""
            artists = [channel] if channel else []

            if platform == TargetPlatform.YOUTUBE_MUSIC:
                url = f"https://music.youtube.com/watch?v={video_id}"
            else:
                url = f"https://www.youtube.com/watch?v={video_id}"

            is_verified = entry.get("channel_is_verified", False)
            album_name = entry.get("album", None)

            return DownloadResult(
                name=title,
                artists=artists,
                artist=channel,
                duration=int(duration),
                platform=platform,
                platform_id=video_id,
                url=url,
                verified=is_verified,
                album_name=album_name,
                views=entry.get("view_count"),
                cover_url=entry.get("thumbnail"),
            )

        except Exception as e:
            logger.warning(f"Failed to convert entry to result: {e}")
            return None

    # ============== Matching ==============

    async def find_matches(
        self,
        song: Song,
        platforms: list[TargetPlatform] | None = None,
        limit: int = 5,
    ) -> list[DownloadResult]:
        """Find matching results for a song across all target platforms."""
        if platforms is None:
            platforms = [
                TargetPlatform.YOUTUBE,
                TargetPlatform.YOUTUBE_MUSIC,
                TargetPlatform.SOUNDCLOUD,
                TargetPlatform.BANDCAMP,
            ]

        self._init_providers()
        all_results: list[DownloadResult] = []

        full_query = create_search_query(song.name, song.artists)

        for platform in platforms:
            try:
                if platform == TargetPlatform.YOUTUBE_MUSIC:
                    results = await self._ytm_target_provider.search(song, limit)
                elif platform == TargetPlatform.YOUTUBE:
                    results = await self._yt_target_provider.search(song, limit)
                elif platform == TargetPlatform.SOUNDCLOUD:
                    results = await self._soundcloud_target_provider.search(song, limit)
                elif platform == TargetPlatform.BANDCAMP:
                    results = await self._bandcamp_target_provider.search(song, limit)
                else:
                    continue

                all_results.extend(results)

            except Exception as e:
                logger.warning(f"Search failed for {platform}: {e}")

        if not all_results:
            return []

        # Score and rank results using the matching engine
        scored = order_results(all_results, song, full_query)

        # Sort by score descending
        sorted_results = sorted(scored.items(), key=lambda x: x[1], reverse=True)

        # Add score to results and return
        matched_results = []
        for result, score in sorted_results[:limit]:
            result.score = score
            matched_results.append(result)

        return matched_results

    async def get_best_match(
        self,
        song: Song,
        min_score: float = 80.0,
    ) -> DownloadResult | None:
        """Get the single best match for a song."""
        matches = await self.find_matches(song)

        if not matches:
            return None

        best = matches[0]
        if best.score < min_score:
            logger.debug(f"Best match score {best.score} below threshold {min_score}")
            return None

        return best

    # ============== Metadata Enrichment ==============

    async def enrich_song(self, song: Song) -> Song:
        """Enrich a song with metadata from MusicBrainz."""
        self._init_providers()

        try:
            return await self._musicbrainz_provider.enrich_song(song)
        except Exception as e:
            logger.warning(f"Failed to enrich song: {e}")
            return song

    # ============== Cleanup ==============

    async def close(self) -> None:
        """Close all provider connections."""
        if self._deezer_provider:
            await self._deezer_provider.close()
        if self._yt_target_provider:
            await self._yt_target_provider.close()
        if self._soundcloud_target_provider:
            await self._soundcloud_target_provider.close()
        if self._bandcamp_target_provider:
            await self._bandcamp_target_provider.close()


# Global instance
_offline_matcher: OfflineMatcher | None = None


def get_offline_matcher() -> OfflineMatcher:
    """Get the global offline matcher instance."""
    global _offline_matcher
    if _offline_matcher is None:
        _offline_matcher = OfflineMatcher()
    return _offline_matcher
