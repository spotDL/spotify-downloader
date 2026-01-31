"""Song service for resolving URLs to song metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    pass


class SongServiceError(Exception):
    """Base exception for song service errors."""


class UnsupportedURLError(SongServiceError):
    """Raised when URL is not from a supported platform."""


class SongService:
    """
    Service for resolving URLs to song metadata.

    This service manages source providers and uses them to
    fetch song metadata from various platforms.
    """

    def __init__(
        self,
        spotify_client_id: str | None = None,
        spotify_client_secret: str | None = None,
        ytmusic_auth_file: str | None = None,
    ) -> None:
        """
        Initialize the song service.

        Args:
            spotify_client_id: Spotify API client ID
            spotify_client_secret: Spotify API client secret
            ytmusic_auth_file: YouTube Music auth file path
        """
        self._resolver = URLResolver()
        self._providers: dict[Platform, SourceProvider] = {}

        # Initialize providers
        self._init_providers(
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
            ytmusic_auth_file=ytmusic_auth_file,
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

    async def resolve_url(self, url: str) -> list[Song]:
        """
        Resolve a URL to songs.

        Args:
            url: URL to resolve

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
            return songs
        except SourceProviderError as e:
            raise SongServiceError(f"Failed to resolve URL: {e}") from e

    async def get_track(self, url: str) -> Song:
        """
        Get a single track from URL.

        Args:
            url: Track URL

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
            return await provider.get_track(url)
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
        """
        provider = self._providers.get(platform)
        if provider is None:
            raise UnsupportedURLError(f"No provider for platform: {platform.value}")

        try:
            return await provider.search(query, limit=limit)
        except SourceProviderError:
            return []

    @property
    def supported_platforms(self) -> list[Platform]:
        """Get list of supported platforms."""
        return list(self._providers.keys())


# Global service instance
_song_service: SongService | None = None


def get_song_service(
    spotify_client_id: str | None = None,
    spotify_client_secret: str | None = None,
    ytmusic_auth_file: str | None = None,
) -> SongService:
    """
    Get the global song service instance.

    Args:
        spotify_client_id: Spotify API client ID
        spotify_client_secret: Spotify API client secret
        ytmusic_auth_file: YouTube Music auth file path

    Returns:
        SongService instance
    """
    global _song_service
    if _song_service is None:
        _song_service = SongService(
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
            ytmusic_auth_file=ytmusic_auth_file,
        )
    return _song_service
