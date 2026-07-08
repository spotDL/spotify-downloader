"""Single source of truth for URL and ``provider:type:id`` parsing.

Every layer that turns a user-supplied string into a provider reference goes
through :func:`parse`. Parsing is entirely offline and synchronous; only
:func:`resolve_shortlink` touches the network (to expand short domains such as
``spotify.link``). The accepted-forms table in the Task 2 brief is the
authoritative contract for what :func:`parse` accepts.

``entity_id`` is always the raw platform id with query string and fragment
stripped, except for the handful of providers whose id lives in the query
(YouTube ``v=``/``list=``, Apple Music ``i=``) or is intentionally the URL path
(SoundCloud, Bandcamp -- the respective providers re-expand it later).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

from spotdl_core.model import EntityType, ProviderId
from spotdl_core.providers.errors import UnsupportedURL

if TYPE_CHECKING:
    import httpx

__all__ = ["PlatformRef", "parse", "resolve_shortlink", "strip_intl"]

# Short-link domains that must be expanded (over the network) before parsing.
_SHORT_HOSTS = frozenset({"spotify.link", "deezer.page.link", "deezer.app.link"})

# Locale segment injected by some hosts, e.g. ``/intl-de/``.
_INTL_RE = re.compile(r"/intl-[a-z]{2}/")


@dataclass(frozen=True, slots=True)
class PlatformRef:
    """A resolved reference to an entity on a specific provider.

    ``entity_id`` is the raw platform identifier. ``url`` is the (intl-stripped)
    source URL when the reference came from a URL, and ``None`` when it came from
    a ``provider:type:id`` string.
    """

    provider: ProviderId
    entity_type: EntityType
    entity_id: str
    url: str | None = None


def strip_intl(url: str) -> str:
    """Remove a ``/intl-xx/`` locale segment so it is transparent to matching."""
    return _INTL_RE.sub("/", url)


def parse(value: str) -> PlatformRef:
    """Parse a URL or ``provider:type:id`` string into a :class:`PlatformRef`.

    Raises :class:`UnsupportedURL` if the value matches no known form.
    """
    raw = value.strip()
    if not raw:
        raise UnsupportedURL(value)

    if "://" not in raw:
        # No scheme: the only accepted shape is ``provider:type:id`` (this also
        # covers Spotify URIs, which share that grammar).
        ref = _parse_uri(raw)
        if ref is not None:
            return ref
        raise UnsupportedURL(value)

    ref = _parse_url(strip_intl(raw))
    if ref is not None:
        return ref
    raise UnsupportedURL(value)


def _parse_uri(raw: str) -> PlatformRef | None:
    """Parse ``provider:type:id`` (validating provider and type). ``None`` if invalid."""
    parts = raw.split(":", 2)
    if len(parts) != 3:
        return None
    provider_str, type_str, entity_id = parts
    if not entity_id:
        return None
    try:
        provider = ProviderId(provider_str)
        entity_type = EntityType(type_str)
    except ValueError:
        return None
    return PlatformRef(provider=provider, entity_type=entity_type, entity_id=entity_id)


def _segments(path: str) -> list[str]:
    return [segment for segment in path.split("/") if segment]


def _parse_url(url: str) -> PlatformRef | None:  # noqa: PLR0911 - flat host dispatch
    """Match a URL against the known host table. ``None`` if no host matches."""
    split = urlsplit(url)
    host = (split.hostname or "").lower()
    segments = _segments(split.path)
    query = parse_qs(split.query)

    if host == "open.spotify.com":
        return _spotify(segments, url)
    if host in {"www.deezer.com", "deezer.com"}:
        return _deezer(segments, url)
    if host == "music.apple.com":
        return _apple(segments, query, url)
    if host == "musicbrainz.org":
        return _musicbrainz(segments, url)
    if host == "music.youtube.com":
        return _ytmusic(segments, query, url)
    if host in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        return _youtube(segments, query, url)
    if host == "youtu.be":
        return _youtu_be(segments, url)
    if host == "piped.video":
        return _piped(segments, query, url)
    if host == "soundcloud.com":
        return _soundcloud(segments, url)
    if host.endswith(".bandcamp.com"):
        return _bandcamp(host, segments, url)
    return None


def _spotify(segments: list[str], url: str) -> PlatformRef | None:
    if len(segments) >= 2:
        try:
            entity_type = EntityType(segments[0])
        except ValueError:
            return None
        return PlatformRef(ProviderId.SPOTIFY, entity_type, segments[1], url=url)
    return None


def _deezer(segments: list[str], url: str) -> PlatformRef | None:
    # An optional locale prefix (``/en/``, ``/us/``) precedes ``/type/id``.
    for index, segment in enumerate(segments):
        try:
            entity_type = EntityType(segment)
        except ValueError:
            continue
        if index + 1 < len(segments):
            return PlatformRef(ProviderId.DEEZER, entity_type, segments[index + 1], url=url)
    return None


def _apple(segments: list[str], query: dict[str, list[str]], url: str) -> PlatformRef | None:
    # ``?i=<track-id>`` on an album URL denotes a single track.
    if "i" in query and query["i"]:
        return PlatformRef(ProviderId.ITUNES, EntityType.TRACK, query["i"][0], url=url)
    mapping = {
        "album": EntityType.ALBUM,
        "artist": EntityType.ARTIST,
        "playlist": EntityType.PLAYLIST,
    }
    for segment in segments:
        entity_type = mapping.get(segment)
        if entity_type is not None:
            # The numeric/opaque id is always the final path segment.
            return PlatformRef(ProviderId.ITUNES, entity_type, segments[-1], url=url)
    return None


def _musicbrainz(segments: list[str], url: str) -> PlatformRef | None:
    mapping = {
        "recording": EntityType.TRACK,
        "release": EntityType.ALBUM,
        "artist": EntityType.ARTIST,
    }
    if len(segments) >= 2:
        entity_type = mapping.get(segments[0])
        if entity_type is not None:
            return PlatformRef(ProviderId.MUSICBRAINZ, entity_type, segments[1], url=url)
    return None


def _ytmusic(segments: list[str], query: dict[str, list[str]], url: str) -> PlatformRef | None:
    if segments and segments[0] == "watch" and query.get("v"):
        return PlatformRef(ProviderId.YTMUSIC, EntityType.TRACK, query["v"][0], url=url)
    if segments and segments[0] == "playlist" and query.get("list"):
        # A YouTube Music "playlist" (OLAK...) is an album release.
        return PlatformRef(ProviderId.YTMUSIC, EntityType.ALBUM, query["list"][0], url=url)
    return None


def _youtube(segments: list[str], query: dict[str, list[str]], url: str) -> PlatformRef | None:
    if segments and segments[0] == "watch" and query.get("v"):
        return PlatformRef(ProviderId.YOUTUBE, EntityType.TRACK, query["v"][0], url=url)
    if segments and segments[0] == "playlist" and query.get("list"):
        return PlatformRef(ProviderId.YOUTUBE, EntityType.PLAYLIST, query["list"][0], url=url)
    return None


def _youtu_be(segments: list[str], url: str) -> PlatformRef | None:
    if segments:
        return PlatformRef(ProviderId.YOUTUBE, EntityType.TRACK, segments[0], url=url)
    return None


def _piped(segments: list[str], query: dict[str, list[str]], url: str) -> PlatformRef | None:
    if segments and segments[0] == "watch" and query.get("v"):
        return PlatformRef(ProviderId.PIPED, EntityType.TRACK, query["v"][0], url=url)
    return None


def _soundcloud(segments: list[str], url: str) -> PlatformRef | None:
    # SoundCloud has no numeric id in the URL; the path itself is the id.
    if not segments:
        return None
    if "sets" in segments:
        return PlatformRef(ProviderId.SOUNDCLOUD, EntityType.PLAYLIST, "/".join(segments), url=url)
    if len(segments) >= 2:
        return PlatformRef(ProviderId.SOUNDCLOUD, EntityType.TRACK, "/".join(segments[:2]), url=url)
    return PlatformRef(ProviderId.SOUNDCLOUD, EntityType.ARTIST, segments[0], url=url)


def _bandcamp(host: str, segments: list[str], url: str) -> PlatformRef | None:
    artist = host.split(".", 1)[0]
    mapping = {"track": EntityType.TRACK, "album": EntityType.ALBUM}
    if len(segments) >= 2:
        entity_type = mapping.get(segments[0])
        if entity_type is not None:
            entity_id = f"{artist}/{segments[0]}/{segments[1]}"
            return PlatformRef(ProviderId.BANDCAMP, entity_type, entity_id, url=url)
    return None


async def resolve_shortlink(client: httpx.AsyncClient, value: str) -> str:
    """Expand a short-link domain to its canonical URL; pass through otherwise.

    For ``spotify.link`` / ``deezer.page.link`` / ``deezer.app.link`` this issues
    a redirect-following GET and returns the final URL. Any other input is
    returned unchanged without a network request.
    """
    host = (urlsplit(value).hostname or "").lower()
    if host in _SHORT_HOSTS:
        response = await client.get(value, follow_redirects=True)
        return str(response.url)
    return value
