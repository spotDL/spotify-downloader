"""Tests for the capability-based :class:`ProviderRegistry`.

These use *fake* providers exclusively -- no network, no real provider modules,
no heavy third-party deps. They pin the CONTRACT surface: deterministic
``PROVIDER_ORDER`` ordering, lazy construction with caching, isolation of
construction failures, and lifecycle (``aclose`` / ``async with``).
"""

from __future__ import annotations

import pytest
from spotdl_core.model import EntityType, Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import (
    ProvidesLyrics,
    ResolvedEntity,
    Resolves,
    Searches,
)
from spotdl_core.providers.errors import ProviderError, ProviderUnavailable
from spotdl_core.providers.registry import (
    PROVIDER_ORDER,
    ProviderContext,
    ProviderRegistry,
    ProviderSpec,
    SpotifyConfig,
    build_default_registry,
)
from spotdl_core.providers.urls import PlatformRef

# --- fake providers -------------------------------------------------------


class FakeResolver:
    """A ``Resolves``-only provider whose id is configurable per instance."""

    def __init__(self, provider_id: ProviderId) -> None:
        self.id = provider_id

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        return ResolvedEntity(
            provider=self.id,
            provider_id=ref.entity_id,
            entity_type=EntityType.TRACK,
            track=Track(name="x", artists=("a",), duration_ms=1000),
        )


class FakeResolverSearcher(FakeResolver):
    """Both ``Resolves`` and ``Searches``."""

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        return [Track(name=query, artists=("a",), duration_ms=1000)]


class FakeLyricsProvider:
    def __init__(self, provider_id: ProviderId) -> None:
        self.id = provider_id

    async def lyrics(self, track: Track) -> Lyrics | None:
        return Lyrics(kind=LyricsKind.PLAIN, text="la", source=self.id)


class ClosableResolver(FakeResolver):
    """Records ``aclose`` invocations so lifecycle can be asserted."""

    def __init__(self, provider_id: ProviderId, log: list[ProviderId]) -> None:
        super().__init__(provider_id)
        self._log = log

    async def aclose(self) -> None:
        self._log.append(self.id)


def _ctx() -> ProviderContext:
    return ProviderContext()


# --- capability filtering + ordering --------------------------------------


def test_capable_returns_matching_providers_in_provider_order() -> None:
    reg = ProviderRegistry(_ctx())
    # register out of PROVIDER_ORDER on purpose
    reg.register(
        ProviderSpec(
            id=ProviderId.GENIUS,
            capabilities=frozenset({ProvidesLyrics}),
            factory=lambda ctx: FakeLyricsProvider(ProviderId.GENIUS),
        )
    )
    reg.register(
        ProviderSpec(
            id=ProviderId.DEEZER,
            capabilities=frozenset({Resolves, Searches}),
            factory=lambda ctx: FakeResolverSearcher(ProviderId.DEEZER),
        )
    )
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: FakeResolver(ProviderId.SPOTIFY),
        )
    )

    resolvers = reg.capable(Resolves)
    assert [p.id for p in resolvers] == [ProviderId.SPOTIFY, ProviderId.DEEZER]

    searchers = reg.capable(Searches)
    assert [p.id for p in searchers] == [ProviderId.DEEZER]

    lyricists = reg.capable(ProvidesLyrics)
    assert [p.id for p in lyricists] == [ProviderId.GENIUS]


def test_registered_is_in_provider_order() -> None:
    reg = ProviderRegistry(_ctx())
    for pid in (ProviderId.GENIUS, ProviderId.SPOTIFY, ProviderId.DEEZER):
        reg.register(
            ProviderSpec(
                id=pid,
                capabilities=frozenset({Resolves}),
                factory=lambda ctx, p=pid: FakeResolver(p),
            )
        )
    assert reg.registered == (ProviderId.SPOTIFY, ProviderId.DEEZER, ProviderId.GENIUS)


def test_register_is_idempotent_later_wins() -> None:
    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: FakeResolver(ProviderId.SPOTIFY),
        )
    )
    marker = FakeResolver(ProviderId.SPOTIFY)
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: marker,
        )
    )
    assert reg.registered == (ProviderId.SPOTIFY,)
    assert reg.get(ProviderId.SPOTIFY) is marker


