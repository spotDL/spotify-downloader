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

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from spotdl_core.matching import MATCHER_V5_DEFAULT, ScoringConfig, match
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    EntityType,
    Lyrics,
    ProviderId,
    SearchHit,
    Track,
)
from spotdl_core.providers import (
    PlatformRef,
    ProviderError,
    ProviderNotConfigured,
    ProviderRegistry,
    ProviderUnavailable,
    ProvidesAudio,
    ProvidesLyrics,
    ResolvedEntity,
    Resolves,
    Searches,
    SearchesEntities,
    UnsupportedURL,
    parse,
)
from spotdl_core.providers.metadata.lastfm import (
    LastfmArtistInfo,
    LastfmProvider,
    LastfmTrackInfo,
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
    normalize_artist_name,
)
from spotdl_server.repositories.links import EntityLinkRepository
from spotdl_server.repositories.lyrics import LyricsRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.repositories.merge import SOURCE_PRIORITY, CanonicalMerger
from spotdl_server.repositories.snapshots import (
    PARTIAL_MARKER,
    SnapshotRepository,
    is_partial,
)
from spotdl_server.repositories.stats import EntityStatRepository
from spotdl_server.services import views
from spotdl_server.services.dto import ResolveResult
from spotdl_server.services.provider_search import provider_search

#: The set of canonical metadata sources cross-provider enrichment fans out to —
#: exactly the providers the deterministic merge ranks (``SOURCE_PRIORITY``:
#: Spotify > Deezer > iTunes > MusicBrainz). Audio-only providers (YTMusic, …) are
#: deliberately excluded: enrichment gathers *metadata*, and the merge only reads
#: these four for display fields. Membership is checked, not iteration order — the
#: merge re-sorts by priority regardless of the order snapshots are gathered in.
_METADATA_SOURCES: frozenset[ProviderId] = frozenset(SOURCE_PRIORITY)

#: Per-provider wall-clock budget for one enrichment fan-out leg (search + resolve).
#: A secondary provider that exceeds it is dropped (recorded as a degraded source),
#: never blocking the primary result. Sized for the slowest legitimate leg:
#: MusicBrainz throttles to 1 req/s and an artist leg is 3 sequential requests
#: (search + artist + release-group browse) with MB's own multi-second latency —
#: 6s cut that leg off mid-flight. Legs run concurrently, so this only bounds a
#: COLD resolve's tail, never a warm one.
_ENRICH_TIMEOUT_S: float = 12.0

#: How many search hits a secondary provider is asked for per enrichment leg.
_ENRICH_SEARCH_LIMIT: int = 5

#: Artist top-track listing cap: the primary's top tracks (Spotify serves 10)
#: unioned with confirmed secondaries' (Deezer serves up to 100), deduped.
_ARTIST_TOP_TRACKS_CAP: int = 25

#: Provider-snapshot ``raw_payload`` key → ``entity_stat`` metric name. Engagement
#: metrics are lifted from the already-collected snapshots (no extra fetch):
#: Spotify ``followers``/``popularity``, Deezer ``followers`` (``nb_fan``, mapped by
#: the Deezer provider), Last.fm ``listeners``/``playcount``. One capture per
#: (entity, provider, metric) per resolve (spec §Phase 4).
_STAT_METRICS: tuple[tuple[str, str], ...] = (
    ("followers", "followers"),
    ("popularity", "popularity"),
    ("listeners", "listeners"),
    ("playcount", "playcount"),
)


def _same_artist(primary: ResolvedEntity, candidate: ResolvedEntity) -> bool:
    """Confirm a same-named secondary candidate is the SAME artist by content overlap.

    Name equality alone is unsafe — providers host many artists sharing a name.
    Any shared album title or top-track title (case-folded) confirms identity.
    When both sides expose a comparable catalogue (albums or top tracks) and
    NOTHING overlaps, the candidate is a stranger and is rejected. When neither
    side has comparable content, the normalized-name gate (already applied by the
    caller) is the best available signal, so the candidate is accepted.
    """
    primary_albums = {a.name.casefold() for a in primary.albums}
    candidate_albums = {a.name.casefold() for a in candidate.albums}
    if primary_albums & candidate_albums:
        return True
    primary_tracks = {t.name.casefold() for t in primary.tracks}
    candidate_tracks = {t.name.casefold() for t in candidate.tracks}
    if primary_tracks & candidate_tracks:
        return True
    albums_comparable = bool(primary_albums and candidate_albums)
    tracks_comparable = bool(primary_tracks and candidate_tracks)
    return not (albums_comparable or tracks_comparable)


