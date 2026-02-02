"""Query parsing utilities for SpotDL CLI.

Supports query prefixes like `album:`, `artist:`, `playlist:`, and special keywords.
"""

from __future__ import annotations

from enum import StrEnum


class QueryType(StrEnum):
    """Types of queries that can be parsed."""

    AUTO = "auto"  # Auto-detect (URL or search)
    URL = "url"  # Direct URL
    ALBUM = "album"  # album: prefix
    ARTIST = "artist"  # artist: prefix
    PLAYLIST = "playlist"  # playlist: prefix
    TRACK = "track"  # track: prefix
    SAVED = "saved"  # User's saved tracks
    USER_PLAYLISTS = "user_playlists"  # all-user-playlists
    SAVED_ALBUMS = "saved_albums"  # all-user-saved-albums


# Query prefix mapping
QUERY_PREFIXES: dict[str, QueryType] = {
    "album:": QueryType.ALBUM,
    "artist:": QueryType.ARTIST,
    "playlist:": QueryType.PLAYLIST,
    "track:": QueryType.TRACK,
}

# Special keyword mapping
SPECIAL_KEYWORDS: dict[str, QueryType] = {
    "saved": QueryType.SAVED,
    "all-user-playlists": QueryType.USER_PLAYLISTS,
    "all-user-saved-albums": QueryType.SAVED_ALBUMS,
}

# URL patterns that indicate a URL query
URL_PATTERNS: tuple[str, ...] = (
    "http://",
    "https://",
    "spotify:",
    "deezer:",
    "open.spotify.com",
    "spotify.com",
    "deezer.com",
    "youtube.com",
    "youtu.be",
    "music.youtube.com",
    "soundcloud.com",
    "bandcamp.com",
    "music.apple.com",
    "tidal.com",
)


def parse_query(query: str) -> tuple[QueryType, str]:
    """Parse a query string to extract the query type and value.

    Args:
        query: The raw query string

    Returns:
        Tuple of (query_type, cleaned_value)

    Examples:
        >>> parse_query("album:Random Access Memories")
        (QueryType.ALBUM, "Random Access Memories")

        >>> parse_query("https://open.spotify.com/track/...")
        (QueryType.URL, "https://open.spotify.com/track/...")

        >>> parse_query("Daft Punk")
        (QueryType.AUTO, "Daft Punk")

        >>> parse_query("saved")
        (QueryType.SAVED, "")
    """
    query = query.strip()

    if not query:
        return QueryType.AUTO, ""

    # Check for special keywords (case-insensitive)
    query_lower = query.lower()
    if query_lower in SPECIAL_KEYWORDS:
        return SPECIAL_KEYWORDS[query_lower], ""

    # Check for query prefixes (case-insensitive)
    for prefix, query_type in QUERY_PREFIXES.items():
        if query_lower.startswith(prefix):
            value = query[len(prefix) :].strip()
            return query_type, value

    # Check for URL patterns
    for pattern in URL_PATTERNS:
        if pattern in query_lower:
            return QueryType.URL, query

    # Default to auto-detect
    return QueryType.AUTO, query


def is_url(query: str) -> bool:
    """Check if a query string is a URL.

    Args:
        query: The query string to check

    Returns:
        True if the query appears to be a URL
    """
    query_lower = query.lower().strip()
    return any(pattern in query_lower for pattern in URL_PATTERNS)


def extract_platform_from_url(url: str) -> str | None:
    """Extract the platform name from a URL.

    Args:
        url: The URL to analyze

    Returns:
        Platform name or None if not recognized
    """
    url_lower = url.lower()

    if "spotify" in url_lower:
        return "spotify"
    if "deezer" in url_lower:
        return "deezer"
    if "music.youtube" in url_lower:
        return "youtube_music"
    if "youtube" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "soundcloud" in url_lower:
        return "soundcloud"
    if "bandcamp" in url_lower:
        return "bandcamp"
    if "music.apple" in url_lower:
        return "apple_music"
    if "tidal" in url_lower:
        return "tidal"

    return None


def extract_content_type_from_url(url: str) -> str | None:
    """Extract the content type from a URL (track, album, artist, playlist).

    Args:
        url: The URL to analyze

    Returns:
        Content type or None if not recognized
    """
    url_lower = url.lower()

    # Spotify patterns
    if "spotify" in url_lower:
        if "/track/" in url_lower or "spotify:track:" in url_lower:
            return "track"
        if "/album/" in url_lower or "spotify:album:" in url_lower:
            return "album"
        if "/artist/" in url_lower or "spotify:artist:" in url_lower:
            return "artist"
        if "/playlist/" in url_lower or "spotify:playlist:" in url_lower:
            return "playlist"

    # Deezer patterns
    if "deezer" in url_lower:
        if "/track/" in url_lower:
            return "track"
        if "/album/" in url_lower:
            return "album"
        if "/artist/" in url_lower:
            return "artist"
        if "/playlist/" in url_lower:
            return "playlist"

    # YouTube patterns
    if "youtube" in url_lower or "youtu.be" in url_lower:
        if "list=" in url_lower:
            return "playlist"
        return "track"

    # SoundCloud patterns
    if "soundcloud" in url_lower:
        if "/sets/" in url_lower:
            return "playlist"
        return "track"

    # Apple Music patterns
    if "music.apple" in url_lower:
        if "/album/" in url_lower:
            return "album"
        if "/artist/" in url_lower:
            return "artist"
        if "/playlist/" in url_lower:
            return "playlist"
        return "track"

    return None


__all__ = [
    "QUERY_PREFIXES",
    "SPECIAL_KEYWORDS",
    "QueryType",
    "extract_content_type_from_url",
    "extract_platform_from_url",
    "is_url",
    "parse_query",
]
