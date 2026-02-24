"""Song service for resolving URLs to song metadata."""

from __future__ import annotations

import logging

from spotdl.core.services.metadata import MetadataService
from spotdl.core.types.song import Platform, Song, SongList
from spotdl.providers.sources import (
    AppleMusicProvider,
    BandcampProvider,
    DeezerProvider,
    SoundCloudProvider,
    SourceProvider,
    SourceProviderError,
    SpotifyProvider,
    TidalProvider,
    URLResolver,
    YouTubeMusicProvider,
    detect_platform,
)

logger = logging.getLogger(__name__)


class SongServiceError(Exception):
    """Base exception for song service errors."""


class UnsupportedURLError(SongServiceError):
    """Raised when URL is not from a supported platform."""


class SongService:
    """
    Service for resolving URLs to song metadata.

    This service manages source providers and uses them to
    fetch song metadata from various platforms.

    Optionally enriches songs with metadata from MusicBrainz and Discogs.
    """

    def __init__(
        self,
        spotify_client_id: str | None = None,
        spotify_client_secret: str | None = None,
        ytmusic_auth_file: str | None = None,
        enable_metadata_enrichment: bool = True,
        enable_musicbrainz: bool = True,
        enable_discogs: bool = True,
        discogs_user_token: str | None = None,
    ) -> None:
        """
        Initialize the song service.

        Args:
            spotify_client_id: Spotify API client ID
            spotify_client_secret: Spotify API client secret
            ytmusic_auth_file: YouTube Music auth file path
            enable_metadata_enrichment: Enable metadata enrichment from external sources
            enable_musicbrainz: Enable MusicBrainz lookups (free, no auth)
            enable_discogs: Enable Discogs lookups (free, optional auth for higher rate limits)
            discogs_user_token: Optional Discogs user token for higher rate limits
        """
        self._resolver = URLResolver()
        self._providers: dict[Platform, SourceProvider] = {}
        self._metadata_service: MetadataService | None = None
        self._enable_enrichment = enable_metadata_enrichment

        # Initialize source providers
        self._init_providers(
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
            ytmusic_auth_file=ytmusic_auth_file,
        )

        # Initialize metadata service for enrichment
        if enable_metadata_enrichment:
            self._metadata_service = MetadataService(
                enable_musicbrainz=enable_musicbrainz,
                enable_discogs=enable_discogs,
                discogs_user_token=discogs_user_token,
            )
            logger.debug(
                f"Metadata enrichment enabled with providers: "
                f"{self._metadata_service.provider_names}"
            )

    def _init_providers(
        self,
        spotify_client_id: str | None = None,
        spotify_client_secret: str | None = None,
        ytmusic_auth_file: str | None = None,
    ) -> None:
        """Initialize and register all source providers."""
        # Spotify
        spotify = SpotifyProvider(
            client_id=spotify_client_id,
            client_secret=spotify_client_secret,
        )
        self._providers[Platform.SPOTIFY] = spotify
        self._resolver.register_provider(Platform.SPOTIFY, spotify)

        # YouTube Music
        ytmusic = YouTubeMusicProvider(auth_file=ytmusic_auth_file)
        self._providers[Platform.YOUTUBE_MUSIC] = ytmusic
        self._resolver.register_provider(Platform.YOUTUBE_MUSIC, ytmusic)

        # Deezer
        deezer = DeezerProvider()
        self._providers[Platform.DEEZER] = deezer
        self._resolver.register_provider(Platform.DEEZER, deezer)

        # Apple Music
        apple_music = AppleMusicProvider()
        self._providers[Platform.APPLE_MUSIC] = apple_music
        self._resolver.register_provider(Platform.APPLE_MUSIC, apple_music)

        # Tidal
        tidal = TidalProvider()
        self._providers[Platform.TIDAL] = tidal
        self._resolver.register_provider(Platform.TIDAL, tidal)

        # SoundCloud
        soundcloud = SoundCloudProvider()
        self._providers[Platform.SOUNDCLOUD] = soundcloud
        self._resolver.register_provider(Platform.SOUNDCLOUD, soundcloud)

        # Bandcamp
        bandcamp = BandcampProvider()
        self._providers[Platform.BANDCAMP] = bandcamp
        self._resolver.register_provider(Platform.BANDCAMP, bandcamp)

    def get_provider(self, platform: Platform) -> SourceProvider | None:
        """
        Get the provider for a platform.

        Args:
            platform: Platform to get provider for

        Returns:
            Provider instance or None
        """
        return self._providers.get(platform)

    async def resolve_url(self, url: str, enrich: bool | None = None) -> list[Song]:
        """
        Resolve a URL to songs.

        Args:
            url: URL to resolve
            enrich: Whether to enrich songs with metadata (defaults to service setting)

        Returns:
            List of Song objects

        Raises:
            UnsupportedURLError: If URL is not supported
            SongServiceError: If resolution fails
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedURLError(f"Unsupported URL: {url}")

        try:
            songs = await self._resolver.resolve(url)

            # Enrich songs with metadata if enabled
            should_enrich = enrich if enrich is not None else self._enable_enrichment
            if should_enrich and self._metadata_service and songs:
                songs = await self._metadata_service.enrich_songs(
                    songs,
                    use_all_providers=True,
                )

            return songs
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to resolve URL: {e}") from e

    async def get_track(self, url: str, enrich: bool | None = None) -> Song:
        """
        Get a single track from URL.

        Args:
            url: Track URL
            enrich: Whether to enrich with metadata (defaults to service setting)

        Returns:
            Song object

        Raises:
            UnsupportedURLError: If URL is not supported
            SongServiceError: If fetch fails
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedURLError(f"Unsupported URL: {url}")

        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            song = await provider.get_track(url)

            # Enrich with metadata if enabled
            should_enrich = enrich if enrich is not None else self._enable_enrichment
            if should_enrich and self._metadata_service:
                song = await self._metadata_service.enrich_song(
                    song,
                    use_all_providers=True,
                )

            return song
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to get track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Get an album from URL.

        Args:
            url: Album URL

        Returns:
            SongList containing album tracks

        Raises:
            UnsupportedURLError: If URL is not supported
            SongServiceError: If fetch fails
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedURLError(f"Unsupported URL: {url}")

        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            return await provider.get_album(url)
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to get album: {e}") from e

    async def get_playlist(self, url: str) -> SongList:
        """
        Get a playlist from URL.

        Args:
            url: Playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            UnsupportedURLError: If URL is not supported
            SongServiceError: If fetch fails
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedURLError(f"Unsupported URL: {url}")

        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            return await provider.get_playlist(url)
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to get playlist: {e}") from e

    async def get_artist(self, url: str) -> SongList:
        """
        Get all tracks from an artist.

        Args:
            url: Artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            UnsupportedURLError: If URL is not supported
            SongServiceError: If fetch fails
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedURLError(f"Unsupported URL: {url}")

        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            return await provider.get_artist(url)
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to get artist: {e}") from e

    async def search(
        self,
        query: str,
        platform: Platform = Platform.SPOTIFY,
        limit: int = 10,
    ) -> list[Song]:
        """
        Search for songs on a platform.

        Args:
            query: Search query
            platform: Platform to search on
            limit: Maximum number of results

        Returns:
            List of matching Song objects

        Raises:
            UnsupportedURLError: If platform is not supported
            SongServiceError: If search fails
        """
        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            return await provider.search(query, limit=limit)
        except SourceProviderError as e:
            raise SongServiceError(str(e)) from e

    @property
    def supported_platforms(self) -> list[Platform]:
        """Get list of supported platforms."""
        return list(self._providers.keys())

    @property
    def metadata_providers(self) -> list[str]:
        """Get list of active metadata providers."""
        if self._metadata_service:
            return self._metadata_service.provider_names
        return []

    async def enrich_song(self, song: Song) -> Song:
        """
        Enrich a song with metadata from external sources.

        Uses MusicBrainz and Discogs to fill in missing metadata
        like ISRC, genres, year, album info, etc.

        Args:
            song: Song to enrich

        Returns:
            Enriched Song object (same instance, modified)
        """
        if self._metadata_service:
            return await self._metadata_service.enrich_song(
                song,
                use_all_providers=True,
            )
        return song

    async def enrich_songs(self, songs: list[Song]) -> list[Song]:
        """
        Enrich multiple songs with metadata.

        Args:
            songs: Songs to enrich

        Returns:
            List of enriched Song objects
        """
        if self._metadata_service:
            return await self._metadata_service.enrich_songs(
                songs,
                use_all_providers=True,
            )
        return songs

    async def lookup_isrc(self, isrc: str) -> dict | None:
        """
        Look up metadata by ISRC code.

        Args:
            isrc: ISRC code (e.g., "USRC17607839")

        Returns:
            Metadata dict or None if not found
        """
        if self._metadata_service:
            return await self._metadata_service.lookup_by_isrc(isrc)
        return None