def test_reregister_after_construction_supersedes_cached_instance() -> None:
    reg = ProviderRegistry(_ctx())
    first = FakeResolver(ProviderId.SPOTIFY)
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: first,
        )
    )
    assert reg.get(ProviderId.SPOTIFY) is first  # constructs + caches
    second = FakeResolver(ProviderId.SPOTIFY)
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: second,
        )
    )
    # "later wins" holds even though the id was already queried.
    assert reg.get(ProviderId.SPOTIFY) is second


def test_reregister_after_failure_clears_cached_failure() -> None:
    def boom(ctx: ProviderContext) -> FakeResolver:
        raise ImportError("missing dep")

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(id=ProviderId.SPOTIFY, capabilities=frozenset({Resolves}), factory=boom)
    )
    with pytest.raises(ProviderUnavailable):
        reg.get(ProviderId.SPOTIFY)
    assert ProviderId.SPOTIFY in reg.unavailable
    # Re-registering with a working factory supersedes the cached failure.
    good = FakeResolver(ProviderId.SPOTIFY)
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: good,
        )
    )
    assert ProviderId.SPOTIFY not in reg.unavailable
    assert reg.get(ProviderId.SPOTIFY) is good


# --- lazy construction + caching ------------------------------------------


def test_get_constructs_lazily_and_caches() -> None:
    calls = {"n": 0}

    def factory(ctx: ProviderContext) -> FakeResolver:
        calls["n"] += 1
        return FakeResolver(ProviderId.SPOTIFY)

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(id=ProviderId.SPOTIFY, capabilities=frozenset({Resolves}), factory=factory)
    )
    assert calls["n"] == 0  # nothing built until asked
    first = reg.get(ProviderId.SPOTIFY)
    second = reg.get(ProviderId.SPOTIFY)
    assert first is second
    assert calls["n"] == 1


def test_get_unregistered_raises_key_error() -> None:
    reg = ProviderRegistry(_ctx())
    with pytest.raises(KeyError):
        reg.get(ProviderId.SPOTIFY)


# --- failure isolation + caching ------------------------------------------


def test_get_wraps_factory_failure_as_provider_unavailable() -> None:
    def boom(ctx: ProviderContext) -> FakeResolver:
        raise ImportError("missing dep")

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(id=ProviderId.YTMUSIC, capabilities=frozenset({Resolves}), factory=boom)
    )
    with pytest.raises(ProviderUnavailable) as excinfo:
        reg.get(ProviderId.YTMUSIC)
    assert excinfo.value.provider == ProviderId.YTMUSIC


def test_failed_construction_is_cached_for_registry_lifetime() -> None:
    calls = {"n": 0}

    def boom(ctx: ProviderContext) -> FakeResolver:
        calls["n"] += 1
        raise ImportError("missing dep")

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(id=ProviderId.YTMUSIC, capabilities=frozenset({Resolves}), factory=boom)
    )
    with pytest.raises(ProviderUnavailable):
        reg.get(ProviderId.YTMUSIC)
    with pytest.raises(ProviderUnavailable):
        reg.get(ProviderId.YTMUSIC)
    assert calls["n"] == 1
    assert ProviderId.YTMUSIC in reg.unavailable
    assert isinstance(reg.unavailable[ProviderId.YTMUSIC], ProviderUnavailable)


def test_capable_skips_providers_whose_factory_fails() -> None:
    def boom(ctx: ProviderContext) -> FakeResolver:
        raise ImportError("missing dep")

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: FakeResolver(ProviderId.SPOTIFY),
        )
    )
    reg.register(
        ProviderSpec(id=ProviderId.DEEZER, capabilities=frozenset({Resolves}), factory=boom)
    )
    resolvers = reg.capable(Resolves)
    assert [p.id for p in resolvers] == [ProviderId.SPOTIFY]
    assert ProviderId.DEEZER in reg.unavailable
    assert isinstance(reg.unavailable[ProviderId.DEEZER], ProviderError)