def _same_artist_strict(primary: ResolvedEntity, candidate: ResolvedEntity) -> bool:
    """The overlap gate WITHOUT the lenient no-content fallback.

    Used for a candidate whose name did NOT match the query (a provider's
    canonical rename — MusicBrainz lists Kanye West as "Ye" — or a relevance-only
    hit): identity must be PROVEN by shared content, never assumed.
    """
    primary_albums = {a.name.casefold() for a in primary.albums}
    candidate_albums = {a.name.casefold() for a in candidate.albums}
    if primary_albums & candidate_albums:
        return True
    primary_tracks = {t.name.casefold() for t in primary.tracks}
    candidate_tracks = {t.name.casefold() for t in candidate.tracks}
    return bool(primary_tracks & candidate_tracks)


class ResolveService:
    """Cache-first resolve of a query to a canonical entity + kicked matches.

    On a cache **miss** the resolve additionally fans out to the other canonical
    metadata providers (:data:`_METADATA_SOURCES`), snapshots the same real-world
    entity from each, and links those snapshots so the deterministic merge folds
    every source into the canonical row (Spotify still wins display fields). The
    fan-out is bounded (per-provider timeout, concurrent) and best-effort (a miss
    or error degrades that source, never the result). A warm re-resolve inside the
    snapshot's freshness window skips the fan-out entirely — the durable snapshot
    layer is the cache, so the already-linked secondary snapshots re-merge for free.
    """

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
        self._stats = EntityStatRepository(session)
        self._merger = CanonicalMerger(session)

    async def resolve(self, query: str, *, force: bool = False) -> ResolveResult:
        """Resolve ``query`` to a canonical entity view + ``degraded_sources``.

        ``force=True`` bypasses the snapshot cache and refetches from the
        providers (re-merging into the SAME canonical entity via its links) —
        the "Refresh" affordance. Without it a permanent snapshot means an
        already-resolved entity would never pick up new provider data.
        """
        degraded: set[ProviderId] = set()
        ref = await self._parse_or_search(query, degraded)

        if ref.entity_type is EntityType.TRACK:
            result = await self._resolve_track(ref, degraded, force=force)
        else:
            result = await self._resolve_container(ref, degraded, force=force)

        degraded.update(
            pid
            for pid, error in self._registry.unavailable.items()
            # A never-configured optional provider (no API key) is a deliberate
            # absence, not an outage — surfacing it would pin a permanent
            # "sources unavailable" banner on every result.
            if not isinstance(error, ProviderNotConfigured)
        )
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
    async def _resolve_track(
        self, ref: PlatformRef, degraded: set[ProviderId], *, force: bool = False
    ) -> ResolveResult:
        now = datetime.now(UTC)
        primary = (
            None if force else await self._snapshots.get_fresh(ref.provider, ref.entity_id, now)
        )
        if primary is not None and is_partial(primary):
            # A marked-partial listing preview (no ISRC) is not a resolved track —
            # fall through to a full fetch, whose authoritative persist clears it.
            primary = None
        was_miss = primary is None
        enriched: list[ProviderSnapshot] = []
        if primary is None:  # cache miss → fetch + snapshot + fan-out enrichment
            record_cache_miss("snapshot")
            resolved = await self._fetch_primary(ref)
            assert resolved.track is not None  # _fetch_primary guarantees a track
            primary = await self._persist_track_snapshot(
                resolved.provider, resolved.provider_id, resolved.track
            )
            enriched = await self._enrich_track(resolved.provider, resolved.track, degraded)
        else:
            record_cache_hit("snapshot")

        merge_set = self._combine(await self._merge_set(primary), enriched)
        track = await self._merger.merge_track(merge_set)
        # Capture engagement stats only on a fresh fetch (a cold miss) — a warm
        # re-resolve re-merges cached snapshots and should not append a duplicate
        # capture for the same numbers.
        if was_miss:
            await self._record_stats(EntityType.TRACK, track.id, merge_set)
        await self._kick_matching(track, degraded)

        # Fetch lyrics on a COLD resolve or a forced refresh only. Gating on
        # "no rows yet" alone would re-run the fan-out on EVERY warm resolve of a
        # track that genuinely has no lyrics anywhere — paying the slowest lyrics
        # source's timeout (lrclib's search path can run tens of seconds) on each
        # page load. A miss retries on the next cold/forced resolve instead.
        lyrics_rows = await self._lyrics.list_for_track(track.id)
        if force or (was_miss and not lyrics_rows):
            core = self._core_track(track)
            if core is not None:  # a stub with no artists cannot be looked up
                await self._kick_lyrics(track, core, degraded)
                lyrics_rows = await self._lyrics.list_for_track(track.id)

        match_rows = await self._matches.list_for_track(track.id)
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

    async def _kick_lyrics(self, track: TrackModel, core: Track, degraded: set[ProviderId]) -> None:
        """Fetch lyrics for ``track`` from every lyrics provider and persist each hit.

        Fans out to :meth:`ProviderRegistry.capable` for ``ProvidesLyrics``
        concurrently, each leg bounded by :data:`_ENRICH_TIMEOUT_S`. A provider that
        raises or times out records itself in ``degraded`` (same semantics as
        :meth:`_kick_matching`) and is never fatal; a ``None`` result is a clean
        miss (that source simply has no lyrics for the track). Each hit is upserted
        by its ``(source, kind)`` so a re-fetch refreshes the text without resetting
        community votes.
        """
        providers: list[ProvidesLyrics] = self._registry.capable(ProvidesLyrics)  # type: ignore[type-abstract]
        if not providers:
            return

        async def _bounded(provider: ProvidesLyrics) -> Lyrics | None:
            return await asyncio.wait_for(provider.lyrics(core), timeout=_ENRICH_TIMEOUT_S)

        results = await asyncio.gather(
            *(_bounded(provider) for provider in providers), return_exceptions=True
        )
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, Lyrics):
                await self._lyrics.upsert(track.id, result.source, result.kind, result.text)
            elif isinstance(result, BaseException):
                degraded.add(provider.id)
                record_provider_error(provider.id.value)

    # --------------------------------------------------- cross-provider enrich
    def _enrichment_providers(self, primary: ProviderId, capability: type) -> list[Any]:
        """The other canonical metadata sources with ``capability``, primary excluded.

        Restricted to :data:`_METADATA_SOURCES` (the merge-ranked providers) so
        enrichment only gathers display metadata. ``capable`` constructs each lazily
        and skips (records in ``registry.unavailable``) any whose factory fails, so a
        broken optional provider degrades exactly one source.
        """
        providers: list[Any] = self._registry.capable(capability)
        return [
            provider
            for provider in providers
            if provider.id in _METADATA_SOURCES and provider.id != primary
        ]

    async def _gather_enrich(
        self, providers: list[Any], leg: Any, degraded: set[ProviderId]
    ) -> list[ProviderSnapshot]:
        """Run one enrichment ``leg`` per provider, concurrently + time-bounded.

        Each leg returns a linked-in snapshot or ``None`` (a clean miss — the source
        had no confident match). A leg that raises or exceeds
        :data:`_ENRICH_TIMEOUT_S` degrades that source (never fatal). Never blocks
        the primary result on a slow secondary — the timeout caps every leg.
        """
        if not providers:
            return []

        async def _bounded(provider: Any) -> ProviderSnapshot | None:
            return await asyncio.wait_for(leg(provider), timeout=_ENRICH_TIMEOUT_S)

        results = await asyncio.gather(
            *(_bounded(provider) for provider in providers), return_exceptions=True
        )
        snapshots: list[ProviderSnapshot] = []
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, ProviderSnapshot):
                snapshots.append(result)
            elif isinstance(result, BaseException):
                degraded.add(provider.id)
                record_provider_error(provider.id.value)
        return snapshots

    async def _enrich_track(
        self, primary: ProviderId, track: Track, degraded: set[ProviderId]
    ) -> list[ProviderSnapshot]:
        """Fan out to the other metadata sources for the same recording.

        Match strategy: search each source by ISRC (falling back to
        ``name + main artist`` when the ISRC query finds nothing, or when the track
        has no ISRC), confirm the best hit is really the same recording with the
        shared matcher (``match`` — reusing its ISRC/title/artist gate, no new rule),
        resolve it to a full entity, and snapshot + link it so the merge folds it in.
        """
        providers = self._enrichment_providers(primary, Searches)

        async def leg(provider: Any) -> ProviderSnapshot | None:
            return await self._enrich_track_from(provider, track)

        snapshots = await self._gather_enrich(providers, leg, degraded)
        lastfm = await self._enrich_lastfm_track(track, degraded)
        if lastfm is not None:
            snapshots.append(lastfm)
        return snapshots

    async def _enrich_track_from(self, provider: Any, track: Track) -> ProviderSnapshot | None:
        queries: list[str] = []
        if track.isrc:
            queries.append(track.isrc)
        queries.append(f"{track.name} {track.main_artist}".strip())
        for query in queries:
            hits = await provider.search(query, limit=_ENRICH_SEARCH_LIMIT)
            best = self._best_track_match(track, hits)
            if best is None:
                continue
            full = await self._resolve_secondary_track(provider, best)
            confirmed = full or best
            if confirmed.provider_id is None:
                return None  # cannot key/cache a ref-less hit
            return await self._persist_track_snapshot(provider.id, confirmed.provider_id, confirmed)
        return None

    def _best_track_match(self, track: Track, hits: list[Track]) -> Track | None:
        """The highest-confidence hit confirmed to be the same recording, or ``None``.

        Reuses the shared matcher: each hit is scored as an audio candidate against
        ``track`` and accepted only above the matcher's own ISRC short-circuit
        threshold (a calibrated number, not an invented one).
        """
        threshold = self._matcher_config.selection.isrc_short_circuit_min_score
        best: Track | None = None
        best_score = threshold
        for hit in hits:
            ranked = match(track, [self._as_candidate(hit)], self._matcher_config)
            if ranked and ranked[0].score >= best_score:
                best_score = ranked[0].score
                best = hit
        return best

    @staticmethod
    def _as_candidate(track: Track) -> AudioCandidate:
        """Adapt a metadata hit to an ``AudioCandidate`` for a match-confidence check."""
        return AudioCandidate(
            provider=track.provider or ProviderId.SPOTIFY,
            provider_id=track.provider_id or "",
            url="",
            name=track.name,
            artists=track.artists,
            duration_ms=track.duration_ms,
            album=track.album.name if track.album is not None else None,
            isrc=track.isrc,
        )

    @staticmethod
    async def _resolve_secondary_track(provider: Any, hit: Track) -> Track | None:
        """Resolve a confirmed hit's ref to a full track (for its richer metadata)."""
        if hit.provider_id is None or not isinstance(provider, Resolves):
            return None
        resolved = await provider.resolve(
            PlatformRef(
                provider=provider.id, entity_type=EntityType.TRACK, entity_id=hit.provider_id
            )
        )
        return resolved.track

    async def _enrich_album(
        self, resolved: ResolvedEntity, degraded: set[ProviderId]
    ) -> list[ProviderSnapshot]:
        """Fan out to the other metadata sources for the same album (name + year gate).

        Matched by normalized name, additionally gated on release year and album
        artist when the primary carries them (conservative — a miss is non-fatal).
        Only ``SearchesEntities`` providers can search albums, so this naturally
        narrows to Spotify/Deezer.
        """
        album = resolved.album
        name = album.name if album is not None else resolved.name
        if not name:
            return []
        year = album.year if album is not None else None
        album_artist = album.album_artist if album is not None else None
        providers = self._enrichment_providers(resolved.provider, SearchesEntities)

        async def leg(provider: Any) -> ProviderSnapshot | None:
            return await self._enrich_album_from(provider, name, year, album_artist)

        return await self._gather_enrich(providers, leg, degraded)

    async def _enrich_album_from(
        self, provider: Any, name: str, year: int | None, album_artist: str | None
    ) -> ProviderSnapshot | None:
        hits = await provider.search_entities(
            name, types=frozenset({EntityType.ALBUM}), limit=_ENRICH_SEARCH_LIMIT
        )
        best = self._best_album_match(name, year, album_artist, hits)
        if best is None or not isinstance(provider, Resolves):
            return None
        resolved = await provider.resolve(
            PlatformRef(
                provider=provider.id, entity_type=EntityType.ALBUM, entity_id=best.provider_id
            )
        )
        return await self._persist_album_snapshot(resolved)

    @staticmethod
    def _best_album_match(
        name: str, year: int | None, album_artist: str | None, hits: list[SearchHit]
    ) -> SearchHit | None:
        target = normalize_artist_name(name)
        target_artist = normalize_artist_name(album_artist) if album_artist else None
        for hit in hits:
            if normalize_artist_name(hit.name) != target:
                continue
            if year is not None and hit.year is not None and hit.year != year:
                continue
            if (
                target_artist is not None
                and hit.subtitle
                and normalize_artist_name(hit.subtitle) != target_artist
            ):
                continue
            return hit
        return None

    async def _enrich_artist(
        self, resolved: ResolvedEntity, degraded: set[ProviderId]
    ) -> tuple[
        list[ProviderSnapshot], tuple[AlbumRef, ...], tuple[tuple[ResolvedEntity, Track], ...]
    ]:
        """Fan out to the other metadata sources for the same artist.

        Candidates are found by :func:`normalize_artist_name` equality, then
        confirmed by CONTENT OVERLAP against the primary (a shared album or
        top-track name): same-named artists are common (four "Mata"s on Deezer),
        and a name-only gate trusted whichever hit came first — polluting
        followers, genres, and the discography with a stranger's data. Only
        ``SearchesEntities`` providers can search artists (Spotify/Deezer).

        Returns the confirmed snapshots plus the confirmed candidates' discography
        refs AND top tracks (each paired with its source entity for snapshot
        keying), so both the discography and the top-track listing are the UNION
        across all sources — a provider-exclusive release or track still appears.
        """
        artist = resolved.artist
        name = artist.name if artist is not None else resolved.name
        if not name:
            return [], (), ()
        providers = self._enrichment_providers(resolved.provider, SearchesEntities)

        async def leg(provider: Any) -> tuple[ResolvedEntity, bool] | None:
            return await self._artist_candidate_from(provider, name)

        candidates = await self._gather_artist_candidates(providers, leg, degraded)
        snapshots: list[ProviderSnapshot] = []
        extra_albums: list[AlbumRef] = []
        extra_tracks: list[tuple[ResolvedEntity, Track]] = []
        for candidate, name_matched in candidates:
            confirmed = (
                _same_artist(resolved, candidate)
                if name_matched
                else _same_artist_strict(resolved, candidate)
            )
            if not confirmed:
                continue  # a same-named stranger / unproven rename — never trust it
            snapshots.append(await self._persist_artist_snapshot(candidate))
            extra_albums.extend(candidate.albums)
            extra_tracks.extend((candidate, track) for track in candidate.tracks)
        lastfm = await self._enrich_lastfm_artist(name, degraded)
        if lastfm is not None:
            snapshots.append(lastfm)
        return snapshots, tuple(extra_albums), tuple(extra_tracks)

    async def _artist_candidate_from(
        self, provider: Any, name: str
    ) -> tuple[ResolvedEntity, bool] | None:
        """Search+resolve one secondary provider's candidate for ``name`` (no persist).

        The first normalized-name-equal hit is preferred — the provider's own
        relevance ranking beats raw popularity (Deezer ranks the intended "Mata"
        first even though a same-named stranger has more fans). When NO hit
        matches the name, the top relevance hit is still resolved but flagged
        ``name_matched=False``: providers canonically rename artists (MusicBrainz
        lists Kanye West as "Ye"), so the caller demands STRICT content overlap
        before trusting it. Nothing is persisted here.
        """
        hits = await provider.search_entities(
            name, types=frozenset({EntityType.ARTIST}), limit=_ENRICH_SEARCH_LIMIT
        )
        target = normalize_artist_name(name)
        exact = next(
            (hit for hit in hits if normalize_artist_name(hit.name) == target),
            None,
        )
        best = exact or (hits[0] if hits else None)
        if best is None or not isinstance(provider, Resolves):
            return None
        resolved = await provider.resolve(
            PlatformRef(
                provider=provider.id, entity_type=EntityType.ARTIST, entity_id=best.provider_id
            )
        )
        return resolved, exact is not None

    async def _gather_artist_candidates(
        self, providers: list[Any], leg: Any, degraded: set[ProviderId]
    ) -> list[tuple[ResolvedEntity, bool]]:
        """The ``_gather_enrich`` semantics (concurrent, time-bounded, a failing leg
        degrades its source) for legs yielding an unpersisted
        ``(ResolvedEntity, name_matched)`` candidate pair."""
        if not providers:
            return []

        async def _bounded(provider: Any) -> tuple[ResolvedEntity, bool] | None:
            return await asyncio.wait_for(leg(provider), timeout=_ENRICH_TIMEOUT_S)

        results = await asyncio.gather(
            *(_bounded(provider) for provider in providers), return_exceptions=True
        )
        candidates: list[tuple[ResolvedEntity, bool]] = []
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, tuple):
                candidates.append(result)
            elif isinstance(result, BaseException):
                degraded.add(provider.id)
                record_provider_error(provider.id.value)
        return candidates

    # --------------------------------------------------- last.fm enrichment
    def _lastfm(self) -> LastfmProvider | None:
        """The Last.fm provider, or ``None`` when unavailable (no API key set).

        Constructed lazily by the registry; a missing key makes the factory raise
        :class:`ProviderUnavailable`, which the registry caches — so this simply
        yields ``None`` and every Last.fm leg becomes a clean no-op (never an error).
        """
        try:
            provider = self._registry.get(ProviderId.LASTFM)
        except (KeyError, ProviderError):
            return None
        return provider if isinstance(provider, LastfmProvider) else None

    async def _enrich_lastfm_artist(
        self, name: str, degraded: set[ProviderId]
    ) -> ProviderSnapshot | None:
        """Query Last.fm by artist name; snapshot bio/genres + engagement stats.

        Confirmed by :func:`normalize_artist_name` equality against the returned
        name (Last.fm may autocorrect) so a wrong-artist bio is never trusted. The
        lookup is time-bounded and non-fatal — a failure degrades Last.fm only.
        """
        provider = self._lastfm()
        if provider is None or not name:
            return None
        info = await self._bounded_lastfm(provider.artist_info(name), degraded)
        if info is None or not self._names_match(name, info.name):
            return None
        return await self._persist_lastfm_artist_snapshot(name, info)

    async def _enrich_lastfm_track(
        self, track: Track, degraded: set[ProviderId]
    ) -> ProviderSnapshot | None:
        """Query Last.fm by artist+track name; snapshot genres + engagement stats.

        Confirmed by normalized-name equality on BOTH the track title and the main
        artist so an unrelated same-titled recording is not trusted. Time-bounded
        and non-fatal (a failure degrades Last.fm only).
        """
        provider = self._lastfm()
        if provider is None or not track.name or not track.artists:
            return None
        info = await self._bounded_lastfm(
            provider.track_info(track.main_artist, track.name), degraded
        )
        if info is None or not self._names_match(track.name, info.name):
            return None
        if info.artist is not None and not self._names_match(track.main_artist, info.artist):
            return None
        return await self._persist_lastfm_track_snapshot(track, info)

    @staticmethod
    async def _bounded_lastfm(coro: Any, degraded: set[ProviderId]) -> Any:
        """Await a Last.fm coroutine under the enrichment timeout; ``None`` on failure.

        Any error or timeout degrades Last.fm (records it) and yields ``None`` so
        the resolve continues — Last.fm is strictly best-effort (spec §Phase 4).
        """
        try:
            return await asyncio.wait_for(coro, timeout=_ENRICH_TIMEOUT_S)
        except Exception:  # noqa: BLE001 — best-effort: any failure degrades, never fatal
            degraded.add(ProviderId.LASTFM)
            record_provider_error(ProviderId.LASTFM.value)
            return None

    @staticmethod
    def _names_match(expected: str, actual: str | None) -> bool:
        """Whether two names share the normalized artist-identity key."""
        return actual is not None and normalize_artist_name(expected) == normalize_artist_name(
            actual
        )

    async def _persist_lastfm_artist_snapshot(
        self, name: str, info: LastfmArtistInfo
    ) -> ProviderSnapshot:
        """Snapshot a Last.fm artist result under a stable normalized-name key.

        The payload carries the merge-read keys (``bio``/``genres`` fold into the
        canonical artist — Spotify-first still wins, so Last.fm fills the bio when
        Spotify has none) plus ``listeners``/``playcount`` for :meth:`_record_stats`.
        """
        payload: dict[str, Any] = {
            "name": info.name,
            "bio": info.bio,
            "genres": list(info.genres),
            "listeners": info.listeners,
            "playcount": info.playcount,
        }
        return await self._snapshots.upsert(
            provider=ProviderId.LASTFM,
            provider_entity_id=f"artist:{normalize_artist_name(name)}",
            entity_type=EntityType.ARTIST,
            raw_payload=payload,
            name=info.name,
        )

    async def _persist_lastfm_track_snapshot(
        self, track: Track, info: LastfmTrackInfo
    ) -> ProviderSnapshot:
        """Snapshot a Last.fm track result keyed by normalized artist + title.

        Contributes ``genres`` to the merge (gap-fill only, Last.fm ranks last) and
        carries ``listeners``/``playcount`` for :meth:`_record_stats`.
        """
        artist_key = normalize_artist_name(track.main_artist)
        key = f"track:{artist_key}:{normalize_artist_name(track.name)}"
        payload: dict[str, Any] = {
            "name": info.name,
            "artists": [info.artist or track.main_artist],
            "genres": list(info.genres),
            "listeners": info.listeners,
            "playcount": info.playcount,
        }
        return await self._snapshots.upsert(
            provider=ProviderId.LASTFM,
            provider_entity_id=key,
            entity_type=EntityType.TRACK,
            raw_payload=payload,
            name=info.name,
            artist_names=[info.artist or track.main_artist],
        )

    # ------------------------------------------------------ stats recording
    async def _record_stats(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        snapshots: list[ProviderSnapshot],
    ) -> None:
        """Append one engagement capture per (provider, metric) into ``entity_stat``.

        Lifts the metrics in :data:`_STAT_METRICS` from each contributing snapshot's
        ``raw_payload`` (already fetched — no extra network call): Spotify
        ``followers``/``popularity``, Deezer ``followers``, Last.fm
        ``listeners``/``playcount``. Deduplicated by (provider, metric) so a single
        resolve writes at most one row per pair; across resolves the series grows.
        """
        seen: set[tuple[ProviderId, str]] = set()
        for snapshot in snapshots:
            payload = snapshot.raw_payload if isinstance(snapshot.raw_payload, dict) else {}
            for key, metric in _STAT_METRICS:
                value = payload.get(key)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    continue
                marker = (snapshot.provider, metric)
                if marker in seen:
                    continue
                seen.add(marker)
                await self._stats.record(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    provider=snapshot.provider,
                    metric=metric,
                    value=value,
                )

    @staticmethod
    def _combine(
        base: list[ProviderSnapshot], extra: list[ProviderSnapshot]
    ) -> list[ProviderSnapshot]:
        """Union two snapshot lists, de-duplicated by id (order-independent merge)."""
        seen = {snapshot.id for snapshot in base}
        combined = list(base)
        for snapshot in extra:
            if snapshot.id not in seen:
                seen.add(snapshot.id)
                combined.append(snapshot)
        return combined

    # ------------------------------------------------------------- container
    async def _resolve_container(
        self, ref: PlatformRef, degraded: set[ProviderId], *, force: bool = False
    ) -> ResolveResult:
        """Resolve an album/artist/playlist ref (no per-track match kick).

        Cache-first: a fresh snapshot already merged into a canonical entity is
        reloaded without any network call. Otherwise (or on ``force``) the entity
        and its track listing are fetched, snapshotted, and merged.
        """
        now = datetime.now(UTC)
        fresh = None if force else await self._snapshots.get_fresh(ref.provider, ref.entity_id, now)
        if fresh is not None:
            existing = await self._existing_container(fresh)
            if existing is not None:
                record_cache_hit("snapshot")
                return existing

        record_cache_miss("snapshot")
        resolved = await self._fetch_container(ref)
        return await self._merge_container(resolved, degraded)

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

    async def _merge_container(
        self, resolved: ResolvedEntity, degraded: set[ProviderId]
    ) -> ResolveResult:
        if resolved.entity_type is EntityType.ALBUM:
            album_snap = await self._persist_album_snapshot(resolved)
            enriched = await self._enrich_album(resolved, degraded)
            by_pos = {
                index: [await self._persist_track_snapshot_from(resolved, index, track)]
                for index, track in enumerate(resolved.tracks)
            }
            album = await self._merger.merge_album([album_snap, *enriched], by_pos)
            await self._record_stats(EntityType.ALBUM, album.id, [album_snap, *enriched])
            return ResolveResult(entity_type=EntityType.ALBUM.value, album=views.album_view(album))
        if resolved.entity_type is EntityType.ARTIST:
            artist_snap = await self._persist_artist_snapshot(resolved)
            enriched, extra_albums, extra_tracks = await self._enrich_artist(resolved, degraded)
            # The top-track listing is the UNION across sources: the primary's
            # (Spotify serves 10) first, then confirmed secondaries' tracks the
            # primary doesn't carry (ISRC-first dedupe, then case-folded name),
            # capped so the page stays a "top tracks" list, not a full dump.
            listing: list[tuple[ResolvedEntity, Track]] = [(resolved, t) for t in resolved.tracks]
            # Seed BOTH keys for every primary track — an ISRC-only seed let a
            # secondary's copy of the same recording through whenever its ISRC
            # differed (a distinct pressing/remaster) or was absent, since the
            # name fallback never saw the primary's title (the "ECHO twice" bug).
            seen_tracks: set[str] = set()
            for t in resolved.tracks:
                seen_tracks.add(t.name.casefold())
                if t.isrc:
                    seen_tracks.add(t.isrc)
            for source_entity, track in extra_tracks:
                name_key = track.name.casefold()
                if name_key in seen_tracks or (track.isrc and track.isrc in seen_tracks):
                    continue  # same title, or same ISRC — the primary's copy already wins
                seen_tracks.add(name_key)
                if track.isrc:
                    seen_tracks.add(track.isrc)
                listing.append((source_entity, track))
            listing = listing[:_ARTIST_TOP_TRACKS_CAP]
            by_pos = {
                index: [await self._persist_track_snapshot_from(container, index, track)]
                for index, (container, track) in enumerate(listing)
            }
            # Snapshot each discography album (metadata-only, one source snapshot
            # each — no per-album enrichment fan-out) so the merge persists + links
            # them; refs without a resolvable provider id are skipped. The listing
            # is the UNION across sources: the primary's discography first, then any
            # overlap-confirmed secondary's releases the primary doesn't carry
            # (case-folded name dedupe, matching the providers' own dedupe rule).
            disc_refs = list(resolved.albums)
            seen_names = {ref.name.casefold() for ref in disc_refs}
            for ref in extra_albums:
                key = ref.name.casefold()
                if key not in seen_names:
                    seen_names.add(key)
                    disc_refs.append(ref)
            album_by_pos: dict[int, list[ProviderSnapshot]] = {}
            for index, album_ref in enumerate(disc_refs):
                disc_snap = await self._persist_discography_album_snapshot(album_ref)
                if disc_snap is not None:
                    album_by_pos[index] = [disc_snap]
            artist = await self._merger.merge_artist([artist_snap, *enriched], by_pos, album_by_pos)
            await self._record_stats(EntityType.ARTIST, artist.id, [artist_snap, *enriched])
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
            # A trackless album is a discography stub (persisted metadata-only from
            # an artist's ``/albums`` listing), NOT a fully-resolved album — fall
            # through to a real fetch so the direct resolve returns its track list.
            if album is not None and album.tracks:
                return ResolveResult(entity_type=entity_type.value, album=views.album_view(album))
            if album is not None:
                return None
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
        self,
        provider: ProviderId,
        provider_entity_id: str,
        track: Track,
        *,
        preview: bool = False,
    ) -> ProviderSnapshot:
        """Persist one track snapshot.

        ``preview=True`` is the container-listing mode (album/playlist/top-tracks
        rows): it fills gaps without clobbering a richer existing snapshot, and the
        row is marked :data:`PARTIAL_MARKER` — a preview must never satisfy a
        direct resolve, or the track's first open would skip the authoritative
        fetch AND the cross-provider enrichment fan-out (a track first seen via an
        artist/album listing stayed single-source forever).
        """
        payload = track.model_dump(mode="json")
        if preview:
            payload[PARTIAL_MARKER] = True
        return await self._snapshots.upsert(
            provider=provider,
            provider_entity_id=provider_entity_id,
            entity_type=EntityType.TRACK,
            raw_payload=payload,
            fill_only=preview,
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
        return await self._persist_track_snapshot(provider, provider_id, track, preview=True)

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

    async def _persist_discography_album_snapshot(self, album: AlbumRef) -> ProviderSnapshot | None:
        """Snapshot one discography album ref (metadata only), keyed by its source ref.

        Returns ``None`` for a ref lacking a resolvable ``provider``/``provider_id``
        (it cannot be cached or later resolve-refreshed). The serialized ``AlbumRef``
        carries the merge-read keys (``album_type``/``year``/``cover_url`` …).
        """
        if album.provider is None or album.provider_id is None:
            return None
        # ``fill_only``: an existing snapshot may be richer (a full album resolve:
        # label/copyright) OR sparser (a search hit with no ``album_type``) — fill
        # the gaps this ref knows (album_type/track_count) and never downgrade.
        return await self._snapshots.upsert(
            provider=album.provider,
            provider_entity_id=album.provider_id,
            entity_type=EntityType.ALBUM,
            raw_payload=album.model_dump(mode="json"),
            fill_only=True,
            name=album.name,
            album_name=album.name,
            art_url=album.cover_url,
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
        # Serialize the provider's ``PlaylistRef`` (description/owner/cover) under
        # the keys ``merge_playlist`` reads; older providers without one still
        # persist the name-only shape.
        playlist = resolved.playlist
        payload: dict[str, Any] = (
            playlist.model_dump(mode="json")
            if playlist is not None
            else {"name": resolved.name, "description": None, "owner": None}
        )
        payload.setdefault("name", resolved.name)
        return await self._snapshots.upsert(
            provider=resolved.provider,
            provider_entity_id=resolved.provider_id,
            entity_type=EntityType.PLAYLIST,
            raw_payload=payload,
            name=resolved.name,
            art_url=playlist.cover_url if playlist is not None else None,
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
