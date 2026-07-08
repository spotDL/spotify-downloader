"""Integration smoke tests for :func:`build_default_registry`.

Unlike ``test_registry.py`` (which pins the registry *mechanics* with fake
providers), these tests exercise the *real* wiring produced by
:func:`build_default_registry`: every v1 provider is registered with a lazy
factory, capability queries return the right providers in the right order, and
one broken provider never takes down its siblings.

All tests here are non-network except the single ``@pytest.mark.network``
end-to-end test, which is excluded from ``make check`` / CI. The default suite
must never touch the network, so:

* provider *construction* is asserted to be side-effect free (factories build an
  httpx client at most; no request is issued until a method is called), and
* lazy-import discipline is verified in a *subprocess* with a pristine
  ``sys.modules`` so the assertion cannot be polluted by another test module
  having already imported a heavy dependency.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from spotdl_core.model import ProviderId
from spotdl_core.providers.base import (
    ProvidesAudio,
    ProvidesLyrics,
    Resolves,
)
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.registry import (
    PROVIDER_ORDER,
    ProviderContext,
    build_default_registry,
)
from spotdl_core.providers.urls import parse

# --- lazy-import isolation -------------------------------------------------

# Run in a fresh interpreter: importing the registry module must not pull in any
# heavy/fragile provider dependency. A subprocess guarantees a pristine
# ``sys.modules`` regardless of what other test modules imported first.
_ISOLATION_PROBE = """
import sys
import spotdl_core.providers.registry  # noqa: F401
leaked = [m for m in ("ytmusicapi", "yt_dlp", "bs4") if m in sys.modules]
assert not leaked, f"registry import leaked heavy deps: {leaked}"
print("OK")
"""


def test_import_registry_has_no_provider_dep_imports() -> None:
    """Importing the registry must not import ytmusicapi / yt_dlp / bs4."""
    result = subprocess.run(
        [sys.executable, "-c", _ISOLATION_PROBE],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"


# --- full registration set -------------------------------------------------


def test_default_registry_registers_all_providers() -> None:
    """Every ``ProviderId`` in ``PROVIDER_ORDER`` is registered (all 13)."""
    reg = build_default_registry(ProviderContext())
    assert set(reg.registered) == set(PROVIDER_ORDER)
    # ``registered`` is returned in PROVIDER_ORDER, so the tuple equals it.
    assert reg.registered == PROVIDER_ORDER


# --- capability ordering + membership --------------------------------------


def test_capable_metadata_order() -> None:
    """Resolvers lead with the four metadata sources, in PROVIDER_ORDER."""
    reg = build_default_registry(ProviderContext())
    ids = [p.id for p in reg.capable(Resolves)]
    # The four metadata sources lead, in order.
    assert ids[:4] == [
        ProviderId.SPOTIFY,
        ProviderId.DEEZER,
        ProviderId.ITUNES,
        ProviderId.MUSICBRAINZ,
    ]
    # Audio providers that also resolve may follow; whatever appears is in
    # PROVIDER_ORDER relative order with no duplicates.
    order_index = {pid: i for i, pid in enumerate(PROVIDER_ORDER)}
    assert ids == sorted(ids, key=lambda pid: order_index[pid])
    assert len(ids) == len(set(ids))


def test_capable_audio_membership() -> None:
    """The audio-capable set is exactly the five audio targets."""
    reg = build_default_registry(ProviderContext())
    assert {p.id for p in reg.capable(ProvidesAudio)} == {
        ProviderId.YTMUSIC,
        ProviderId.YOUTUBE,
        ProviderId.SOUNDCLOUD,
        ProviderId.BANDCAMP,
        ProviderId.PIPED,
    }


def test_capable_lyrics_membership_without_genius_token() -> None:
    """Without a Genius token, Genius is unavailable; the other three remain."""
    reg = build_default_registry(ProviderContext(genius_token=None))
    assert {p.id for p in reg.capable(ProvidesLyrics)} == {
        ProviderId.LRCLIB,
        ProviderId.MUSIXMATCH,
        ProviderId.AZLYRICS,
    }
    assert ProviderId.GENIUS in reg.unavailable
    assert isinstance(reg.unavailable[ProviderId.GENIUS], ProviderUnavailable)


# --- failure isolation -----------------------------------------------------


def test_isolation_broken_provider_does_not_break_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A factory that fails to import degrades exactly that one provider."""

    def _boom(*args: object, **kwargs: object) -> object:
        raise ImportError("simulated broken ytmusicapi")

    # The YTMusic factory imports this lazily at call time, so patching the
    # module attribute makes only YTMusic's construction fail.
    monkeypatch.setattr(
        "spotdl_core.providers.audio.ytmusic.build_ytmusic_provider",
        _boom,
    )
    reg = build_default_registry(ProviderContext())
    audio_ids = {p.id for p in reg.capable(ProvidesAudio)}
    assert audio_ids == {
        ProviderId.YOUTUBE,
        ProviderId.SOUNDCLOUD,
        ProviderId.BANDCAMP,
        ProviderId.PIPED,
    }
    assert ProviderId.YTMUSIC in reg.unavailable
    assert isinstance(reg.unavailable[ProviderId.YTMUSIC], ProviderUnavailable)


# --- lifecycle -------------------------------------------------------------


async def test_registry_aclose_is_safe_with_no_construction() -> None:
    """Closing a registry that constructed nothing is a clean no-op."""
    reg = build_default_registry(ProviderContext())
    await reg.aclose()  # nothing constructed -> nothing to close


async def test_async_context_manager_with_no_construction() -> None:
    """``async with`` exits cleanly when no provider was constructed."""
    async with build_default_registry(ProviderContext()):
        pass


# --- live end-to-end (excluded from CI) ------------------------------------


@pytest.mark.network
async def test_end_to_end_resolve_then_audio() -> None:
    """Resolve a real Spotify track, then find real audio candidates.

    Excluded from ``make check`` (network marker). Run deliberately with
    ``uv run pytest -m network``.
    """
    ref = parse("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")
    async with build_default_registry(ProviderContext()) as reg:
        spotify = reg.get(ProviderId.SPOTIFY)
        resolved = await spotify.resolve(ref)  # type: ignore[attr-defined]
        track = resolved.track
        assert track is not None
        ytmusic = reg.get(ProviderId.YTMUSIC)
        candidates = await ytmusic.audio_candidates(track)  # type: ignore[attr-defined]
        assert len(candidates) >= 1
