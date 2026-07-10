"""Deezer metadata provider (open API, no authentication).

Deezer's public API at ``https://api.deezer.com`` requires no key. Two quirks
drive the mapping and are enforced here as **contract**:

* **Duration is in seconds.** The ``duration`` field is seconds; the domain
  model stores milliseconds, so every mapped track multiplies by ``1000``.
* **"Not found" is an HTTP 200.** Deezer returns ``200 OK`` with a body of
  ``{"error": {"message": ...}}`` instead of a 404. An ``expect_ok_body``
  callback handed to :func:`request_json` translates that into
  :class:`EntityNotFound`.

Album listings (``/album/{id}`` -> ``tracks.data[]``) contain only *simplified*
track objects that omit ISRC, track/disc position and contributors, so the
provider re-fetches each ``/track/{id}`` for the full fields (in parallel).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import AlbumRef, ArtistRef, EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers.base import ALL_SEARCH_ENTITY_TYPES, HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, UnsupportedURL
from spotdl_core.providers.http import create_client, request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "DeezerProvider",
    "build_deezer_provider",
    "map_album",
    "map_album_hits",
    "map_artist_hits",
    "map_playlist_hits",
    "map_search",
    "map_track_hits",
    "map_track",
]

_API_BASE = "https://api.deezer.com"

#: Deezer caps ``/artist/{id}/top`` and search at 100 items per request.
_TOP_LIMIT = 100


def _expect_no_error(body: Any) -> None:
    """Raise :class:`EntityNotFound` for Deezer's HTTP-200 error envelope."""
    if isinstance(body, dict) and body.get("error"):
        raise EntityNotFound(provider=ProviderId.DEEZER)


# --- pure mappers ---------------------------------------------------------


def _year(release_date: str | None) -> int | None:
    if not release_date:
        return None
    head = release_date[:4]
    return int(head) if head.isdigit() else None


def _artist_names(payload: dict[str, Any]) -> tuple[str, ...]:
    """Main artist followed by contributors, de-duplicated, order preserved."""
    names: list[str] = []
    main = (payload.get("artist") or {}).get("name")
    if main:
        names.append(main)
    for contributor in payload.get("contributors") or []:
        name = contributor.get("name")
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _genre_names(album_payload: dict[str, Any]) -> tuple[str, ...]:
    """Genre names from ``/album`` ``genres.data[]`` (absent on album refs)."""
    data = (album_payload.get("genres") or {}).get("data") or []
    return tuple(g["name"] for g in data if isinstance(g, dict) and g.get("name"))


def _album_ref(album_payload: dict[str, Any]) -> AlbumRef | None:
    title = album_payload.get("title")
    if not title:
        return None
    # ``label``/``genres``/``record_type``/``fans`` are present only on the full
    # ``/album/{id}`` object, not on the simplified album embedded in a track — they
    # fall back to ``None``/``()`` there.
    return AlbumRef(
        name=title,
        album_artist=(album_payload.get("artist") or {}).get("name"),
        year=_year(album_payload.get("release_date")),
        track_count=album_payload.get("nb_tracks"),
        cover_url=album_payload.get("cover_xl") or album_payload.get("cover_big"),
        label=album_payload.get("label"),
        album_type=album_payload.get("record_type"),
        popularity=album_payload.get("fans"),
        genres=_genre_names(album_payload),
    )


def map_track(payload: dict[str, Any]) -> Track:
    """Map a ``/track/{id}`` (or search) object to a :class:`Track`."""
    album_payload = payload.get("album")
    album = _album_ref(album_payload) if album_payload else None
    return Track(
        name=payload["title"],
        artists=_artist_names(payload),
        duration_ms=int(payload["duration"]) * 1000,
        album=album,
        isrc=payload.get("isrc"),
        explicit=payload.get("explicit_lyrics"),
        track_number=payload.get("track_position"),
        disc_number=payload.get("disk_number"),
        year=album.year if album else None,
        provider=ProviderId.DEEZER,
        provider_id=str(payload["id"]),
    )


