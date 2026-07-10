"""Last.fm metadata provider (free API key; engagement + bio + tags).

Last.fm exposes a free JSON web service at ``https://ws.audioscrobbler.com/2.0/``.
Unlike the other metadata sources it has **no reliable id-resolve** for our
canonical refs, so it is integrated as a *name-keyed enrichment* source rather
than a :class:`~spotdl_core.providers.base.Resolves`/``Searches`` provider: the
resolve layer queries it by name during artist/track enrichment, confirms the
returned name matches (guarding against a wrong-artist bio), and folds the result
in as an extra snapshot + engagement stats.

Endpoints used (all ``format=json``, ``api_key`` on every call):

* ``artist.getInfo?artist={name}&autocorrect=1`` -> ``stats.listeners`` /
  ``stats.playcount`` (engagement), ``bio.summary`` (the artist ``bio`` — Spotify
  never provides one, so this fills it), ``tags.tag[].name`` (-> genres).
* ``track.getInfo?artist={a}&track={t}&autocorrect=1`` -> ``listeners`` /
  ``playcount`` and ``toptags.tag[].name`` (-> genres).

**Not-found is not an error.** Last.fm answers an unknown artist/track with a
``200`` body carrying an ``error`` code (6 = "not found"), not a ``404``. Those
bodies map to ``None`` (a clean miss). Transport/5xx failures propagate as the
usual taxonomy errors (the enrichment leg degrades that one source, never fatal).

The ``bio.summary`` HTML carries a trailing ``<a href=...>Read more on Last.fm</a>``
link and occasional inline tags; :func:`clean_bio` strips all tags and that link,
returning plain text (or ``None`` when nothing readable remains).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict

from spotdl_core.model import ProviderId
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.http import create_client, request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = [
    "LastfmArtistInfo",
    "LastfmProvider",
    "LastfmTrackInfo",
    "build_lastfm_provider",
    "clean_bio",
    "map_artist_info",
    "map_track_info",
]

#: Base URL. The trailing slash is load-bearing: httpx joins request paths
#: relative to it, so the (empty) request path preserves the ``/2.0/`` endpoint.
_API_BASE = "https://ws.audioscrobbler.com/2.0/"

#: Number of top tags kept as genres (Last.fm returns a long, noisy tail).
_MAX_TAGS = 5

#: Strips any HTML tag; used to reduce ``bio.summary`` to plain text.
_TAG_RE = re.compile(r"<[^>]+>")

#: A trailing "Read more" sentence Last.fm appends to every ``bio.summary``.
_READ_MORE_RE = re.compile(r"\s*Read more\s*(on Last\.fm)?\.?\s*$", re.IGNORECASE)


class LastfmArtistInfo(BaseModel):
    """Name-confirmed artist info: engagement + bio + tags (genres)."""

    model_config = ConfigDict(frozen=True)

    name: str
    listeners: int | None = None
    playcount: int | None = None
    bio: str | None = None
    genres: tuple[str, ...] = ()


class LastfmTrackInfo(BaseModel):
    """Name-confirmed track info: engagement + tags (genres)."""

    model_config = ConfigDict(frozen=True)

    name: str
    artist: str | None = None
    listeners: int | None = None
    playcount: int | None = None
    genres: tuple[str, ...] = ()


# --- pure mappers ---------------------------------------------------------


def _int(value: Any) -> int | None:
    """Coerce a Last.fm count (a numeric string) to a non-negative int, else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def clean_bio(summary: str | None) -> str | None:
    """Reduce a ``bio.summary`` HTML blob to plain text (or ``None`` if empty).

    Strips every HTML tag (including the trailing ``<a>Read more</a>`` link) and
    the "Read more on Last.fm" sentence, collapses whitespace, and returns the
    remaining prose. ``None``/blank in yields ``None`` out.
    """
    if not summary:
        return None
    text = _TAG_RE.sub("", summary)
    text = _READ_MORE_RE.sub("", text)
    text = " ".join(text.split())
    return text or None


def _tags(container: dict[str, Any] | None) -> tuple[str, ...]:
    """Flatten a ``{"tag": [{"name": ...}, ...]}`` block to ordered genre names."""
    if not isinstance(container, dict):
        return ()
    raw = container.get("tag")
    if isinstance(raw, dict):  # a single tag is returned unwrapped
        raw = [raw]
    if not isinstance(raw, list):
        return ()
    names: list[str] = []
    for entry in raw:
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return tuple(names[:_MAX_TAGS])


