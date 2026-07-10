"""Offline tests for the shared multi-provider search helper (no DB).

``provider_search`` runs every ``Searches`` provider in PROVIDER_ORDER,
concatenates results, de-duplicates by ISRC then by ``(name, main_artist)``, and
truncates to ``limit``. A ``ProviderError`` from one searcher records its id in
the returned failed set and never aborts the others.
"""

from __future__ import annotations

from spotdl_core.model import EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers import ProviderUnavailable
from spotdl_server.services.provider_search import (
    provider_search,
    provider_search_entities,
)

from apps.server.tests.fakes import (
    FakeEntitySearcher,
    FakeSearcher,
    build_fake_registry,
)

_ALL_TYPES = frozenset({EntityType.TRACK, EntityType.ALBUM, EntityType.ARTIST, EntityType.PLAYLIST})


def _track(
    name: str,
    artist: str,
    *,
    isrc: str | None = None,
    provider: ProviderId | None = None,
    provider_id: str | None = None,
) -> Track:
    return Track(
        name=name,
        artists=(artist,),
        duration_ms=180_000,
        isrc=isrc,
        provider=provider,
        provider_id=provider_id,
    )


def _hit(
    entity_type: EntityType,
    name: str,
    *,
    subtitle: str | None = None,
    provider: ProviderId = ProviderId.SPOTIFY,
    provider_id: str = "x1",
    isrc: str | None = None,
) -> SearchHit:
    return SearchHit(
        entity_type=entity_type,
        provider=provider,
        provider_id=provider_id,
        name=name,
        subtitle=subtitle,
        isrc=isrc,
    )


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


# --- provider_search_entities (universal) ---------------------------------


async def test_entities_groups_hits_by_type() -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[
            _hit(EntityType.ALBUM, "Al", provider_id="al1"),
            _hit(EntityType.ARTIST, "Ar", provider_id="ar1"),
            _hit(EntityType.PLAYLIST, "Pl", provider_id="pl1"),
        ],
    )
    registry = build_fake_registry(spotify)

    by_type, failed = await provider_search_entities(registry, "q", types=_ALL_TYPES)

    assert failed == set()
    assert [h.name for h in by_type[EntityType.ALBUM]] == ["Al"]
    assert [h.name for h in by_type[EntityType.ARTIST]] == ["Ar"]
    assert [h.name for h in by_type[EntityType.PLAYLIST]] == ["Pl"]
    assert by_type[EntityType.TRACK] == []  # no track hits from this provider


async def test_entities_track_fallback_from_track_only_searcher() -> None:
    # SPOTIFY does entity search (albums); ITUNES is track-only (Searches).
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY, hits=[_hit(EntityType.ALBUM, "Al", provider_id="al1")]
    )
    itunes = FakeSearcher(
        id=ProviderId.ITUNES,
        tracks=[_track("Song", "Artist", provider=ProviderId.ITUNES, provider_id="it1")],
    )
    registry = build_fake_registry(spotify, itunes)

    by_type, failed = await provider_search_entities(registry, "q", types=_ALL_TYPES)

    assert failed == set()
    # The track-only searcher's result is synthesised into a track hit.
    assert [h.name for h in by_type[EntityType.TRACK]] == ["Song"]
    assert by_type[EntityType.TRACK][0].provider is ProviderId.ITUNES
    assert [h.name for h in by_type[EntityType.ALBUM]] == ["Al"]


async def test_entities_skip_track_fallback_when_not_requested() -> None:
    itunes = FakeSearcher(
        id=ProviderId.ITUNES,
        tracks=[_track("Song", "Artist", provider=ProviderId.ITUNES, provider_id="it1")],
    )
    registry = build_fake_registry(itunes)

    by_type, _failed = await provider_search_entities(
        registry, "q", types=frozenset({EntityType.ALBUM})
    )

    assert EntityType.TRACK not in by_type  # track fallback not run
    assert by_type[EntityType.ALBUM] == []


async def test_entities_dedupe_tracks_by_isrc_then_name_subtitle() -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[
            _hit(EntityType.TRACK, "Song", subtitle="Artist", provider_id="t1", isrc="ISRC1"),
        ],
    )
    deezer = FakeEntitySearcher(
        id=ProviderId.DEEZER,
        hits=[
            _hit(
                EntityType.TRACK,
                "Song (Live)",
                subtitle="Artist",
                provider=ProviderId.DEEZER,
                provider_id="t2",
                isrc="ISRC1",
            ),  # dup by ISRC
            _hit(
                EntityType.TRACK,
                "song",
                subtitle="artist",
                provider=ProviderId.DEEZER,
                provider_id="t3",
                isrc="ISRC2",
            ),  # dup by (name, subtitle)
            _hit(
                EntityType.TRACK,
                "Other",
                subtitle="Artist",
                provider=ProviderId.DEEZER,
                provider_id="t4",
            ),  # kept
        ],
    )
    registry = build_fake_registry(spotify, deezer)

    by_type, _failed = await provider_search_entities(
        registry, "q", types=frozenset({EntityType.TRACK})
    )

    assert [h.name for h in by_type[EntityType.TRACK]] == ["Song", "Other"]


async def test_entities_dedupe_albums_by_name_subtitle() -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[_hit(EntityType.ALBUM, "Discovery", subtitle="Daft Punk", provider_id="a1")],
    )
    deezer = FakeEntitySearcher(
        id=ProviderId.DEEZER,
        hits=[
            _hit(
                EntityType.ALBUM,
                "discovery",
                subtitle="daft punk",
                provider=ProviderId.DEEZER,
                provider_id="a2",
            )
        ],
    )
    registry = build_fake_registry(spotify, deezer)

    by_type, _failed = await provider_search_entities(
        registry, "q", types=frozenset({EntityType.ALBUM})
    )

    # SPOTIFY ranks first in PROVIDER_ORDER → its copy wins.
    assert [h.provider_id for h in by_type[EntityType.ALBUM]] == ["a1"]


async def test_entities_truncates_each_type_to_limit() -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        hits=[_hit(EntityType.ALBUM, f"Al{i}", provider_id=f"a{i}") for i in range(10)],
    )
    registry = build_fake_registry(spotify)

    by_type, _failed = await provider_search_entities(
        registry, "q", types=frozenset({EntityType.ALBUM}), limit=3
    )

    assert [h.name for h in by_type[EntityType.ALBUM]] == ["Al0", "Al1", "Al2"]


async def test_entities_failing_provider_records_id() -> None:
    spotify = FakeEntitySearcher(
        id=ProviderId.SPOTIFY,
        error=ProviderUnavailable("down", provider=ProviderId.SPOTIFY),
    )
    deezer = FakeEntitySearcher(
        id=ProviderId.DEEZER,
        hits=[_hit(EntityType.ALBUM, "Kept", provider=ProviderId.DEEZER, provider_id="a1")],
    )
    registry = build_fake_registry(spotify, deezer)

    by_type, failed = await provider_search_entities(
        registry, "q", types=frozenset({EntityType.ALBUM})
    )

    assert [h.name for h in by_type[EntityType.ALBUM]] == ["Kept"]
    assert failed == {ProviderId.SPOTIFY}
