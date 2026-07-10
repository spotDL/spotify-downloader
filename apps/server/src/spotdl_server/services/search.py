"""SearchService — free-text search fan-out with a durable snapshot cache.

The read side of ``GET /search`` (spec §6.2). A thin orchestration seam over the
shared :func:`~spotdl_server.services.provider_search.provider_search` helper
(Task 8 — the fan-out / merge / de-dup rule is **not** re-implemented here):

1. Delegate the multi-provider search + de-dup + truncate to ``provider_search``.
2. **Snapshot** every result track (``SnapshotRepository.upsert``) so a later
   ``POST /resolve`` of that provider ref is a cache hit — the permanent snapshot
   cache is the durable layer, so no separate query→results cache is needed.
3. Return a plain :class:`~spotdl_server.services.dto.SearchResult` (a ranked
   ``TrackView`` tuple + ``degraded_sources``).

Provider failures are non-fatal: a searcher that raised (from the helper's failed
set) unioned with the registry's construction failures (``registry.unavailable``)
becomes the sorted ``degraded_sources`` tuple (spec §10 "no silent fallbacks").
Empty results return an empty tuple — never an error.

Collaborators are injected; the service holds no FastAPI types and returns no ORM
rows. The unit of work is the caller's (the FastAPI ``get_session`` dependency or
a test fixture owns commit/rollback).
"""

from __future__ import annotations

from spotdl_core.model import EntityType, Track
from spotdl_core.providers import ProviderRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.observability import record_provider_degraded
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.dto import AlbumView, SearchResult, TrackView
from spotdl_server.services.provider_search import provider_search


class SearchService:
    """Fan-out free-text search, snapshot the hits, return a ranked track list."""

    def __init__(self, *, session: AsyncSession, registry: ProviderRegistry) -> None:
        self._session = session
        self._registry = registry
        self._snapshots = SnapshotRepository(session)

    async def search(self, query: str, *, limit: int = 20) -> SearchResult:
        """Search every capable provider, snapshot the hits, return the results."""
        tracks, failed = await provider_search(self._registry, query, limit=limit)

        views: list[TrackView] = []
        for track in tracks:
            views.append(await self._snapshot_and_view(track))

        degraded = failed | set(self._registry.unavailable.keys())
        sources = tuple(sorted(pid.value for pid in degraded))
        for provider in sources:
            record_provider_degraded(provider)
        return SearchResult(tracks=tuple(views), degraded_sources=sources)

    async def _snapshot_and_view(self, track: Track) -> TrackView:
        """Persist a search hit as a snapshot (when it carries a provider ref) and
        map it to a preview :class:`TrackView`.

        The snapshot's id is the view's stable id — a search hit is a cached
        provider snapshot, not a canonical merged entity (resolve does the merge).
        A track without a provider ref cannot be keyed/cached, so it gets no
        snapshot; it still appears in the results as a preview.
        """
        snapshot_id: str | None = None
        if track.provider is not None and track.provider_id is not None:
            snapshot = await self._snapshots.upsert(
                provider=track.provider,
                provider_entity_id=track.provider_id,
                entity_type=EntityType.TRACK,
                raw_payload=track.model_dump(mode="json"),
                name=track.name,
                isrc=track.isrc,
                duration_ms=track.duration_ms,
                artist_names=list(track.artists),
                album_name=track.album.name if track.album is not None else None,
                art_url=track.cover_url or (track.album.cover_url if track.album else None),
            )
            snapshot_id = str(snapshot.id)
        return self._track_view(track, id=snapshot_id or _ref_id(track))

    @staticmethod
    def _track_view(track: Track, *, id: str) -> TrackView:
        """Map a core :class:`Track` (a search hit) to a preview ``TrackView``.

        ``matches`` / ``lyrics`` are empty — a search hit is a lightweight preview;
        the client resolves it for the full canonical graph. The provider hit's
        ``album`` (metadata only, no listing) is carried through when present so the
        result cards can render cover art without a per-hit resolve.
        """
        album = track.album
        album_meta = (
            AlbumView(
                id="",  # preview: not a canonical row yet (resolve mints the id)
                name=album.name,
                album_artist=album.album_artist,
                year=album.year,
                track_count=album.track_count,
                cover_url=album.cover_url,
            )
            if album is not None
            else None
        )
        return TrackView(
            id=id,
            name=track.name,
            artists=tuple(track.artists),
            duration_ms=track.duration_ms,
            isrc=track.isrc,
            explicit=track.explicit,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=track.year,
            genres=tuple(track.genres),
            popularity=track.popularity,
            album=album_meta,
            provider=track.provider.value if track.provider is not None else None,
            provider_id=track.provider_id,
        )


def _ref_id(track: Track) -> str:
    """A stable non-persistent id for a hit that could not be snapshotted.

    Real searchers always carry a provider ref (so the hit is resolvable); this
    is a defensive fallback for a ref-less hit, keyed on its identity so the same
    hit is stable within a result set.
    """
    provider = track.provider.value if track.provider is not None else "unknown"
    return f"{provider}:{track.provider_id or track.name}"
