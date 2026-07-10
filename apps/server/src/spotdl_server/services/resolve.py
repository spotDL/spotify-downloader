"""ResolveService — cache-first resolve → snapshot → merge → canonical → match.

The read side of ``POST /resolve`` (spec §6.2). Orchestrates the provider
registry, the snapshot cache, the deterministic canonical merger, and the
matcher into one unit of work:

1. **Parse** the query (URL / ``provider:type:id``); on failure treat it as free
   text and search, resolving the best-matching track.
2. **Cache-first** — a fresh snapshot for the ref skips the network fetch.
3. **Fetch + snapshot** the primary provider's ``ResolvedEntity`` (failures are
   recorded in ``degraded_sources``, never silently dropped — spec §10).
4. **Merge** the full snapshot set for the entity into a canonical row.
5. **Kick matching** for tracks: gather audio candidates from every audio
   provider, rank via ``match()``, persist. (Album/playlist bulk matching is
   Plan 7's queue — deliberately not kicked per-track here.)

Collaborators are injected (``session``, ``registry``, ``matcher_config``) — the
service holds no FastAPI types and its public output is a plain
:class:`~spotdl_server.services.dto.ResolveResult` (no ORM rows cross the
boundary). The unit of work is the caller's: repositories flush, and the FastAPI
``get_session`` dependency (or a test's session fixture) owns commit/rollback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from spotdl_core.matching import MATCHER_V5_DEFAULT, ScoringConfig, match
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    EntityType,
    ProviderId,
    Track,
)
from spotdl_core.providers import (
    PlatformRef,
    ProviderError,
    ProviderRegistry,
    ProviderUnavailable,
    ProvidesAudio,
    ResolvedEntity,
    Resolves,
    UnsupportedURL,
    parse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import (
    ProviderSnapshot,
)
from spotdl_server.db.models import (
    Track as TrackModel,
)
from spotdl_server.observability import (
    record_cache_hit,
    record_cache_miss,
    record_match_served,
    record_provider_degraded,
    record_provider_error,
)
from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
)
from spotdl_server.repositories.links import EntityLinkRepository
from spotdl_server.repositories.lyrics import LyricsRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.repositories.merge import CanonicalMerger
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services import views
from spotdl_server.services.dto import ResolveResult
from spotdl_server.services.provider_search import provider_search


class ResolveService:
    """Cache-first resolve of a query to a canonical entity + kicked matches."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        registry: ProviderRegistry,
        matcher_config: ScoringConfig = MATCHER_V5_DEFAULT,
    ) -> None:
        self._session = session
        self._registry = registry
        self._matcher_config = matcher_config
        self._snapshots = SnapshotRepository(session)
        self._links = EntityLinkRepository(session)
        self._matches = MatchRepository(session)
        self._lyrics = LyricsRepository(session)
        self._albums = AlbumRepository(session)
        self._artists = ArtistRepository(session)
        self._playlists = PlaylistRepository(session)
        self._merger = CanonicalMerger(session)

    async def resolve(self, query: str) -> ResolveResult:
        """Resolve ``query`` to a canonical entity view + ``degraded_sources``."""
        degraded: set[ProviderId] = set()
        ref = await self._parse_or_search(query, degraded)

        if ref.entity_type is EntityType.TRACK:
            result = await self._resolve_track(ref, degraded)
        else:
            result = await self._resolve_container(ref, degraded)

        degraded.update(self._registry.unavailable.keys())
        return self._with_degraded(result, degraded)

    # --------------------------------------------------------------- parsing
    async def _parse_or_search(self, query: str, degraded: set[ProviderId]) -> PlatformRef:
        """Parse ``query``; on ``UnsupportedURL`` fall back to free-text search.

        The top search result's provider ref becomes the ref to resolve. When
        the search yields nothing (or no usable provider ref), the original
        ``UnsupportedURL`` is re-raised.
        """
        try:
            return parse(query)
        except UnsupportedURL:
            tracks, failed = await provider_search(self._registry, query)
            degraded.update(failed)
            for track in tracks:
                if track.provider is not None and track.provider_id is not None:
                    return PlatformRef(
                        provider=track.provider,
                        entity_type=EntityType.TRACK,
                        entity_id=track.provider_id,
                    )
            raise

    # ----------------------------------------------------------------- track
    async def _resolve_track(self, ref: PlatformRef, degraded: set[ProviderId]) -> ResolveResult:
        now = datetime.now(UTC)
        primary = await self._snapshots.get_fresh(ref.provider, ref.entity_id, now)
        if primary is None:  # cache miss → fetch + snapshot
            record_cache_miss("snapshot")
            resolved = await self._fetch_primary(ref)
            assert resolved.track is not None  # _fetch_primary guarantees a track
            primary = await self._persist_track_snapshot(
                resolved.provider, resolved.provider_id, resolved.track
            )
        else:
            record_cache_hit("snapshot")

        merge_set = await self._merge_set(primary)
        track = await self._merger.merge_track(merge_set)
        await self._kick_matching(track, degraded)

        match_rows = await self._matches.list_for_track(track.id)
        lyrics_rows = await self._lyrics.list_for_track(track.id)
        view = views.track_view(track, matches=match_rows, lyrics=lyrics_rows, include_album=True)
        return ResolveResult(entity_type=EntityType.TRACK.value, track=view)

    async def _fetch_primary(self, ref: PlatformRef) -> ResolvedEntity:
        """Resolve ``ref`` via its owning provider.

        A ``KeyError`` (the id parses to a provider the registry never
        registered) is mapped to :class:`ProviderUnavailable` so it reaches the
        client as a 502 ``provider_unavailable`` envelope, not a 500. A provider
        that is registered but unavailable, or that raises resolving, is the
        sole source for this ref — there is no fallback, so it propagates.
        """
        try:
            provider = self._registry.get(ref.provider)
        except KeyError as exc:
            raise ProviderUnavailable(
                f"no provider registered for {ref.provider.value}", provider=ref.provider
            ) from exc
        if not isinstance(provider, Resolves):
            raise ProviderUnavailable(
                f"{ref.provider.value} cannot resolve entities", provider=ref.provider
            )
        resolved = await provider.resolve(ref)
        if resolved.track is None:
            raise ProviderUnavailable(
                f"{ref.provider.value} returned no track for {ref.entity_id}",
                provider=ref.provider,
            )
        return resolved

    async def _kick_matching(self, track: TrackModel, degraded: set[ProviderId]) -> None:
        """Rank audio candidates for ``track`` and replace its AUTO matches.

        Every ``ProvidesAudio`` provider is queried; a failure records the
        provider in ``degraded`` and is never fatal. ``replace_for_track`` swaps
        in the fresh ranking while preserving community-voted rows.
        """
        core = self._core_track(track)
        if core is None:  # a stub with no artists cannot be matched
            return
        candidates: list[AudioCandidate] = []
        for provider in self._registry.capable(ProvidesAudio):  # type: ignore[type-abstract]
            try:
                candidates.extend(await provider.audio_candidates(core))
            except ProviderError:
                degraded.add(provider.id)
                record_provider_error(provider.id.value)
        ranked = match(core, candidates, self._matcher_config)
        await self._matches.replace_for_track(
            track.id, ranked, self._matcher_config.matcher_version
        )
        record_match_served(self._matcher_config.matcher_version)

    # ------------------------------------------------------------- container
    async def _resolve_container(
        self, ref: PlatformRef, degraded: set[ProviderId]
    ) -> ResolveResult:
        """Resolve an album/artist/playlist ref (no per-track match kick).

        Cache-first: a fresh snapshot already merged into a canonical entity is
        reloaded without any network call. Otherwise the entity and its track
        listing are fetched, snapshotted, and merged.
        """
        now = datetime.now(UTC)
        fresh = await self._snapshots.get_fresh(ref.provider, ref.entity_id, now)
        if fresh is not None:
            existing = await self._existing_container(fresh)
            if existing is not None:
                record_cache_hit("snapshot")
                return existing

        record_cache_miss("snapshot")
        resolved = await self._fetch_container(ref)
        return await self._merge_container(resolved)

    async def _fetch_container(self, ref: PlatformRef) -> ResolvedEntity:
        try:
            provider = self._registry.get(ref.provider)
        except KeyError as exc:
            raise ProviderUnavailable(
                f"no provider registered for {ref.provider.value}", provider=ref.provider
            ) from exc
        if not isinstance(provider, Resolves):
            raise ProviderUnavailable(
                f"{ref.provider.value} cannot resolve entities", provider=ref.provider
            )
        return await provider.resolve(ref)

    async def _merge_container(self, resolved: ResolvedEntity) -> ResolveResult:
        if resolved.entity_type is EntityType.ALBUM:
            album_snap = await self._persist_album_snapshot(resolved)
            by_pos = {
                index: [await self._persist_track_snapshot_from(resolved, index, track)]
                for index, track in enumerate(resolved.tracks)
            }
            album = await self._merger.merge_album([album_snap], by_pos)
            return ResolveResult(entity_type=EntityType.ALBUM.value, album=views.album_view(album))
        if resolved.entity_type is EntityType.ARTIST:
            artist_snap = await self._persist_artist_snapshot(resolved)
            by_pos = {
                index: [await self._persist_track_snapshot_from(resolved, index, track)]
                for index, track in enumerate(resolved.tracks)
            }
            artist = await self._merger.merge_artist([artist_snap], by_pos)
            return ResolveResult(
                entity_type=EntityType.ARTIST.value, artist=views.artist_view(artist)
            )
        # PLAYLIST
        playlist_snap = await self._persist_playlist_snapshot(resolved)
        ordered = [
            [await self._persist_track_snapshot_from(resolved, index, track)]
            for index, track in enumerate(resolved.tracks)
        ]
        playlist = await self._merger.merge_playlist([playlist_snap], ordered)
        return ResolveResult(
            entity_type=EntityType.PLAYLIST.value, playlist=views.playlist_view(playlist)
        )

    async def _existing_container(self, fresh: ProviderSnapshot) -> ResolveResult | None:
        """Reload an already-merged album/artist/playlist from a fresh snapshot."""
        located = await self._links.entity_for_snapshot(fresh.id)
        if located is None:
            return None
        entity_type, entity_id = located
        if entity_type is EntityType.ALBUM:
            album = await self._albums.get(entity_id)
            if album is not None:
                return ResolveResult(entity_type=entity_type.value, album=views.album_view(album))
        elif entity_type is EntityType.ARTIST:
            artist = await self._artists.get(entity_id)
            if artist is not None:
                return ResolveResult(
                    entity_type=entity_type.value, artist=views.artist_view(artist)
                )
        elif entity_type is EntityType.PLAYLIST:
            playlist = await self._playlists.get(entity_id)
            if playlist is not None:
                return ResolveResult(
                    entity_type=entity_type.value, playlist=views.playlist_view(playlist)
                )
        return None

    # --------------------------------------------------------- snapshot I/O
    async def _merge_set(self, primary: ProviderSnapshot) -> list[ProviderSnapshot]:
        """The full snapshot set for the entity ``primary`` belongs to.

        When ``primary`` is already merged, the complete provenance set is
        returned so the re-merge is order-independent; otherwise just ``primary``
        (a brand-new or seeded-but-unmerged snapshot).
        """
        located = await self._links.entity_for_snapshot(primary.id)
        if located is None:
            return [primary]
        entity_type, entity_id = located
        linked = await self._snapshots.list_for_entity(entity_type, entity_id)
        return linked or [primary]

    async def _persist_track_snapshot(
        self, provider: ProviderId, provider_entity_id: str, track: Track
    ) -> ProviderSnapshot:
        return await self._snapshots.upsert(
            provider=provider,
            provider_entity_id=provider_entity_id,
            entity_type=EntityType.TRACK,
            raw_payload=track.model_dump(mode="json"),
            name=track.name,
            isrc=track.isrc,
            duration_ms=track.duration_ms,
            artist_names=list(track.artists),
            album_name=track.album.name if track.album is not None else None,
            art_url=track.cover_url or (track.album.cover_url if track.album else None),
        )

    async def _persist_track_snapshot_from(
        self, container: ResolvedEntity, index: int, track: Track
    ) -> ProviderSnapshot:
        """Snapshot a listing track, synthesising a stable id when it lacks one."""
        provider = track.provider or container.provider
        provider_id = track.provider_id or f"{container.provider_id}::{index}"
        return await self._persist_track_snapshot(provider, provider_id, track)

    async def _persist_album_snapshot(self, resolved: ResolvedEntity) -> ProviderSnapshot:
        album = resolved.album
        payload: dict[str, Any] = album.model_dump(mode="json") if album is not None else {}
        payload.setdefault("name", resolved.name)
        return await self._snapshots.upsert(
            provider=resolved.provider,
            provider_entity_id=resolved.provider_id,
            entity_type=EntityType.ALBUM,
            raw_payload=payload,
            name=(album.name if album is not None else resolved.name),
            album_name=(album.name if album is not None else resolved.name),
            art_url=album.cover_url if album is not None else None,
        )

    async def _persist_artist_snapshot(self, resolved: ResolvedEntity) -> ProviderSnapshot:
        artist = resolved.artist
        name = artist.name if artist is not None else resolved.name
        # Serialize the full ``ArtistRef`` (image_url/genres/followers/popularity/bio)
        # into ``raw_payload`` under the keys the merger reads (``_image_url``,
        # ``_genres``, ``_payload_key("followers")`` …); ``art_url`` mirrors the avatar
        # for the fast-query projection (``_image_url`` prefers it).
        payload: dict[str, Any] = artist.model_dump(mode="json") if artist is not None else {}
        payload["name"] = name
        return await self._snapshots.upsert(
            provider=resolved.provider,
            provider_entity_id=resolved.provider_id,
            entity_type=EntityType.ARTIST,
            raw_payload=payload,
            name=name,
            art_url=artist.image_url if artist is not None else None,
        )

    async def _persist_playlist_snapshot(self, resolved: ResolvedEntity) -> ProviderSnapshot:
        payload: dict[str, Any] = {"name": resolved.name, "description": None, "owner": None}
        return await self._snapshots.upsert(
            provider=resolved.provider,
            provider_entity_id=resolved.provider_id,
            entity_type=EntityType.PLAYLIST,
            raw_payload=payload,
            name=resolved.name,
        )

    # ------------------------------------------------------------- mapping
    def _core_track(self, track: TrackModel) -> Track | None:
        """Build a core :class:`Track` from a canonical row for matching.

        Returns ``None`` for an artist-less stub (a track needs ≥1 artist).
        """
        artists = tuple(a.name for a in track.artists)
        if not artists:
            return None
        album = track.album
        return Track(
            name=track.name,
            artists=artists,
            duration_ms=track.duration_ms,
            isrc=track.isrc,
            explicit=track.explicit,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=track.year,
            genres=tuple(track.genres),
            popularity=track.popularity,
            album=(
                AlbumRef(
                    name=album.name,
                    album_artist=album.album_artist,
                    year=album.year,
                    track_count=album.track_count,
                    cover_url=album.cover_url,
                )
                if album is not None
                else None
            ),
        )

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _with_degraded(result: ResolveResult, degraded: set[ProviderId]) -> ResolveResult:
        sources = tuple(sorted(pid.value for pid in degraded))
        for provider in sources:
            record_provider_degraded(provider)
        return ResolveResult(
            entity_type=result.entity_type,
            track=result.track,
            album=result.album,
            artist=result.artist,
            playlist=result.playlist,
            degraded_sources=sources,
        )
