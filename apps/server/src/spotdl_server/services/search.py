"""SearchService — universal free-text search with a durable snapshot cache.

The read side of ``GET /search`` (spec §Phase 2). A thin orchestration seam over
the shared fan-out helpers (the merge / de-dup rules are **not** re-implemented
here):

1. **Tracks** — delegate to
   :func:`~spotdl_server.services.provider_search.provider_search`, which fans out
   every ``Searches`` provider and yields rich :class:`Track` results (so the track
   preview keeps its full ``TrackView`` shape with album cover).
2. **Albums / artists / playlists** — delegate to
   :func:`~spotdl_server.services.provider_search.provider_search_entities`, which
   fans out every ``SearchesEntities`` provider and yields lightweight
   :class:`~spotdl_core.model.SearchHit` previews per type.
3. **Snapshot** every track/album/artist hit (``SnapshotRepository.upsert``) so a
   later ``POST /resolve`` of that provider ref is a cache hit — the permanent
   snapshot cache is the durable layer, so no separate query→results cache is
   needed. (Playlist hits are not snapshotted — a playlist's canonical row is its
   ordered listing, which a preview does not carry.)
4. Return a sectioned :class:`~spotdl_server.services.dto.SearchResult`.

Provider failures are non-fatal: the searchers that raised (from both helpers'
failed sets) unioned with the registry's construction failures
(``registry.unavailable``) become the sorted ``degraded_sources`` tuple (spec §10
"no silent fallbacks"). Empty groups return empty tuples — never an error.

Collaborators are injected; the service holds no FastAPI types and returns no ORM
rows. The unit of work is the caller's (the FastAPI ``get_session`` dependency or
a test fixture owns commit/rollback).
"""

from __future__ import annotations

from spotdl_core.model import EntityType, SearchHit, Track
from spotdl_core.providers import ProviderNotConfigured, ProviderRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.observability import record_provider_degraded
from spotdl_server.repositories.snapshots import PARTIAL_MARKER, SnapshotRepository
from spotdl_server.services.dto import AlbumView, ArtistView, PlaylistView, SearchResult, TrackView
from spotdl_server.services.provider_search import provider_search, provider_search_entities

#: The non-track entity groups sourced from the ``SearchesEntities`` fan-out
#: (tracks keep the rich ``provider_search`` path to preserve their full preview).
_ENTITY_TYPES: frozenset[EntityType] = frozenset(
    {EntityType.ALBUM, EntityType.ARTIST, EntityType.PLAYLIST}
)


