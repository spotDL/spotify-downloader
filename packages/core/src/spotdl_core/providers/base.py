"""Capability Protocols, ``ResolvedEntity``, and the ``HttpProvider`` base.

This module is the plugin contract shared by every provider (Tasks 6-11) and by
the registry (Task 5), and is consumed by Plans 3/5. Providers implement any
subset of the five runtime-checkable capability Protocols; the registry filters
providers by capability using ``isinstance`` checks against these Protocols.

``runtime_checkable`` verifies only the *presence* of the declared members, not
their signatures -- which is exactly what capability filtering needs. Every
capability Protocol inherits :class:`Provider`, so each also requires ``id``.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict

from spotdl_core.model import (
    AlbumRef,
    ArtistRef,
    AudioCandidate,
    EntityType,
    Lyrics,
    PlaylistRef,
    ProviderId,
    SearchHit,
    Track,
)
from spotdl_core.providers.urls import PlatformRef

#: Every entity type free-text search can return — the default request set for
#: :meth:`SearchesEntities.search_entities`.
ALL_SEARCH_ENTITY_TYPES: frozenset[EntityType] = frozenset(EntityType)

__all__ = [
    "ALL_SEARCH_ENTITY_TYPES",
    "Enriches",
    "HttpProvider",
    "Provider",
    "ProvidesAudio",
    "ProvidesLyrics",
    "ResolvedEntity",
    "Resolves",
    "Searches",
    "SearchesEntities",
]


class ResolvedEntity(BaseModel):
    """Provider-layer result of resolving one URL/ref. The populated fields
    depend on `entity_type`:
      TRACK    -> `track` set; `tracks` empty.
      ALBUM    -> `album` set; `tracks` = album track listing.
      ARTIST   -> `artist` set; `tracks` = top tracks (may be empty);
                  `albums` = the artist's discography (may be empty).
      PLAYLIST -> `playlist` set (name/description/owner/cover);
                  `tracks` = playlist track listing.
    """

    model_config = ConfigDict(frozen=True)

    provider: ProviderId
    provider_id: str
    entity_type: EntityType
    track: Track | None = None
    album: AlbumRef | None = None
    artist: ArtistRef | None = None
    playlist: PlaylistRef | None = None
    name: str | None = None
    tracks: tuple[Track, ...] = ()
    #: ARTIST only — the artist's discography as metadata-only album refs (each
    #: carrying its source ``provider``/``provider_id`` for resolve-on-open).
    albums: tuple[AlbumRef, ...] = ()


@runtime_checkable
class Provider(Protocol):
    """Every provider exposes its stable id."""

    id: ClassVar[ProviderId]


@runtime_checkable
class Resolves(Provider, Protocol):
    """URL / provider:type:id -> metadata."""

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity: ...


@runtime_checkable
class Searches(Provider, Protocol):
    """Free-text search -> tracks."""

    async def search(self, query: str, *, limit: int = 10) -> list[Track]: ...


@runtime_checkable
class SearchesEntities(Provider, Protocol):
    """Universal free-text search -> mixed entity previews (optional capability).

    Providers whose API can search across tracks, albums, artists and playlists
    implement this to power sectioned universal search (spec §Phase 2). ``types``
    selects which entity sections to return; a provider maps only the requested,
    supported sections and returns the flattened :class:`SearchHit` list (each
    section truncated to ``limit``). A provider without this capability stays
    track-only via :class:`Searches`; the fan-out layer synthesises track hits
    from its :meth:`Searches.search` results.
    """

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]: ...


@runtime_checkable
class Enriches(Provider, Protocol):
    """Return a copy of `track` with missing fields filled; never removes data."""

    async def enrich(self, track: Track) -> Track: ...


@runtime_checkable
class ProvidesAudio(Provider, Protocol):
    """Return downloadable audio candidates for a track (best-first)."""

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]: ...


@runtime_checkable
class ProvidesLyrics(Provider, Protocol):
    """Return lyrics for a track, or None if not found (None is not an error)."""

    async def lyrics(self, track: Track) -> Lyrics | None: ...


class HttpProvider:
    """Concrete base for providers backed by a single injected httpx client.
    The registry owns the client's lifetime and calls `aclose()`."""

    id: ClassVar[ProviderId]

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def aclose(self) -> None:
        await self._client.aclose()