def map_album(
    album_payload: dict[str, Any], track_payloads: list[dict[str, Any]]
) -> ResolvedEntity:
    """Map an album plus its re-fetched full track objects to a resolved album.

    The album context (which carries ``track_count`` and ``album_artist`` only
    available on the ``/album`` endpoint) is injected onto every track.
    """
    album = _album_ref(album_payload)
    album_year = album.year if album else None
    tracks = tuple(
        map_track(payload).model_copy(update={"album": album, "year": album_year})
        for payload in track_payloads
    )
    return ResolvedEntity(
        provider=ProviderId.DEEZER,
        provider_id=str(album_payload["id"]),
        entity_type=EntityType.ALBUM,
        album=album,
        name=album_payload.get("title"),
        tracks=tracks,
    )


def map_search(payload: dict[str, Any]) -> list[Track]:
    """Map a ``/search/track`` payload to a list of :class:`Track`."""
    return [map_track(item) for item in (payload.get("data") or []) if item]


def _cover(payload: dict[str, Any], *keys: str) -> str | None:
    """First present, non-empty image URL across ``keys`` (largest-first)."""
    for key in keys:
        value = payload.get(key)
        if value:
            return value if isinstance(value, str) else None
    return None


def map_track_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``/search/track`` payload to track :class:`SearchHit`\\ s."""
    return [SearchHit.from_track(track) for track in map_search(payload)]


def map_album_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``/search/album`` payload to album :class:`SearchHit`\\ s.

    Deezer's album-search items carry no ``release_date``, so ``year`` is ``None``.
    """
    hits: list[SearchHit] = []
    for item in payload.get("data") or []:
        if not item or not item.get("id") or not item.get("title"):
            continue
        hits.append(
            SearchHit(
                entity_type=EntityType.ALBUM,
                provider=ProviderId.DEEZER,
                provider_id=str(item["id"]),
                name=item["title"],
                subtitle=(item.get("artist") or {}).get("name"),
                cover_url=_cover(item, "cover_xl", "cover_big", "cover"),
            )
        )
    return hits


def map_artist_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``/search/artist`` payload to artist :class:`SearchHit`\\ s."""
    hits: list[SearchHit] = []
    for item in payload.get("data") or []:
        if not item or not item.get("id") or not item.get("name"):
            continue
        hits.append(
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.DEEZER,
                provider_id=str(item["id"]),
                name=item["name"],
                subtitle=None,
                cover_url=_cover(item, "picture_xl", "picture_big", "picture"),
            )
        )
    return hits


def map_playlist_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``/search/playlist`` payload to playlist :class:`SearchHit`\\ s."""
    hits: list[SearchHit] = []
    for item in payload.get("data") or []:
        if not item or not item.get("id") or not item.get("title"):
            continue
        hits.append(
            SearchHit(
                entity_type=EntityType.PLAYLIST,
                provider=ProviderId.DEEZER,
                provider_id=str(item["id"]),
                name=item["title"],
                subtitle=(item.get("user") or {}).get("name"),
                cover_url=_cover(item, "picture_xl", "picture_big", "picture"),
            )
        )
    return hits


# --- provider -------------------------------------------------------------


