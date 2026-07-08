"""Capability-based provider registry with deterministic ordering.

The registry is the single entry point through which the server (Plan 5)
obtains providers by *capability* rather than by name. It solves three
problems at once:

* **Deterministic ordering** -- capability queries return providers in a fixed,
  auditable precedence (:data:`PROVIDER_ORDER`), never in registration order or
  dict-iteration order.
* **Lazy, isolated construction** -- a spec declares which capability Protocols
  its provider satisfies, so :meth:`ProviderRegistry.capable` can *filter*
  without importing the provider's (possibly fragile) module. Only matching
  specs are constructed, lazily, on first use, and cached thereafter.
* **No silent fallbacks** -- when a factory fails (e.g. a lazy ``import
  ytmusicapi`` blows up), the failure is wrapped in
  :class:`~spotdl_core.providers.errors.ProviderUnavailable`, cached for the
  registry's lifetime, and surfaced via :attr:`ProviderRegistry.unavailable`.
  :meth:`get` re-raises it; :meth:`capable` skips that provider but the failure
  remains observable. One broken dependency degrades exactly one provider.

This module must import with **zero provider third-party dependencies** present
(the isolation constraint): it imports only the standard library, the core
model, and the sibling provider-layer modules. Heavy deps (``ytmusicapi``,
``yt-dlp``, scrapers) are imported *inside* the factories that Tasks 6-12
register, never at this module's top level.

The public API and :data:`PROVIDER_ORDER` are a **CONTRACT**. The
:func:`build_default_registry` wiring lands incrementally: it is a documented
stub here and Tasks 6-12 append their ``reg.register(...)`` calls.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar, cast

from spotdl_core.model import ProviderId
from spotdl_core.providers.base import Provider
from spotdl_core.providers.errors import ProviderError, ProviderUnavailable
from spotdl_core.providers.http import DEFAULT_USER_AGENT

__all__ = [
    "DEFAULT_PIPED_INSTANCES",
    "PROVIDER_ORDER",
    "ProviderContext",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderSpec",
    "SpotifyConfig",
    "build_default_registry",
]

#: Fixed precedence used by every capability query. Providers earlier in this
#: tuple are preferred. This is a CONTRACT relied on by Plans 3-7 and by
#: Task 12's full-registry assertion; it lists every :class:`ProviderId`.
PROVIDER_ORDER: tuple[ProviderId, ...] = (
    ProviderId.SPOTIFY,
    ProviderId.DEEZER,
    ProviderId.ITUNES,
    ProviderId.MUSICBRAINZ,
    ProviderId.YTMUSIC,
    ProviderId.YOUTUBE,
    ProviderId.SOUNDCLOUD,
    ProviderId.BANDCAMP,
    ProviderId.PIPED,
    ProviderId.LRCLIB,
    ProviderId.GENIUS,
    ProviderId.MUSIXMATCH,
    ProviderId.AZLYRICS,
)

#: Rank lookup for ordering matched specs; O(1) per provider.
_ORDER_INDEX: dict[ProviderId, int] = {pid: i for i, pid in enumerate(PROVIDER_ORDER)}

#: Default public Piped API instances used when no override is supplied
#: (consumed by the Piped audio provider in Task 10). Operators may override
#: via :attr:`ProviderContext.piped_instances`.
DEFAULT_PIPED_INSTANCES: tuple[str, ...] = (
    "https://pipedapi.kavin.rocks",
    "https://api.piped.yt",
    "https://pipedapi.adminforge.de",
)


def _env_flag(raw: str) -> bool:
    """Interpret an environment-variable string as a boolean.

    ``"0"`` and ``"false"`` (any case, surrounding whitespace ignored) mean
    ``False``; everything else means ``True``.
    """
    return raw.strip().lower() not in ("0", "false")


@dataclass(frozen=True)
class SpotifyConfig:
    """Spotify credential/behaviour configuration.

    ``prefer_anonymous`` selects the token strategy (Task 6): ``True`` tries the
    anonymous TOTP token first and falls back to client-credentials; ``False``
    reverses that. ``totp_secret_override`` lets operators rotate the pinned
    anonymous-token TOTP secret via configuration without a code release
    (spec §1: no hardcoded-shared-secret failure mode).
    """

    client_id: str | None = None
    client_secret: str | None = None
    prefer_anonymous: bool = True
    totp_secret_override: str | None = None

    @classmethod
    def from_env(cls) -> SpotifyConfig:
        """Build a config from ``SPOTDL_SPOTIFY_*`` environment variables.

        Reads ``SPOTDL_SPOTIFY_CLIENT_ID``, ``SPOTDL_SPOTIFY_CLIENT_SECRET``,
        ``SPOTDL_SPOTIFY_TOTP_SECRET`` (-> ``totp_secret_override``) and
        ``SPOTDL_SPOTIFY_PREFER_ANONYMOUS`` (``"0"``/``"false"`` -> ``False``).
        Unset variables keep the dataclass defaults.
        """
        prefer_raw = os.environ.get("SPOTDL_SPOTIFY_PREFER_ANONYMOUS")
        return cls(
            client_id=os.environ.get("SPOTDL_SPOTIFY_CLIENT_ID"),
            client_secret=os.environ.get("SPOTDL_SPOTIFY_CLIENT_SECRET"),
            totp_secret_override=os.environ.get("SPOTDL_SPOTIFY_TOTP_SECRET"),
            prefer_anonymous=_env_flag(prefer_raw) if prefer_raw is not None else True,
        )


@dataclass(frozen=True)
class ProviderContext:
    """Immutable configuration handed to every provider factory.

    A single context is built at startup and shared across all providers; it
    carries only configuration (credentials, language, endpoints), never live
    clients -- each factory creates and owns its own client.
    """

    user_agent: str = DEFAULT_USER_AGENT
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)
    soundcloud_client_id: str | None = None
    genius_token: str | None = None
    piped_instances: tuple[str, ...] = DEFAULT_PIPED_INSTANCES
    ytmusic_language: str = "en"


#: A factory receives the shared context and returns a constructed provider.
ProviderFactory = Callable[[ProviderContext], Provider]


@dataclass(frozen=True)
class ProviderSpec:
    """Declarative registration record for one provider.

    ``capabilities`` lists the capability Protocol *types* the provider
    satisfies (e.g. ``frozenset({Resolves, Searches})``). It is declared here so
    :meth:`ProviderRegistry.capable` can filter by capability without importing
    or constructing the provider module first.
    """

    id: ProviderId
    capabilities: frozenset[type]
    factory: ProviderFactory


C = TypeVar("C")


class ProviderRegistry:
    """Owns provider specs, lazily constructs providers, and closes them.

    Construction is deferred until the first :meth:`get`/:meth:`capable` that
    needs the provider; successes and failures are both cached for the
    registry's lifetime. Recovery from a cached failure requires building a new
    registry -- the server constructs one per process/startup, so a restart or
    config reload retries.
    """

    def __init__(self, context: ProviderContext) -> None:
        self._context = context
        self._specs: dict[ProviderId, ProviderSpec] = {}
        self._instances: dict[ProviderId, Provider] = {}
        self._failures: dict[ProviderId, ProviderError] = {}

    def register(self, spec: ProviderSpec) -> None:
        """Register (or replace) a provider spec, keyed by id.

        Idempotent by id: a later registration for the same id wins. Raises
        :class:`ValueError` if the id has no place in :data:`PROVIDER_ORDER`.
        """
        if spec.id not in _ORDER_INDEX:
            raise ValueError(f"provider id {spec.id!r} is not part of PROVIDER_ORDER")
        self._specs[spec.id] = spec

    def get(self, provider_id: ProviderId) -> Provider:
        """Return the provider for ``provider_id``, constructing it on demand.

        Raises :class:`KeyError` if the id was never registered (distinct from
        "registered but unavailable"). If construction previously failed, the
        cached :class:`ProviderUnavailable` is re-raised without re-running the
        factory. A fresh factory failure is wrapped in
        :class:`ProviderUnavailable`, cached, and re-raised.
        """
        if provider_id not in self._specs:
            raise KeyError(provider_id)
        cached = self._instances.get(provider_id)
        if cached is not None:
            return cached
        failure = self._failures.get(provider_id)
        if failure is not None:
            raise failure
        return self._construct(self._specs[provider_id])

    def _construct(self, spec: ProviderSpec) -> Provider:
        """Run a factory once, caching either the instance or the failure."""
        try:
            instance = spec.factory(self._context)
        except ProviderError as exc:
            if exc.provider is None:
                exc.provider = spec.id
            self._failures[spec.id] = exc
            raise
        except Exception as exc:
            error = ProviderUnavailable(
                f"provider {spec.id} failed to initialise: {exc}", provider=spec.id
            )
            self._failures[spec.id] = error
            raise error from exc
        self._instances[spec.id] = instance
        return instance

    def capable(self, capability: type[C]) -> list[C]:
        """Return constructed providers satisfying ``capability``, in order.

        Specs are filtered by their declared capabilities (no module import),
        sorted by :data:`PROVIDER_ORDER`, then constructed lazily. Providers
        whose construction fails are skipped -- the failure is recorded in
        :attr:`unavailable`, never silently dropped.
        """
        matched = sorted(
            (spec for spec in self._specs.values() if capability in spec.capabilities),
            key=lambda spec: _ORDER_INDEX[spec.id],
        )
        providers: list[C] = []
        for spec in matched:
            try:
                providers.append(cast(C, self.get(spec.id)))
            except ProviderError:
                continue
        return providers

    @property
    def registered(self) -> tuple[ProviderId, ...]:
        """Registered provider ids, in :data:`PROVIDER_ORDER`."""
        return tuple(pid for pid in PROVIDER_ORDER if pid in self._specs)

    @property
    def unavailable(self) -> dict[ProviderId, ProviderError]:
        """Snapshot of providers whose construction failed (id -> error)."""
        return dict(self._failures)

    async def aclose(self) -> None:
        """Close every constructed provider that exposes an async ``aclose``."""
        for instance in self._instances.values():
            aclose = getattr(instance, "aclose", None)
            if callable(aclose):
                await aclose()

    async def __aenter__(self) -> ProviderRegistry:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


def _spotify_factory(ctx: ProviderContext) -> Provider:
    """Lazily import and build the Spotify provider (isolation constraint)."""
    from spotdl_core.providers.metadata.spotify import build_spotify_provider

    return build_spotify_provider(ctx)


def build_default_registry(context: ProviderContext) -> ProviderRegistry:
    """Return the registry wired with spotDL's built-in providers.

    Tasks 6-12 append their ``reg.register(...)`` calls here as each provider
    lands; Task 12 asserts the full built-in set is present. Every factory
    imports its provider module lazily so a broken optional dependency degrades
    exactly one provider instead of breaking registry import.
    """
    from spotdl_core.providers.base import Enriches, Resolves, Searches

    reg = ProviderRegistry(context)
    reg.register(
        ProviderSpec(
            ProviderId.SPOTIFY,
            frozenset({Resolves, Searches, Enriches}),
            _spotify_factory,
        )
    )
    return reg
