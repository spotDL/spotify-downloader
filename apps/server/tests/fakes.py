"""In-memory fake providers implementing the Plan 2 capability Protocols.

The whole Plan 5 service/API suite is offline: every provider is faked at the
:class:`~spotdl_core.providers.ProviderRegistry` seam so no test touches the
network. Each fake implements exactly one capability Protocol (``id`` is a plain
instance attribute — ``runtime_checkable`` Protocols only check member presence,
and the registry orders by ``spec.id`` not the instance's ``id``).

:func:`build_fake_registry` wires fakes into a real ``ProviderRegistry`` via
``ProviderSpec``s whose factories return the given instances; ``failing=`` ids
get a factory that raises ``ProviderUnavailable`` so the registry records them in
:attr:`ProviderRegistry.unavailable` — the seam that drives ``degraded_sources``.
"""

from __future__ import annotations

from collections.abc import Iterable

from spotdl_core.model import (
    AudioCandidate,
    EntityType,
    Lyrics,
    LyricsKind,
    ProviderId,
    SearchHit,
    Track,
)
from spotdl_core.providers import (
    ALL_SEARCH_ENTITY_TYPES,
    Enriches,
    ProviderContext,
    ProviderRegistry,
    ProviderSpec,
    ProviderUnavailable,
    ProvidesAudio,
    ProvidesLyrics,
    ResolvedEntity,
    Resolves,
    Searches,
    SearchesEntities,
)
from spotdl_core.providers.urls import PlatformRef

# Every capability Protocol a fake might satisfy, checked in build order.
_ALL_CAPABILITIES: tuple[type, ...] = (
    Resolves,
    Searches,
    SearchesEntities,
    Enriches,
    ProvidesAudio,
    ProvidesLyrics,
)