class DeezerProvider(HttpProvider):
    """Resolve/search/enrich against the open Deezer API.

    Implements :class:`~spotdl_core.providers.base.Resolves`,
    :class:`~spotdl_core.providers.base.Searches`,
    :class:`~spotdl_core.providers.base.SearchesEntities` and
    :class:`~spotdl_core.providers.base.Enriches`.
    """

    id: ClassVar[ProviderId] = ProviderId.DEEZER

    #: Per-entity ``/search/{path}`` endpoint + item→hit mapper, in stable order.
    _SEARCH_ENDPOINTS: ClassVar[
        tuple[tuple[EntityType, str, Callable[[dict[str, Any]], list[SearchHit]]], ...]
    ] = (
        (EntityType.TRACK, "track", map_track_hits),
        (EntityType.ALBUM, "album", map_album_hits),
        (EntityType.ARTIST, "artist", map_artist_hits),
        (EntityType.PLAYLIST, "playlist", map_playlist_hits),
    )

    async def _get(self, path: str, **params: Any) -> Any:
        return await request_json(
            self._client,
            "GET",
            path,
            provider=ProviderId.DEEZER,
            expect_ok_body=_expect_no_error,
            params=params or None,
        )

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is EntityType.TRACK:
            return await self._resolve_track(ref.entity_id)
        if ref.entity_type is EntityType.ALBUM:
            return await self._resolve_album(ref.entity_id)
        if ref.entity_type is EntityType.ARTIST:
            return await self._resolve_artist(ref.entity_id)
        if ref.entity_type is EntityType.PLAYLIST:
            return await self._resolve_playlist(ref.entity_id)
        raise UnsupportedURL(f"deezer cannot resolve entity type {ref.entity_type}")

    async def _resolve_track(self, entity_id: str) -> ResolvedEntity:
        payload = await self._get(f"/track/{entity_id}")
        return ResolvedEntity(
            provider=ProviderId.DEEZER,
            provider_id=entity_id,
            entity_type=EntityType.TRACK,
            track=map_track(payload),
        )

    async def _resolve_album(self, entity_id: str) -> ResolvedEntity:
        album = await self._get(f"/album/{entity_id}")
        entries = (album.get("tracks") or {}).get("data") or []
        track_ids = [entry["id"] for entry in entries if entry.get("id") is not None]
        full_tracks = await asyncio.gather(
            *(self._get(f"/track/{track_id}") for track_id in track_ids)
        )
        return map_album(album, list(full_tracks))

    async def _resolve_artist(self, entity_id: str) -> ResolvedEntity:
        artist = await self._get(f"/artist/{entity_id}")
        top = await self._get(f"/artist/{entity_id}/top", limit=_TOP_LIMIT)
        tracks = tuple(map_track(item) for item in (top.get("data") or []) if item)
        name = artist.get("name")
        return ResolvedEntity(
            provider=ProviderId.DEEZER,
            provider_id=entity_id,
            entity_type=EntityType.ARTIST,
            artist=(
                ArtistRef(
                    name=name,
                    provider=ProviderId.DEEZER,
                    provider_id=entity_id,
                    image_url=_cover(artist, "picture_xl", "picture_big", "picture"),
                    followers=artist.get("nb_fan"),
                )
                if name
                else None
            ),
            name=name,
            tracks=tracks,
        )

    async def _resolve_playlist(self, entity_id: str) -> ResolvedEntity:
        playlist = await self._get(f"/playlist/{entity_id}")
        entries = (playlist.get("tracks") or {}).get("data") or []
        tracks = tuple(map_track(item) for item in entries if item and item.get("id"))
        return ResolvedEntity(
            provider=ProviderId.DEEZER,
            provider_id=entity_id,
            entity_type=EntityType.PLAYLIST,
            name=playlist.get("title"),
            tracks=tracks,
        )

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        payload = await self._get("/search/track", q=query, limit=limit)
        return map_search(payload)

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Universal search: one ``/search/{type}`` request per type, concurrently."""
        requested = [
            (entity_type, path, mapper)
            for entity_type, path, mapper in self._SEARCH_ENDPOINTS
            if entity_type in types
        ]
        if not requested:
            return []
        payloads = await asyncio.gather(
            *(self._get(f"/search/{path}", q=query, limit=limit) for _, path, _ in requested)
        )
        hits: list[SearchHit] = []
        for (_, _, mapper), payload in zip(requested, payloads, strict=True):
            hits.extend(mapper(payload)[:limit])
        return hits

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
        elif (
            track.album is not None
            and fresh.album is not None
            and track.album.cover_url is None
            and fresh.album.cover_url is not None
        ):
            updates["album"] = track.album.model_copy(update={"cover_url": fresh.album.cover_url})
        return track.model_copy(update=updates) if updates else track

    async def _fresh_track(self, track: Track) -> Track | None:
        """Fetch the best Deezer track for ``track`` (by id, else by search)."""
        if track.provider is ProviderId.DEEZER and track.provider_id:
            payload = await self._get(f"/track/{track.provider_id}")
            return map_track(payload)
        results = await self.search(f"{track.main_artist} {track.name}", limit=1)
        return results[0] if results else None


# --- factory --------------------------------------------------------------


def build_deezer_provider(ctx: ProviderContext) -> DeezerProvider:
    """Construct a :class:`DeezerProvider` from a :class:`ProviderContext`."""
    client = create_client(user_agent=ctx.user_agent, base_url=_API_BASE)
    return DeezerProvider(client)
