"""Offline mode handler for CLI.

Provides local matching and URL resolution when backend is unavailable.
Uses yt-dlp for downloading, spotdl_core providers for searching and URL resolution,
and the matching engine for scoring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import yt_dlp

# Import from spotdl_core (shared library)
from spotdl_core import (
    Platform,
    Result,
    Song,
    TargetPlatform,
    order_results,
)
from spotdl_core.matching.utils import create_search_query
from spotdl_core.providers.sources import detect_platform, is_valid_url

from spotdl_cli.config import Settings, get_settings

if TYPE_CHECKING:
    from spotdl_core import (
        DeezerProvider,
        MusicBrainzProvider,
        SpotifyProvider,
        YouTubeMusicProvider,
    )
    from spotdl_core.providers.targets import (
        BandcampProvider,
        SoundCloudProvider,
        YouTubeProvider,
    )
    from spotdl_core.providers.targets import (
        YouTubeMusicProvider as YouTubeMusicTargetProvider,
    )

logger = logging.getLogger(__name__)


class OfflineMatcher:
    """
    Local matching and URL resolution for offline mode.

    Uses spotdl_core providers to search and resolve URLs, and the matching
    engine to find the best result for a song.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the offline matcher."""
        self._settings = settings or get_settings()
        self._providers_initialized = False

        # Source providers
        self._deezer_provider: DeezerProvider | None = None
        self._ytm_source_provider: YouTubeMusicProvider | None = None
        self._spotify_provider: SpotifyProvider | None = None

        # Target providers
        self._yt_target_provider: YouTubeProvider | None = None
        self._ytm_target_provider: YouTubeMusicTargetProvider | None = None
        self._soundcloud_target_provider: SoundCloudProvider | None = None
        self._bandcamp_target_provider: BandcampProvider | None = None

        # Metadata providers
        self._musicbrainz_provider: MusicBrainzProvider | None = None

    def _init_providers(self) -> None:
        """Initialize providers lazily."""
        if self._providers_initialized:
            return

        from spotdl_core import (
            BandcampTargetProvider,
            DeezerProvider,
            MusicBrainzProvider,
            SoundCloudTargetProvider,
            SpotifyProvider,
            YouTubeMusicTargetProvider,
            YouTubeProvider,
        )
        from spotdl_core.providers.sources import YouTubeMusicProvider

        # Source providers
        self._deezer_provider = DeezerProvider()
        self._ytm_source_provider = YouTubeMusicProvider()

        # Initialize Spotify if credentials are configured
        if self._settings.spotify_client_id and self._settings.spotify_client_secret:
            try:
                self._spotify_provider = SpotifyProvider(
                    client_id=self._settings.spotify_client_id,
                    client_secret=self._settings.spotify_client_secret,
                    user_auth=self._settings.spotify_user_auth,
                )
                logger.info("Spotify provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Spotify provider: {e}")
                self._spotify_provider = None

        # Target providers
        self._yt_target_provider = YouTubeProvider()
        self._ytm_target_provider = YouTubeMusicTargetProvider()
        self._soundcloud_target_provider = SoundCloudTargetProvider()
        self._bandcamp_target_provider = BandcampTargetProvider()

        # Metadata providers
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

    def _normalize_provider_id(self, provider_id: str) -> str:
        """Normalize provider IDs to TargetPlatform naming."""
        return provider_id.strip().lower().replace("-", "_")

    def _get_target_platforms(self) -> list[TargetPlatform]:
        """Resolve target platforms from settings preferences."""
        provider_ids: list[str] = []
        prefs = getattr(self._settings, "audio_source_preferences", None)
        if prefs:
            provider_ids = [
                p.get("id", "")
                for p in prefs
                if p and p.get("enabled", True)
            ]
        elif self._settings.audio_providers:
            provider_ids = list(self._settings.audio_providers)

        platforms: list[TargetPlatform] = []
        for provider_id in provider_ids:
            normalized = self._normalize_provider_id(provider_id)
            try:
                platforms.append(TargetPlatform(normalized))
            except ValueError:
                continue

        if not platforms:
            platforms = [
                TargetPlatform.YOUTUBE,
                TargetPlatform.YOUTUBE_MUSIC,
                TargetPlatform.SOUNDCLOUD,
                TargetPlatform.BANDCAMP,
            ]

        return platforms

    # ============== URL Resolution ==============

    async def resolve_url(self, url: str) -> list[Song]:
        """
        Resolve any supported URL to a list of songs.

        Args:
            url: URL to resolve (Spotify, Deezer, YouTube Music, etc.)

        Returns:
            List of Song objects
        """
        platform = detect_platform(url)

        if platform is None:
            logger.warning(f"Unsupported URL: {url}")
            return []

        self._init_providers()

        try:
            if platform == Platform.SPOTIFY:
                return await self._resolve_spotify_url(url)
            elif platform == Platform.DEEZER:
                return await self._resolve_deezer_url(url)
            elif platform == Platform.YOUTUBE_MUSIC:
                return await self._resolve_youtube_url(url)
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

    async def _resolve_spotify_url(self, url: str) -> list[Song]:
        """Resolve a Spotify URL to songs."""
        if self._spotify_provider is None:
            logger.warning(
                "Spotify credentials not configured. "
                "Set SPOTDL_SPOTIFY_CLIENT_ID and SPOTDL_SPOTIFY_CLIENT_SECRET."
            )
            return []

        songs = await self._spotify_provider.get_songs_from_url(url)
        return songs

    async def _resolve_deezer_url(self, url: str) -> list[Song]:
        """Resolve a Deezer URL to songs."""
        if self._deezer_provider is None:
            return []
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
        if self._soundcloud_target_provider is None:
            return []
        # SoundCloud target provider doesn't have get_track_info
        # Use yt-dlp instead
        return await self._resolve_youtube_url(url)

    async def _resolve_bandcamp_url(self, url: str) -> list[Song]:
        """Resolve a Bandcamp URL to songs."""
        # Use yt-dlp for Bandcamp as well
        return await self._resolve_youtube_url(url)

    def _yt_entry_to_song(self, entry: dict[str, Any]) -> Song | None:
        """Convert yt-dlp entry to Song object."""
        try:
            video_id = entry.get("id", "")
            title = entry.get("title", "")
            duration = entry.get("duration", 0) or 0

            if not video_id or not title:
                return None

            channel = entry.get("channel", "") or entry.get("uploader", "") or "Unknown"

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

    def _result_to_song(self, result: Result) -> Song:
        """Convert a Result to a Song."""
        # Map target platform to source platform
        platform_map = {
            TargetPlatform.YOUTUBE: Platform.YOUTUBE_MUSIC,
            TargetPlatform.YOUTUBE_MUSIC: Platform.YOUTUBE_MUSIC,
            TargetPlatform.SOUNDCLOUD: Platform.SOUNDCLOUD,
            TargetPlatform.BANDCAMP: Platform.BANDCAMP,
        }

        return Song(
            name=result.name,
            artists=list(result.artists),
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

        # Search Spotify (if configured)
        if self._spotify_provider:
            try:
                spotify_songs = await self._spotify_provider.search(query, limit)
                for song in spotify_songs:
                    if song.platform_id not in seen_ids:
                        seen_ids.add(song.platform_id)
                        all_songs.append(song)
            except Exception as e:
                logger.warning(f"Spotify search failed: {e}")

        # Search Deezer
        if self._deezer_provider:
            try:
                deezer_songs = await self._deezer_provider.search(query, limit)
                for song in deezer_songs:
                    if song.platform_id not in seen_ids:
                        seen_ids.add(song.platform_id)
                        all_songs.append(song)
            except Exception as e:
                logger.warning(f"Deezer search failed: {e}")

        # Search YouTube Music
        if self._ytm_source_provider:
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

        return all_songs[: limit * 2]  # Return more results from combined search

    async def search_youtube(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Result]:
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

        download_results: list[Result] = []
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
    ) -> list[Result]:
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

        download_results: list[Result] = []
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
    ) -> Result | None:
        """Convert yt-dlp entry to Result."""
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

            return Result(
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
    ) -> list[Result]:
        """Find matching results for a song across all target platforms."""
        if platforms is None:
            platforms = self._get_target_platforms()

        self._init_providers()
        all_results: list[Result] = []

        full_query = create_search_query(song.name, song.artists)

        for platform in platforms:
            try:
                if platform == TargetPlatform.YOUTUBE_MUSIC and self._ytm_target_provider:
                    results = await self._ytm_target_provider.search(song, limit)
                elif platform == TargetPlatform.YOUTUBE and self._yt_target_provider:
                    results = await self._yt_target_provider.search(song, limit)
                elif (
                    platform == TargetPlatform.SOUNDCLOUD
                    and self._soundcloud_target_provider
                ):
                    results = await self._soundcloud_target_provider.search(song, limit)
                elif (
                    platform == TargetPlatform.BANDCAMP and self._bandcamp_target_provider
                ):
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

        return [result for result, _score in sorted_results[:limit]]

    async def get_best_match(
        self,
        song: Song,
        min_score: float | None = None,
    ) -> Result | None:
        """Get the single best match for a song."""
        self._init_providers()

        full_query = create_search_query(song.name, song.artists)
        if min_score is None:
            min_score = float(self._settings.name_match_threshold)
        all_results: list[Result] = []

        # Search all target providers
        for provider in [
            self._ytm_target_provider,
            self._yt_target_provider,
            self._soundcloud_target_provider,
            self._bandcamp_target_provider,
        ]:
            if provider:
                try:
                    results = await provider.search(song, limit=5)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Search failed: {e}")

        if not all_results:
            return None

        # Score and rank results
        scored = order_results(all_results, song, full_query)
        if not scored:
            return None

        best_result, best_score = max(scored.items(), key=lambda x: x[1])

        if best_score < min_score:
            logger.debug(f"Best match score {best_score} below threshold {min_score}")
            return None

        return best_result

    # ============== Metadata Enrichment ==============

    async def enrich_song(self, song: Song) -> Song:
        """Enrich a song with metadata from MusicBrainz and Spotify."""
        self._init_providers()

        # Try Spotify first for high-quality metadata if available
        if self._spotify_provider:
            try:
                # If we have a Spotify URL, use it
                if song.platform == Platform.SPOTIFY and song.url:
                    enriched = await self._spotify_provider.get_metadata(song.url)
                    if enriched:
                        return enriched
                
                # Otherwise search Spotify
                results = await self._spotify_provider.search(
                    create_search_query(song.name, song.artists), limit=1
                )
                if results:
                    return results[0]
            except Exception as e:
                logger.warning(f"Spotify enrichment failed: {e}")

        # Fallback to MusicBrainz
        if self._musicbrainz_provider:
            try:
                return await self._musicbrainz_provider.enrich_song(song)
            except Exception as e:
                logger.warning(f"MusicBrainz enrichment failed: {e}")

        return song

    async def get_lyrics(self, song: Song) -> str | None:
        """Get lyrics for a song using syncedlyrics."""
        search_term = f"{song.name} {song.artist}"
        loop = asyncio.get_event_loop()

        try:
            from syncedlyrics import search as lyrics_search

            result = await loop.run_in_executor(
                None,
                lambda: lyrics_search(search_term, plain_only=True),
            )
            if result:
                return result
        except Exception as e:
            logger.debug(f"Lyrics search failed: {e}")

        return None

    async def get_audio_features(self, song: Song) -> dict[str, Any] | None:
        """Get Spotify audio features for a song.

        Uses spotipy directly since SpotifyProvider doesn't expose audio_features.
        """
        self._init_providers()
        if not self._spotify_provider:
            return None

        try:
            client = self._spotify_provider._get_client()
            loop = asyncio.get_event_loop()

            # Resolve track ID
            track_id: str | None = None
            if song.platform == Platform.SPOTIFY and song.platform_id:
                track_id = song.platform_id
            else:
                # Search for the track on Spotify to get its ID
                query = create_search_query(song.name, song.artists)
                results = await loop.run_in_executor(
                    None, lambda: client.search(q=query, type="track", limit=1)
                )
                items = results.get("tracks", {}).get("items", [])
                if items:
                    track_id = items[0]["id"]

            if not track_id:
                return None

            features_list = await loop.run_in_executor(
                None, client.audio_features, [track_id]
            )
            if features_list and features_list[0]:
                return features_list[0]
        except Exception as e:
            logger.debug(f"Audio features fetch failed: {e}")

        return None

    async def get_all_lyrics(self, song: Song) -> dict[str, str]:
        """Get lyrics from all available providers.

        Returns a dict mapping provider name to lyrics text.
        Uses syncedlyrics provider classes directly to get per-provider results.
        """
        from syncedlyrics import Genius, Lrclib, Musixmatch

        search_term = f"{song.name} {song.artist}"
        loop = asyncio.get_event_loop()

        provider_instances = [
            ("Musixmatch", Musixmatch()),
            ("Genius", Genius()),
            ("Lrclib", Lrclib()),
        ]

        all_lyrics: dict[str, str] = {}
        for name, provider in provider_instances:
            try:
                result = await loop.run_in_executor(
                    None, provider.get_lrc, search_term
                )
                if result:
                    text = result.unsynced or result.synced
                    if text:
                        all_lyrics[name] = text
            except Exception as e:
                logger.debug(f"Lyrics provider {name} failed: {e}")

        return all_lyrics

    # ============== Cleanup ==============

    async def close(self) -> None:
        """Close all provider connections."""
        if self._spotify_provider:
            await self._spotify_provider.close()
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


# Re-export for convenience
__all__ = [
    "OfflineMatcher",
    "detect_platform",
    "get_offline_matcher",
    "is_valid_url",
]