class SearchService:
    """Fan-out universal search, snapshot the hits, return sectioned results."""

    def __init__(self, *, session: AsyncSession, registry: ProviderRegistry) -> None:
        self._session = session
        self._registry = registry
        self._snapshots = SnapshotRepository(session)

    async def search(self, query: str, *, limit: int = 20) -> SearchResult:
        """Search every capable provider, snapshot the hits, return sectioned results."""
        tracks, track_failed = await provider_search(self._registry, query, limit=limit)
        by_type, entity_failed = await provider_search_entities(
            self._registry, query, types=_ENTITY_TYPES, limit=limit
        )

        track_views = [await self._snapshot_and_view(track) for track in tracks]
        album_views = [await self._album_view(hit) for hit in by_type.get(EntityType.ALBUM, [])]
        artist_views = [await self._artist_view(hit) for hit in by_type.get(EntityType.ARTIST, [])]
        playlist_views = [self._playlist_view(hit) for hit in by_type.get(EntityType.PLAYLIST, [])]

        degraded = track_failed | entity_failed
        degraded |= {
            pid
            for pid, error in self._registry.unavailable.items()
            # Never-configured optional providers are a deliberate absence, not
            # an outage (see ResolveService) — they are not degraded sources.
            if not isinstance(error, ProviderNotConfigured)
        }
        sources = tuple(sorted(pid.value for pid in degraded))
        for provider in sources:
            record_provider_degraded(provider)
        return SearchResult(
            tracks=tuple(track_views),
            albums=tuple(album_views),
            artists=tuple(artist_views),
            playlists=tuple(playlist_views),
            degraded_sources=sources,
        )

    async def _album_view(self, hit: SearchHit) -> AlbumView:
        """Snapshot an album hit and map it to a lightweight preview ``AlbumView``.

        The snapshot (``entity_type=ALBUM``) makes a subsequent resolve of the
        provider ref a cache hit; its id is the preview's stable id. The album's
        ``subtitle`` is the album artist.
        """
        snapshot = await self._snapshots.upsert(
            provider=hit.provider,
            provider_entity_id=hit.provider_id,
            entity_type=EntityType.ALBUM,
            raw_payload={
                "name": hit.name,
                "album_artist": hit.subtitle,
                "year": hit.year,
                "cover_url": hit.cover_url,
            },
            name=hit.name,
            album_name=hit.name,
            art_url=hit.cover_url,
            # A hit is sparser than a full resolve — never clobber a rich snapshot.
            fill_only=True,
        )
        return AlbumView(
            id=str(snapshot.id),
            name=hit.name,
            album_artist=hit.subtitle,
            year=hit.year,
            cover_url=hit.cover_url,
            # Carry the source ref so the client resolves the preview into a
            # canonical album on open (the id is a snapshot id, not resolvable).
            provider=hit.provider.value,
            provider_id=hit.provider_id,
        )

    async def _artist_view(self, hit: SearchHit) -> ArtistView:
        """Snapshot an artist hit and map it to a lightweight preview ``ArtistView``.

        The snapshot (``entity_type=ARTIST``) makes a subsequent resolve of the
        provider ref a cache hit; its id is the preview's stable id.
        """
        snapshot = await self._snapshots.upsert(
            provider=hit.provider,
            provider_entity_id=hit.provider_id,
            entity_type=EntityType.ARTIST,
            raw_payload={"name": hit.name, "genres": [], "image_url": hit.cover_url},
            name=hit.name,
            art_url=hit.cover_url,
            # A hit is sparser than a full resolve — never clobber a rich snapshot.
            fill_only=True,
        )
        return ArtistView(
            id=str(snapshot.id),
            name=hit.name,
            image_url=hit.cover_url,
            # Carry the source ref so the client resolves the preview into a
            # canonical artist on open (the id is a snapshot id, not resolvable).
            provider=hit.provider.value,
            provider_id=hit.provider_id,
        )

    @staticmethod
    def _playlist_view(hit: SearchHit) -> PlaylistView:
        """Map a playlist hit to a lightweight preview ``PlaylistView``.

        Playlist hits are not snapshotted (a playlist's canonical row is its ordered
        listing, absent from a preview), so the id is the resolvable provider ref
        ``{provider}:playlist:{provider_id}``; ``subtitle`` is the owner.
        """
        return PlaylistView(
            id=f"{hit.provider.value}:{EntityType.PLAYLIST.value}:{hit.provider_id}",
            name=hit.name,
            owner=hit.subtitle,
            cover_url=hit.cover_url,
            provider=hit.provider.value,
            provider_id=hit.provider_id,
        )

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
            payload = track.model_dump(mode="json")
            # A search hit is a preview: mark it partial so the first direct open
            # does the authoritative fetch + cross-provider enrichment instead of
            # cache-hitting the hit (which would leave the track single-source
            # and, for Deezer/iTunes hits, ISRC-less).
            payload[PARTIAL_MARKER] = True
            snapshot = await self._snapshots.upsert(
                provider=track.provider,
                provider_entity_id=track.provider_id,
                entity_type=EntityType.TRACK,
                raw_payload=payload,
                name=track.name,
                isrc=track.isrc,
                duration_ms=track.duration_ms,
                artist_names=list(track.artists),
                album_name=track.album.name if track.album is not None else None,
                art_url=track.cover_url or (track.album.cover_url if track.album else None),
                fill_only=True,
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