def test_unavailable_is_a_copy() -> None:
    def boom(ctx: ProviderContext) -> FakeResolver:
        raise ImportError("x")

    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(id=ProviderId.DEEZER, capabilities=frozenset({Resolves}), factory=boom)
    )
    with pytest.raises(ProviderUnavailable):
        reg.get(ProviderId.DEEZER)
    snapshot = reg.unavailable
    snapshot.clear()
    assert ProviderId.DEEZER in reg.unavailable


# --- lifecycle ------------------------------------------------------------


async def test_aclose_closes_constructed_providers() -> None:
    log: list[ProviderId] = []
    reg = ProviderRegistry(_ctx())
    reg.register(
        ProviderSpec(
            id=ProviderId.SPOTIFY,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: ClosableResolver(ProviderId.SPOTIFY, log),
        )
    )
    reg.register(
        ProviderSpec(
            id=ProviderId.DEEZER,
            capabilities=frozenset({Resolves}),
            factory=lambda ctx: ClosableResolver(ProviderId.DEEZER, log),
        )
    )
    # only construct SPOTIFY
    reg.get(ProviderId.SPOTIFY)
    await reg.aclose()
    assert log == [ProviderId.SPOTIFY]


async def test_async_context_manager_closes_on_exit() -> None:
    log: list[ProviderId] = []
    async with ProviderRegistry(_ctx()) as reg:
        reg.register(
            ProviderSpec(
                id=ProviderId.SPOTIFY,
                capabilities=frozenset({Resolves}),
                factory=lambda ctx: ClosableResolver(ProviderId.SPOTIFY, log),
            )
        )
        reg.get(ProviderId.SPOTIFY)
    assert log == [ProviderId.SPOTIFY]


# --- contract shapes ------------------------------------------------------


def test_provider_order_is_the_contract_tuple() -> None:
    assert PROVIDER_ORDER == (
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
        ProviderId.LASTFM,
    )
    # every provider id has a place in the ordering
    assert set(PROVIDER_ORDER) == set(ProviderId)


def test_provider_context_defaults() -> None:
    ctx = ProviderContext()
    assert isinstance(ctx.spotify, SpotifyConfig)
    assert ctx.spotify.prefer_anonymous is True
    assert ctx.ytmusic_language == "en"
    assert isinstance(ctx.piped_instances, tuple)
    assert ctx.user_agent  # non-empty default UA


def test_spotify_config_from_env_reads_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTDL_SPOTIFY_CLIENT_ID", "cid")
    monkeypatch.setenv("SPOTDL_SPOTIFY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SPOTDL_SPOTIFY_TOTP_SECRET", "TOTPSEED")
    monkeypatch.setenv("SPOTDL_SPOTIFY_PREFER_ANONYMOUS", "0")
    cfg = SpotifyConfig.from_env()
    assert cfg.client_id == "cid"
    assert cfg.client_secret == "secret"
    assert cfg.totp_secret_override == "TOTPSEED"
    assert cfg.prefer_anonymous is False


def test_spotify_config_from_env_keeps_defaults_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for var in (
        "SPOTDL_SPOTIFY_CLIENT_ID",
        "SPOTDL_SPOTIFY_CLIENT_SECRET",
        "SPOTDL_SPOTIFY_TOTP_SECRET",
        "SPOTDL_SPOTIFY_PREFER_ANONYMOUS",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = SpotifyConfig.from_env()
    assert cfg.client_id is None
    assert cfg.client_secret is None
    assert cfg.totp_secret_override is None
    assert cfg.prefer_anonymous is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("0", False), ("false", False), ("False", False), ("1", True), ("true", True)],
)
def test_spotify_config_prefer_anonymous_parsing(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("SPOTDL_SPOTIFY_PREFER_ANONYMOUS", raw)
    assert SpotifyConfig.from_env().prefer_anonymous is expected


def test_build_default_registry_returns_registry() -> None:
    reg = build_default_registry(_ctx())
    assert isinstance(reg, ProviderRegistry)


def test_registry_module_imports_without_provider_deps() -> None:
    import importlib

    module = importlib.import_module("spotdl_core.providers.registry")
    assert hasattr(module, "ProviderRegistry")
    assert hasattr(module, "PROVIDER_ORDER")
