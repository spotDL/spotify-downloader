"""MusicBrainz metadata provider (open API, no auth, 1 request/second).

MusicBrainz exposes a free web service at ``https://musicbrainz.org/ws/2/``.
This provider talks to it with **plain httpx and** ``fmt=json`` -- deliberately
no ``musicbrainzngs`` dependency, so the whole provider layer has a single HTTP
code path. Endpoints used:

* Recording by MBID: ``GET recording/{mbid}?fmt=json&inc=artists+releases+isrcs``
* ISRC lookup (enrich): ``GET isrc/{isrc}?fmt=json&inc=artists+releases``
* Recording search:     ``GET recording?query=<lucene>&fmt=json&limit=``

Two rules are enforced as **contract**:

* **Mandatory, descriptive User-Agent.** MusicBrainz rejects generic or empty
  User-Agent strings, so the client is built with ``ProviderContext.user_agent``
  (which already carries a contact URL). This is set explicitly on the client in
  :func:`build_musicbrainz_provider`.
* **1 request/second.** A provider-owned async limiter (:class:`_RateLimiter`,
  an :class:`asyncio.Lock` guarding a monotonic timestamp) guarantees at least
  ``1.0`` second between *outbound* MusicBrainz requests issued by a single
  provider instance. Every request path passes through :meth:`_get`, which
  acquires the limiter before calling :func:`request_json`.

Field mapping (JSON WS/2 shapes) -> :class:`Track`:

* ``title`` -> ``name``.
* ``artist-credit[].name`` (falling back to ``.artist.name``) -> ``artists``.
* ``length`` is **already milliseconds** -> ``duration_ms`` (never multiplied).
* ``isrcs[0]`` -- or, for an ISRC lookup, the looked-up ISRC -> ``isrc``.
* ``releases[0].title`` + ``releases[0].date[:4]`` -> :class:`AlbumRef`; the year
  falls back to ``first-release-date`` when no release is attached (the ISRC
  endpoint frequently omits releases).
* Search results carry a relevance ``score`` (older XML dumps used
  ``ext:score``); name-based enrichment accepts a match only at ``>= 80``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import AlbumRef, EntityType, ProviderId, Track
from spotdl_core.providers.base import HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, UnsupportedURL
from spotdl_core.providers.http import create_client, request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "MusicBrainzProvider",
    "build_musicbrainz_provider",
    "lucene_query",
    "map_recording",
    "map_search",
]

#: Base URL. The trailing slash is load-bearing: httpx joins request paths
#: relative to it (RFC 3986), so paths must be given without a leading slash to
#: preserve the ``/ws/2/`` prefix.
_API_BASE = "https://musicbrainz.org/ws/2/"

#: Include parameters requesting the sub-entities each endpoint needs.
_RECORDING_INC = "artists+releases+isrcs"
_ISRC_INC = "artists+releases"

#: Contract: minimum spacing between outbound MusicBrainz requests (seconds).
_MIN_INTERVAL = 1.0

#: Minimum relevance score accepted for a name-based (non-ISRC) match.
_MIN_NAME_SCORE = 80

#: Result cap for the internal name-search used by ``enrich``.
_ENRICH_LIMIT = 5


# --- rate limiter ---------------------------------------------------------


class _RateLimiter:
    """Serialise outbound requests to at most one per ``min_interval`` seconds.

    A single :class:`asyncio.Lock` both serialises acquirers and protects the
    ``_next_allowed`` monotonic timestamp, so concurrent callers within one
    provider instance are spaced correctly. ``clock`` and ``sleep`` are injected
    so tests can drive time deterministically and instantly while still
    verifying that the enforced gap is ``>= min_interval``.
    """

    def __init__(
        self,
        min_interval: float = _MIN_INTERVAL,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] | None = None,
    ) -> None:
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep or asyncio.sleep
        self._lock = asyncio.Lock()
        self._next_allowed: float | None = None

    async def acquire(self) -> None:
        """Block until the caller is allowed to issue the next request."""
        async with self._lock:
            now = self._clock()
            if self._next_allowed is not None and now < self._next_allowed:
                await self._sleep(self._next_allowed - now)
                now = self._clock()
            self._next_allowed = max(now, self._next_allowed or now) + self._min_interval


# --- pure mappers ---------------------------------------------------------


def _year(date: str | None) -> int | None:
    if not date:
        return None
    head = date[:4]
    return int(head) if head.isdigit() else None


def _artist_names(recording: dict[str, Any]) -> tuple[str, ...]:
    """Flatten ``artist-credit`` to ordered, de-duplicated artist names."""
    names: list[str] = []
    for credit in recording.get("artist-credit") or []:
        if not isinstance(credit, dict):
            continue
        name = credit.get("name") or (credit.get("artist") or {}).get("name")
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _album_ref(recording: dict[str, Any]) -> AlbumRef | None:
    releases = recording.get("releases") or []
    if not releases:
        return None
    release = releases[0]
    title = release.get("title")
    if not title:
        return None
    return AlbumRef(name=title, year=_year(release.get("date")))


def _isrc(recording: dict[str, Any], isrc: str | None) -> str | None:
    if isrc:
        return isrc
    isrcs = recording.get("isrcs") or []
    return isrcs[0] if isrcs else None


def map_recording(recording: dict[str, Any], *, isrc: str | None = None) -> Track:
    """Map a WS/2 recording object to a :class:`Track`.

    ``length`` is already milliseconds. ``isrc`` overrides the embedded
    ``isrcs`` list (used by ISRC lookups, whose recordings omit ``isrcs``).
    """
    album = _album_ref(recording)
    length = recording.get("length")
    year: int | None
    if album is not None and album.year is not None:
        year = album.year
    else:
        year = _year(recording.get("first-release-date"))
    return Track(
        name=recording["title"],
        artists=_artist_names(recording),
        duration_ms=int(length) if length is not None else 0,
        album=album,
        isrc=_isrc(recording, isrc),
        year=year,
        provider=ProviderId.MUSICBRAINZ,
        provider_id=str(recording.get("id") or ""),
    )


def _score(recording: dict[str, Any]) -> int:
    raw = recording.get("score", recording.get("ext:score", 0))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _mappable(recording: dict[str, Any]) -> bool:
    return bool(recording.get("title")) and bool(_artist_names(recording))


def map_search(payload: dict[str, Any], *, min_score: int | None = None) -> list[Track]:
    """Map a recording-search payload to tracks, skipping unmappable entries.

    When ``min_score`` is given, recordings below that relevance score are
    dropped (used by name-based enrichment; contract threshold is 80).
    """
    tracks: list[Track] = []
    for recording in payload.get("recordings") or []:
        if not isinstance(recording, dict) or not _mappable(recording):
            continue
        if min_score is not None and _score(recording) < min_score:
            continue
        tracks.append(map_recording(recording))
    return tracks


def _escape_lucene(value: str) -> str:
    """Escape characters that break a quoted Lucene phrase (``\\`` and ``"``)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def lucene_query(track: str, artist: str, album: str | None = None) -> str:
    """Build the Lucene query for a name lookup (contract-shaped)."""
    parts = [f'recording:"{_escape_lucene(track)}"', f'artist:"{_escape_lucene(artist)}"']
    if album:
        parts.append(f'release:"{_escape_lucene(album)}"')
    return " AND ".join(parts)


# --- provider -------------------------------------------------------------


class MusicBrainzProvider(HttpProvider):
    """Resolve/search/enrich against the open MusicBrainz web service.

    Implements :class:`~spotdl_core.providers.base.Resolves`,
    :class:`~spotdl_core.providers.base.Searches` and
    :class:`~spotdl_core.providers.base.Enriches`. All outbound requests are
    gated by a per-instance :class:`_RateLimiter` (>= 1 req/s, contract).
    """

    id: ClassVar[ProviderId] = ProviderId.MUSICBRAINZ

    def __init__(self, client: Any, *, limiter: _RateLimiter | None = None) -> None:
        super().__init__(client)
        self._limiter = limiter if limiter is not None else _RateLimiter(_MIN_INTERVAL)

    async def _get(self, path: str, **params: Any) -> Any:
        params.setdefault("fmt", "json")
        clean = {key: value for key, value in params.items() if value is not None}
        await self._limiter.acquire()
        return await request_json(
            self._client,
            "GET",
            path,
            provider=ProviderId.MUSICBRAINZ,
            params=clean,
        )

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is EntityType.TRACK:
            return await self._resolve_recording(ref.entity_id)
        # Only the recording (track) endpoint is in scope for this provider;
        # release/artist browsing is left to the richer metadata providers.
        raise UnsupportedURL(f"musicbrainz cannot resolve entity type {ref.entity_type}")

    async def _resolve_recording(self, mbid: str) -> ResolvedEntity:
        payload = await self._get(f"recording/{mbid}", inc=_RECORDING_INC)
        return ResolvedEntity(
            provider=ProviderId.MUSICBRAINZ,
            provider_id=str(payload.get("id") or mbid),
            entity_type=EntityType.TRACK,
            track=map_recording(payload),
        )

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        payload = await self._get("recording", query=query, limit=limit)
        return map_search(payload)

    async def enrich(self, track: Track) -> Track:
        fresh = await self._fresh_track(track)
        if fresh is None:
            return track
        updates: dict[str, Any] = {}
        if track.isrc is None and fresh.isrc is not None:
            updates["isrc"] = fresh.isrc
        if track.year is None and fresh.year is not None:
            updates["year"] = fresh.year
        if track.album is None and fresh.album is not None:
            updates["album"] = fresh.album
        return track.model_copy(update=updates) if updates else track

    async def _fresh_track(self, track: Track) -> Track | None:
        """Find the best MusicBrainz recording for ``track``.

        ISRC is the strongest key, so it is tried first; a miss (or absent ISRC)
        falls back to a name search filtered by the contract score threshold.
        """
        if track.isrc:
            try:
                recording = await self._lookup_isrc(track.isrc)
            except EntityNotFound:
                recording = None
            if recording is not None:
                return recording
        if not track.name or not track.artists:
            return None
        query = lucene_query(
            track.name, track.main_artist, track.album.name if track.album else None
        )
        payload = await self._get("recording", query=query, limit=_ENRICH_LIMIT)
        matches = map_search(payload, min_score=_MIN_NAME_SCORE)
        return matches[0] if matches else None

    async def _lookup_isrc(self, isrc: str) -> Track | None:
        payload = await self._get(f"isrc/{isrc}", inc=_ISRC_INC)
        recordings = payload.get("recordings") or []
        if not recordings:
            return None
        return map_recording(recordings[0], isrc=isrc)


# --- factory --------------------------------------------------------------


def build_musicbrainz_provider(ctx: ProviderContext) -> MusicBrainzProvider:
    """Construct a :class:`MusicBrainzProvider` from a :class:`ProviderContext`.

    The descriptive ``ctx.user_agent`` (contact URL included) is set explicitly
    on the client -- MusicBrainz rejects generic User-Agents (contract).
    """
    client = create_client(user_agent=ctx.user_agent, base_url=_API_BASE)
    return MusicBrainzProvider(client)