class FakeResolver:
    """A ``Resolves`` provider returning a canned track for any ref.

    The returned :class:`ResolvedEntity` echoes the ref's ``entity_id`` as its
    ``provider_id`` so the persisted snapshot's key matches the ref (cache-first
    lookups hit on re-resolve). ``error`` makes ``resolve`` raise instead, to
    exercise the resolve-time degraded path. ``calls`` records every ref seen so
    a test can assert the network was (not) touched.
    """

    def __init__(
        self,
        *,
        id: ProviderId,
        track: Track | None = None,
        entity: ResolvedEntity | None = None,
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.track = track
        self.entity = entity
        self.error = error
        self.calls: list[PlatformRef] = []

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        self.calls.append(ref)
        if self.error is not None:
            raise self.error
        if self.entity is not None:  # a fully-formed (e.g. container) entity
            return self.entity
        return ResolvedEntity(
            provider=self.id,
            provider_id=ref.entity_id,
            entity_type=ref.entity_type,
            track=self.track,
        )


class FakeSearcher:
    """A ``Searches`` provider returning a fixed track list (truncated to limit)."""

    def __init__(
        self,
        *,
        id: ProviderId,
        tracks: Iterable[Track] = (),
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.tracks = list(tracks)
        self.error = error
        self.calls: list[str] = []

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return self.tracks[:limit]


class FakeEntitySearcher:
    """A ``SearchesEntities`` provider returning fixed hits filtered by ``types``.

    Returns only the hits whose ``entity_type`` is in the requested ``types`` (each
    such section truncated to ``limit``), mirroring a real provider that maps only
    the requested sections. ``error`` makes ``search_entities`` raise instead.
    """

    def __init__(
        self,
        *,
        id: ProviderId,
        hits: Iterable[SearchHit] = (),
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.hits = list(hits)
        self.error = error
        self.calls: list[tuple[str, frozenset[EntityType]]] = []

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]:
        self.calls.append((query, types))
        if self.error is not None:
            raise self.error
        per_type: dict[EntityType, int] = {}
        selected: list[SearchHit] = []
        for hit in self.hits:
            if hit.entity_type not in types:
                continue
            seen = per_type.get(hit.entity_type, 0)
            if seen >= limit:
                continue
            per_type[hit.entity_type] = seen + 1
            selected.append(hit)
        return selected


class FakeMetadataProvider:
    """A combined ``Resolves`` + ``Searches`` + ``SearchesEntities`` metadata source.

    Drives cross-provider enrichment (Phase 3): ``search`` returns fixed track hits,
    ``search_entities`` returns fixed mixed hits filtered by ``types``, and
    ``resolve`` echoes the ref — returning the configured full entity for that
    ``entity_type`` (``resolved``) or a bare echo otherwise. ``search_calls`` /
    ``resolve_calls`` record activity so a test can assert a warm re-resolve does
    **not** re-fan-out. ``error`` makes every call raise, exercising the
    degraded-secondary path (non-fatal).
    """

    def __init__(
        self,
        *,
        id: ProviderId,
        tracks: Iterable[Track] = (),
        hits: Iterable[SearchHit] = (),
        resolved: dict[EntityType, ResolvedEntity] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.tracks = list(tracks)
        self.hits = list(hits)
        self.resolved = dict(resolved or {})
        self.error = error
        self.search_calls: list[str] = []
        self.resolve_calls: list[PlatformRef] = []

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        self.search_calls.append(query)
        if self.error is not None:
            raise self.error
        return self.tracks[:limit]

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]:
        self.search_calls.append(query)
        if self.error is not None:
            raise self.error
        return [hit for hit in self.hits if hit.entity_type in types][:limit]

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        self.resolve_calls.append(ref)
        if self.error is not None:
            raise self.error
        entity = self.resolved.get(ref.entity_type)
        if entity is not None:
            return entity
        return ResolvedEntity(
            provider=self.id, provider_id=ref.entity_id, entity_type=ref.entity_type
        )


class FakeAudioProvider:
    """A ``ProvidesAudio`` provider returning fixed candidates (truncated to limit)."""

    def __init__(
        self,
        *,
        id: ProviderId,
        candidates: Iterable[AudioCandidate] = (),
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.candidates = list(candidates)
        self.error = error
        self.calls: list[Track] = []

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        self.calls.append(track)
        if self.error is not None:
            raise self.error
        return self.candidates[:limit]


class FakeLyricsProvider:
    """A ``ProvidesLyrics`` provider returning fixed lyrics (or ``None``)."""

    def __init__(
        self,
        *,
        id: ProviderId,
        text: str | None = None,
        kind: LyricsKind = LyricsKind.PLAIN,
        error: Exception | None = None,
    ) -> None:
        self.id = id
        self.text = text
        self.kind = kind
        self.error = error
        self.calls: list[Track] = []

    async def lyrics(self, track: Track) -> Lyrics | None:
        self.calls.append(track)
        if self.error is not None:
            raise self.error
        if self.text is None:
            return None
        return Lyrics(kind=self.kind, text=self.text, source=self.id)


def _capabilities_of(provider: object) -> frozenset[type]:
    """The set of capability Protocols ``provider`` structurally satisfies."""
    return frozenset(cap for cap in _ALL_CAPABILITIES if isinstance(provider, cap))


def _const_factory(provider: object):  # type: ignore[no-untyped-def]
    def factory(_ctx: ProviderContext) -> object:
        return provider

    return factory


def _failing_factory(provider_id: ProviderId):  # type: ignore[no-untyped-def]
    def factory(_ctx: ProviderContext) -> object:
        raise ProviderUnavailable(f"{provider_id} unavailable", provider=provider_id)

    return factory


def build_fake_registry(
    *providers: object,
    failing: Iterable[ProviderId] = (),
) -> ProviderRegistry:
    """Register the fake ``providers`` (capabilities inferred) into a registry.

    Each id in ``failing`` gets a spec whose factory raises
    :class:`ProviderUnavailable`; declaring the broad capability set means a
    normal resolve/match touches (and thus records) the failure so it surfaces in
    ``degraded_sources``.
    """
    registry = ProviderRegistry(ProviderContext())
    for provider in providers:
        provider_id = provider.id  # type: ignore[attr-defined]
        registry.register(
            ProviderSpec(
                id=provider_id,
                capabilities=_capabilities_of(provider),
                factory=_const_factory(provider),
            )
        )
    for provider_id in failing:
        registry.register(
            ProviderSpec(
                id=provider_id,
                capabilities=frozenset(_ALL_CAPABILITIES),
                factory=_failing_factory(provider_id),
            )
        )
    return registry