def map_artist_info(payload: dict[str, Any]) -> LastfmArtistInfo | None:
    """Map an ``artist.getInfo`` body to :class:`LastfmArtistInfo`, or ``None``.

    ``None`` when the body carries an ``error`` code or lacks a usable name (a
    clean miss — the caller treats it as "no Last.fm data", not a failure).
    """
    if payload.get("error"):
        return None
    artist = payload.get("artist")
    if not isinstance(artist, dict):
        return None
    name = artist.get("name")
    if not isinstance(name, str) or not name:
        return None
    raw_stats = artist.get("stats")
    stats: dict[str, Any] = raw_stats if isinstance(raw_stats, dict) else {}
    raw_bio = artist.get("bio")
    bio: dict[str, Any] = raw_bio if isinstance(raw_bio, dict) else {}
    return LastfmArtistInfo(
        name=name,
        listeners=_int(stats.get("listeners")),
        playcount=_int(stats.get("playcount")),
        bio=clean_bio(bio.get("summary")),
        genres=_tags(artist.get("tags")),
    )


def map_track_info(payload: dict[str, Any]) -> LastfmTrackInfo | None:
    """Map a ``track.getInfo`` body to :class:`LastfmTrackInfo`, or ``None``."""
    if payload.get("error"):
        return None
    track = payload.get("track")
    if not isinstance(track, dict):
        return None
    name = track.get("name")
    if not isinstance(name, str) or not name:
        return None
    artist = track.get("artist")
    artist_name = artist.get("name") if isinstance(artist, dict) else None
    return LastfmTrackInfo(
        name=name,
        artist=artist_name if isinstance(artist_name, str) else None,
        listeners=_int(track.get("listeners")),
        playcount=_int(track.get("playcount")),
        genres=_tags(track.get("toptags")),
    )


# --- provider -------------------------------------------------------------


class LastfmProvider(HttpProvider):
    """Query Last.fm's free API for name-keyed engagement, bio and tags.

    Deliberately *not* a capability Protocol implementer (it cannot resolve or
    search our refs): the registry constructs it, and the resolve layer fetches it
    by id (:data:`~spotdl_core.model.ProviderId.LASTFM`) to enrich artists/tracks
    by name. Both lookups are best-effort — a miss returns ``None``; a transport
    failure raises the usual taxonomy error for the caller to treat as degraded.
    """

    id: ClassVar[ProviderId] = ProviderId.LASTFM

    def __init__(self, client: Any, *, api_key: str) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def _get(self, method: str, **params: Any) -> Any:
        query = {
            "method": method,
            "api_key": self._api_key,
            "format": "json",
            "autocorrect": "1",
            **{key: value for key, value in params.items() if value is not None},
        }
        return await request_json(self._client, "GET", "", provider=ProviderId.LASTFM, params=query)

    async def artist_info(self, name: str) -> LastfmArtistInfo | None:
        """Look up ``name`` via ``artist.getInfo`` (``None`` on a miss)."""
        if not name:
            return None
        return map_artist_info(await self._get("artist.getInfo", artist=name))

    async def track_info(self, artist: str, track: str) -> LastfmTrackInfo | None:
        """Look up ``artist``/``track`` via ``track.getInfo`` (``None`` on a miss)."""
        if not artist or not track:
            return None
        return map_track_info(await self._get("track.getInfo", artist=artist, track=track))


# --- factory --------------------------------------------------------------


def build_lastfm_provider(ctx: ProviderContext) -> LastfmProvider:
    """Construct a :class:`LastfmProvider`; require an API key (contract).

    Raises :class:`~spotdl_core.providers.errors.ProviderUnavailable` when
    ``ctx.lastfm.api_key`` is unset so the registry omits Last.fm (a silently
    skipped, degraded-at-most source) rather than constructing a provider that
    always fails — mirroring the Genius token gate.
    """
    from spotdl_core.providers.errors import ProviderUnavailable

    api_key = ctx.lastfm.api_key
    if not api_key:
        raise ProviderUnavailable(
            "last.fm requires an api key (SPOTDL_LASTFM_API_KEY)", provider=ProviderId.LASTFM
        )
    client = create_client(user_agent=ctx.user_agent, base_url=_API_BASE)
    return LastfmProvider(client, api_key=api_key)
