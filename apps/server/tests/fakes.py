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
    Lyrics,
    LyricsKind,
    ProviderId,
    Track,
)
from spotdl_core.providers import (
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
)
from spotdl_core.providers.urls import PlatformRef

# Every capability Protocol a fake might satisfy, checked in build order.
_ALL_CAPABILITIES: tuple[type, ...] = (
    Resolves,
    Searches,
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
