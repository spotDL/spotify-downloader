"""YouTube Music provider: audio candidates plus metadata resolve/search.

Backed by ``ytmusicapi``, a **synchronous** client. It is imported **lazily**
(inside :func:`_default_client`, never at module top level) so a broken install
degrades only this provider, and every blocking call is dispatched to a worker
thread via :func:`asyncio.to_thread`.

The mapping is split into pure functions (:func:`map_results`,
:func:`map_search_tracks`, :func:`map_song`, :func:`map_album`) that are unit
tested from checked-in fixtures, and thin fetch methods that only wrap the
library call. Two mapping rules are **contract**:

* **``verified`` follows ``resultType``.** A ``"song"`` result comes from
  YouTube Music's cleaned catalogue and is marked ``verified=True``; a
  ``"video"`` result is user-uploaded and is ``verified=False``.
* **Duration is an ``"m:ss"`` (or ``"h:mm:ss"``) string** and is converted to
  integer milliseconds.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import AlbumRef, AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.base import ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, UnsupportedURL

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "YTMusicClientFactory",
    "YTMusicProvider",
    "build_ytmusic_provider",
    "map_album",
    "map_results",
    "map_search_tracks",
    "map_song",
]

_WATCH_URL = "https://music.youtube.com/watch?v={video_id}"

#: A ``resultType`` value of ``"song"`` denotes a catalogue track (verified).
_SONG_RESULT_TYPE = "song"


def _duration_to_ms(text: str | None) -> int | None:
    """Convert a ``"m:ss"`` / ``"h:mm:ss"`` duration string to milliseconds.

    Returns ``None`` when the value is missing or not a colon-separated run of
    integers (YTMusic occasionally omits the field for unavailable items).
    """
    if not text:
        return None
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds * 1000


def _artist_names(payload: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        artist["name"]
        for artist in (payload.get("artists") or [])
        if isinstance(artist, dict) and artist.get("name")
    )


def _album_name(payload: dict[str, Any]) -> str | None:
    album = payload.get("album")
    if isinstance(album, dict):
        return album.get("name")
    if isinstance(album, str):
        return album
    return None


# --- pure mappers ---------------------------------------------------------


def map_results(raw: list[dict[str, Any]]) -> list[AudioCandidate]:
    """Map raw ``YTMusic.search`` results to audio candidates (best-first).

    Results without a ``videoId`` or ``title`` are skipped; a ``resultType`` of
    ``"song"`` sets ``verified=True`` (contract).
    """
    candidates: list[AudioCandidate] = []
    for item in raw:
        video_id = item.get("videoId")
        title = item.get("title")
        if not video_id or not title:
            continue
        candidates.append(
            AudioCandidate(
                provider=ProviderId.YTMUSIC,
                provider_id=video_id,
                url=_WATCH_URL.format(video_id=video_id),
                name=title,
                artists=_artist_names(item),
                duration_ms=_duration_to_ms(item.get("duration")),
                album=_album_name(item),
                verified=item.get("resultType") == _SONG_RESULT_TYPE,
                popularity=None,
            )
        )
    return candidates


def map_search_tracks(raw: list[dict[str, Any]]) -> list[Track]:
    """Map ``YTMusic.search`` song results to :class:`Track` objects.

    Skips results that cannot form a valid track (no id/title, no artist, or an
    unparseable duration) since :class:`Track` requires a duration and at least
    one artist.
    """
    tracks: list[Track] = []
    for item in raw:
        video_id = item.get("videoId")
        title = item.get("title")
        artists = _artist_names(item)
        duration_ms = _duration_to_ms(item.get("duration"))
        if not video_id or not title or not artists or duration_ms is None:
            continue
        album_name = _album_name(item)
        year = item.get("year")
        tracks.append(
            Track(
                name=title,
                artists=artists,
                duration_ms=duration_ms,
                album=AlbumRef(name=album_name) if album_name else None,
                year=int(year) if isinstance(year, str) and year.isdigit() else year,
                provider=ProviderId.YTMUSIC,
                provider_id=video_id,
            )
        )
    return tracks


def map_song(payload: dict[str, Any]) -> Track:
    """Map a ``get_song`` payload's ``videoDetails`` to a :class:`Track`.

    Raises :class:`EntityNotFound` if the required fields are absent (e.g. the
    video is unplayable). ``lengthSeconds`` is seconds -> milliseconds.
    """
    details = payload.get("videoDetails") or {}
    video_id = details.get("videoId")
    title = details.get("title")
    author = details.get("author")
    length = details.get("lengthSeconds")
    if not (video_id and title and author and length and str(length).isdigit()):
        raise EntityNotFound(provider=ProviderId.YTMUSIC)
    return Track(
        name=title,
        artists=(author,),
        duration_ms=int(length) * 1000,
        provider=ProviderId.YTMUSIC,
        provider_id=video_id,
    )


def map_album(payload: dict[str, Any], entity_id: str) -> ResolvedEntity:
    """Map a ``get_album`` payload to a resolved album with its track listing.

    The album context (name, album artist, year, track count) is injected onto
    every mapped track. Album tracks carry ``duration_seconds`` (seconds) and a
    ``trackNumber``.
    """
    title = payload.get("title")
    year = payload.get("year")
    year_int = int(year) if isinstance(year, str) and year.isdigit() else year
    artists = payload.get("artists") or []
    album_artist = artists[0]["name"] if artists and artists[0].get("name") else None
    album = (
        AlbumRef(
            name=title,
            album_artist=album_artist,
            year=year_int if isinstance(year_int, int) else None,
            track_count=payload.get("trackCount"),
        )
        if title
        else None
    )
    tracks: list[Track] = []
    for item in payload.get("tracks") or []:
        track = _map_album_track(item, album, album_artist, year_int)
        if track is not None:
            tracks.append(track)
    return ResolvedEntity(
        provider=ProviderId.YTMUSIC,
        provider_id=entity_id,
        entity_type=EntityType.ALBUM,
        album=album,
        name=title,
        tracks=tuple(tracks),
    )


def _map_album_track(
    item: dict[str, Any],
    album: AlbumRef | None,
    album_artist: str | None,
    year: int | None,
) -> Track | None:
    video_id = item.get("videoId")
    title = item.get("title")
    if not video_id or not title:
        return None
    artists = _artist_names(item)
    if not artists and album_artist:
        artists = (album_artist,)
    if not artists:
        return None
    seconds = item.get("duration_seconds")
    duration_ms = (
        int(seconds) * 1000 if isinstance(seconds, int) else _duration_to_ms(item.get("duration"))
    )
    if duration_ms is None:
        return None
    return Track(
        name=title,
        artists=artists,
        duration_ms=duration_ms,
        album=album,
        track_number=item.get("trackNumber"),
        year=year if isinstance(year, int) else None,
        provider=ProviderId.YTMUSIC,
        provider_id=video_id,
    )


# --- provider -------------------------------------------------------------

#: Builds a synchronous ``ytmusicapi`` client for a given language code.
YTMusicClientFactory = Callable[[str], Any]


def _default_client(language: str) -> Any:
    """Lazily import ``ytmusicapi`` and build a client (isolation constraint)."""
    from ytmusicapi import YTMusic

    return YTMusic(language=language)


class YTMusicProvider:
    """YouTube Music audio + metadata provider.

    Implements :class:`~spotdl_core.providers.base.ProvidesAudio`,
    :class:`~spotdl_core.providers.base.Resolves` and
    :class:`~spotdl_core.providers.base.Searches`. The underlying client is
    constructed on first use and its blocking calls run in a worker thread.
    """

    id: ClassVar[ProviderId] = ProviderId.YTMUSIC

    def __init__(
        self,
        *,
        language: str = "en",
        client_factory: YTMusicClientFactory = _default_client,
    ) -> None:
        self._language = language
        self._client_factory = client_factory
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory(self._language)
        return self._client

    async def _search(self, query: str, result_filter: str, limit: int) -> list[dict[str, Any]]:
        client = self._get_client()
        results = await asyncio.to_thread(client.search, query, filter=result_filter, limit=limit)
        return list(results or [])

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        query = f"{track.main_artist} - {track.name}"
        songs = await self._search(query, "songs", limit)
        candidates = map_results(songs)
        if len(candidates) < limit:
            videos = await self._search(query, "videos", limit)
            seen = {candidate.provider_id for candidate in candidates}
            for candidate in map_results(videos):
                if candidate.provider_id not in seen:
                    candidates.append(candidate)
                    seen.add(candidate.provider_id)
        return candidates[:limit]

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        songs = await self._search(query, "songs", limit)
        return map_search_tracks(songs)

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        client = self._get_client()
        if ref.entity_type is EntityType.TRACK:
            payload = await asyncio.to_thread(client.get_song, ref.entity_id)
            return ResolvedEntity(
                provider=ProviderId.YTMUSIC,
                provider_id=ref.entity_id,
                entity_type=EntityType.TRACK,
                track=map_song(payload),
            )
        if ref.entity_type is EntityType.ALBUM:
            payload = await asyncio.to_thread(client.get_album, ref.entity_id)
            return map_album(payload, ref.entity_id)
        raise UnsupportedURL(f"ytmusic cannot resolve entity type {ref.entity_type}")


# --- factory --------------------------------------------------------------


def build_ytmusic_provider(ctx: ProviderContext) -> YTMusicProvider:
    """Construct a :class:`YTMusicProvider` from a :class:`ProviderContext`.

    The ``ytmusicapi`` import happens lazily on first client use, so building
    the provider (and therefore registry construction) never imports the
    library.
    """
    return YTMusicProvider(language=ctx.ytmusic_language)