# Global service instance
_song_service: SongService | None = None


def get_song_service(
    spotify_client_id: str | None = None,
    spotify_client_secret: str | None = None,
    ytmusic_auth_file: str | None = None,
    enable_metadata_enrichment: bool = True,
    enable_musicbrainz: bool = True,
    enable_discogs: bool = True,
    discogs_user_token: str | None = None,
) -> SongService:
    """
    Get the global song service instance.

    Args:
        spotify_client_id: Spotify API client ID
        spotify_client_secret: Spotify API client secret
        ytmusic_auth_file: YouTube Music auth file path
        enable_metadata_enrichment: Enable metadata enrichment from external sources
        enable_musicbrainz: Enable MusicBrainz lookups (free, no auth)
        enable_discogs: Enable Discogs lookups (free, optional auth)
        discogs_user_token: Optional Discogs user token for higher rate limits

    Returns:
        SongService instance
    """
    global _song_service
    if _song_service is None:
        # Import settings here to avoid circular imports
        from spotdl.config import get_settings

        settings = get_settings()

        # Use provided credentials or fall back to settings
        client_id = spotify_client_id or settings.spotify_client_id
        client_secret = spotify_client_secret
        if client_secret is None and settings.spotify_client_secret:
            client_secret = settings.spotify_client_secret.get_secret_value()

        _song_service = SongService(
            spotify_client_id=client_id,
            spotify_client_secret=client_secret,
            ytmusic_auth_file=ytmusic_auth_file,
            enable_metadata_enrichment=enable_metadata_enrichment,
            enable_musicbrainz=enable_musicbrainz,
            enable_discogs=enable_discogs,
            discogs_user_token=discogs_user_token,
        )
    return _song_service
