"""URL resolver for detecting platforms and routing to appropriate providers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from spotdl_core.core.types.song import Platform

if TYPE_CHECKING:
    from spotdl_core.core.types.song import Song
    from spotdl_core.providers.sources.base import SourceProvider


class URLResolverError(Exception):
    """Raised when URL cannot be resolved."""


class UnsupportedPlatformError(URLResolverError):
    """Raised when platform is not supported."""


# URL patterns for platform detection
URL_PATTERNS: dict[Platform, list[re.Pattern[str]]] = {
    Platform.SPOTIFY: [
        re.compile(r"https?://open\.spotify\.com/(?:intl-\w+/)?(track|album|playlist|artist)/([a-zA-Z0-9]+)"),
        re.compile(r"spotify:(track|album|playlist|artist):([a-zA-Z0-9]+)"),
    ],
    Platform.APPLE_MUSIC: [
        re.compile(r"https?://music\.apple\.com/\w+/(album|playlist|artist)/[^/]+/([a-zA-Z0-9._-]+)"),
        re.compile(r"https?://music\.apple\.com/\w+/album/[^/]+/(\d+)\?i=(\d+)"),  # Track in album
    ],
    Platform.DEEZER: [
        re.compile(r"https?://(?:www\.)?deezer\.com/(?:\w+/)?(track|album|playlist|artist)/(\d+)"),
        re.compile(r"deezer\.(page\.link|app\.link)/\w+"),  # Short links
    ],
    Platform.TIDAL: [
        re.compile(r"https?://(?:www\.)?tidal\.com/(?:browse/)?(track|album|playlist|artist)/(\d+)"),
        re.compile(r"https?://listen\.tidal\.com/(track|album|playlist|artist)/(\d+)"),
    ],
    Platform.YOUTUBE_MUSIC: [
        re.compile(r"https?://music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"),
        re.compile(r"https?://music\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"),
        re.compile(r"https?://music\.youtube\.com/channel/([a-zA-Z0-9_-]+)"),
    ],
    Platform.SOUNDCLOUD: [
        re.compile(r"https?://(?:www\.)?soundcloud\.com/([^/]+)/([^/]+)(?:/([^/]+))?"),
        re.compile(r"https?://(?:www\.)?soundcloud\.com/([^/]+)/sets/([^/]+)"),
    ],
    Platform.BANDCAMP: [
        re.compile(r"https?://([^.]+)\.bandcamp\.com/(track|album)/([^/]+)"),
        re.compile(r"https?://([^.]+)\.bandcamp\.com/?$"),  # Artist page
    ],
}


def detect_platform(url: str) -> Platform | None:
    """
    Detect the platform from a URL.

    Args:
        url: URL to analyze

    Returns:
        Platform enum value or None if not detected
    """
    for platform, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(url):
                return platform
    return None


def extract_url_info(url: str) -> dict[str, str | None]:
    """
    Extract information from a URL.

    Args:
        url: URL to analyze

    Returns:
        Dictionary with platform, type, and id
    """
    platform = detect_platform(url)

    if platform is None:
        return {"platform": None, "type": None, "id": None}

    url_type = None
    resource_id = None

    for pattern in URL_PATTERNS[platform]:
        match = pattern.search(url)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                url_type = groups[0]
                resource_id = groups[1]
            elif len(groups) == 1:
                resource_id = groups[0]
            break

    # Normalize URL type
    if url_type:
        url_type = url_type.lower()
        if url_type == "song":
            url_type = "track"

    return {
        "platform": platform.value if platform else None,
        "type": url_type,
        "id": resource_id,
    }


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is from a supported platform.

    Args:
        url: URL to check

    Returns:
        True if URL is from a supported platform
    """
    return detect_platform(url) is not None


class URLResolver:
    """
    Resolves URLs to songs using the appropriate provider.

    This class manages provider instances and routes requests
    to the correct provider based on URL detection.
    """

    def __init__(self) -> None:
        """Initialize the URL resolver."""
        self._providers: dict[Platform, SourceProvider] = {}

    def register_provider(self, platform: Platform, provider: SourceProvider) -> None:
        """
        Register a provider for a platform.

        Args:
            platform: Platform this provider handles
            provider: Provider instance
        """
        self._providers[platform] = provider

    def get_provider(self, platform: Platform) -> SourceProvider | None:
        """
        Get the provider for a platform.

        Args:
            platform: Platform to get provider for

        Returns:
            Provider instance or None if not registered
        """
        return self._providers.get(platform)

    def get_provider_for_url(self, url: str) -> SourceProvider | None:
        """
        Get the provider that can handle a URL.

        Args:
            url: URL to get provider for

        Returns:
            Provider instance or None if no provider found
        """
        platform = detect_platform(url)
        if platform is None:
            return None
        return self._providers.get(platform)

    async def resolve(self, url: str) -> list[Song]:
        """
        Resolve a URL to songs.

        Args:
            url: URL to resolve

        Returns:
            List of Song objects

        Raises:
            UnsupportedPlatformError: If platform is not supported
            URLResolverError: If URL cannot be resolved
        """
        platform = detect_platform(url)

        if platform is None:
            raise UnsupportedPlatformError(f"Could not detect platform from URL: {url}")

        provider = self._providers.get(platform)

        if provider is None:
            raise UnsupportedPlatformError(
                f"No provider registered for platform: {platform.value}"
            )

        return await provider.get_songs_from_url(url)

    @property
    def supported_platforms(self) -> list[Platform]:
        """Get list of platforms with registered providers."""
        return list(self._providers.keys())


# Global resolver instance
_resolver: URLResolver | None = None


def get_resolver() -> URLResolver:
    """Get the global URL resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = URLResolver()
    return _resolver
