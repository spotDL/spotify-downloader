"""Offline tests for the shared multi-provider search helper (no DB).

``provider_search`` runs every ``Searches`` provider in PROVIDER_ORDER,
concatenates results, de-duplicates by ISRC then by ``(name, main_artist)``, and
truncates to ``limit``. A ``ProviderError`` from one searcher records its id in
the returned failed set and never aborts the others.
"""

from __future__ import annotations

from spotdl_core.model import ProviderId, Track
from spotdl_core.providers import ProviderUnavailable
from spotdl_server.services.provider_search import provider_search

from apps.server.tests.fakes import FakeSearcher, build_fake_registry


def _track(name: str, artist: str, *, isrc: str | None = None) -> Track:
    return Track(name=name, artists=(artist,), duration_ms=180_000, isrc=isrc)


async def test_merges_two_searchers_in_provider_order() -> None:
    spotify = FakeSearcher(id=ProviderId.SPOTIFY, tracks=[_track("A", "X"), _track("B", "Y")])
    deezer = FakeSearcher(id=ProviderId.DEEZER, tracks=[_track("C", "Z")])
    registry = build_fake_registry(deezer, spotify)  # registration order irrelevant

    tracks, failed = await provider_search(registry, "q")

    # PROVIDER_ORDER puts SPOTIFY before DEEZER regardless of registration order.
    assert [t.name for t in tracks] == ["A", "B", "C"]
    assert failed == set()


async def test_dedupes_by_isrc_then_name_artist() -> None:
    spotify = FakeSearcher(
        id=ProviderId.SPOTIFY,
        tracks=[_track("Song", "Artist", isrc="ISRC1")],
    )
    deezer = FakeSearcher(
        id=ProviderId.DEEZER,
        tracks=[
            _track("Song (Remaster)", "Artist", isrc="ISRC1"),  # dup by ISRC
            _track("Song", "Artist", isrc="ISRC2"),  # dup by (name, main_artist)
            _track("Other", "Artist", isrc="ISRC3"),  # kept
        ],
    )
    registry = build_fake_registry(spotify, deezer)

    tracks, failed = await provider_search(registry, "q")

    assert [t.name for t in tracks] == ["Song", "Other"]
    assert failed == set()


async def test_truncates_to_limit() -> None:
    spotify = FakeSearcher(
        id=ProviderId.SPOTIFY,
        tracks=[_track(f"T{i}", f"A{i}") for i in range(10)],
    )
    registry = build_fake_registry(spotify)

    tracks, _failed = await provider_search(registry, "q", limit=3)

    assert len(tracks) == 3
    assert [t.name for t in tracks] == ["T0", "T1", "T2"]


async def test_one_failing_searcher_records_id_and_keeps_others() -> None:
    spotify = FakeSearcher(
        id=ProviderId.SPOTIFY,
        error=ProviderUnavailable("down", provider=ProviderId.SPOTIFY),
    )
    deezer = FakeSearcher(id=ProviderId.DEEZER, tracks=[_track("Kept", "Artist")])
    registry = build_fake_registry(spotify, deezer)

    tracks, failed = await provider_search(registry, "q")

    assert [t.name for t in tracks] == ["Kept"]
    assert failed == {ProviderId.SPOTIFY}
