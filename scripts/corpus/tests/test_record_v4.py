"""Tests for the offline v4 pick recorder (``scripts/corpus/record_v4.py``).

These import the recorder's pure pick function as a module (never a subprocess)
and drive it with tiny hand-built corpus cases whose expected v4 behaviour was
confirmed against the real v4 ``order_results`` / ``get_best_result`` code.

The recorder module imports v4's ``spotdl.utils.matching`` from the read-only
reference tree; that import transitively needs ``yt-dlp``/``spotipy``/``requests``/
``rich`` (import-time only, no network). Those are *not* workspace runtime deps,
and the v4 reference tree is absent in CI, so this module skips cleanly when the
import fails -- keeping the default ``make check`` suite fully offline. To run it
for real, provide the deps ephemerally, e.g.::

    uv run --with yt-dlp --with spotipy --with requests --with rich \\
        pytest scripts/corpus/tests/test_record_v4.py -v
"""

import json
from pathlib import Path

import pytest

from scripts.corpus.schema import (
    CorpusAlbum,
    CorpusCandidate,
    CorpusCase,
    CorpusTrack,
)

try:
    from scripts.corpus import record_v4
except Exception as exc:  # pragma: no cover - environment-dependent skip
    pytest.skip(
        f"record_v4 unavailable (needs v4 reference tree + import-time deps): {exc}",
        allow_module_level=True,
    )


def _case(
    candidates: tuple[CorpusCandidate, ...],
    *,
    source: str = "v4-recorded",
    name: str = "Test Song",
    artists: tuple[str, ...] = ("Test Artist",),
    duration_ms: int = 200_000,
    album: str | None = "Test Album",
) -> CorpusCase:
    return CorpusCase(
        case_id="fixture-case",
        source=source,
        description="hand-built fixture",
        track=CorpusTrack(
            name=name,
            artists=artists,
            duration_ms=duration_ms,
            album=CorpusAlbum(name=album) if album is not None else None,
        ),
        candidates=candidates,
        expected_pick_index=None,
        v4_pick_index=None,
    )


def _cand(
    url: str,
    *,
    name: str = "Test Song",
    artists: tuple[str, ...] = ("Test Artist",),
    duration_ms: int = 200_000,
    album: str | None = "Test Album",
    verified: bool = False,
    popularity: int | None = None,
) -> CorpusCandidate:
    return CorpusCandidate(
        provider="ytmusic",
        provider_id=url,
        url=url,
        name=name,
        artists=artists,
        duration_ms=duration_ms,
        album=album,
        verified=verified,
        popularity=popularity,
    )


def test_clear_correct_pick_is_not_just_index_zero() -> None:
    """A decoy at index 0 gets filtered; the obvious match at index 1 is chosen."""
    case = _case(
        candidates=(
            _cand("u-decoy", name="Despacito", artists=("Luis Fonsi",), duration_ms=229_000),
            _cand(
                "u-correct",
                name="Africa",
                artists=("Toto",),
                duration_ms=295_000,
                album="Toto IV",
                verified=True,
                popularity=50,
            ),
        ),
        name="Africa",
        artists=("Toto",),
        duration_ms=295_000,
        album="Toto IV",
    )
    assert record_v4.compute_v4_pick(case) == 1


def test_views_tiebreak_picks_higher_views() -> None:
    """Two candidates tie on score; the ported views tiebreak picks higher views."""
    case = _case(
        candidates=(
            _cand("u-a", popularity=500),  # higher views -> chosen
            _cand("u-b", popularity=100),
        )
    )
    assert record_v4.compute_v4_pick(case) == 0


def test_no_views_variance_reproduces_last_iterated_shadowing_bug() -> None:
    """Equal views => v4's get_best_result returns its last-iterated near-tie entry."""
    case = _case(
        candidates=(
            _cand("u-a", popularity=100),
            _cand("u-b", popularity=100),  # last-iterated -> chosen (bug, replicated)
        )
    )
    assert record_v4.compute_v4_pick(case) == 1


def test_no_scoring_candidate_returns_none() -> None:
    """When no candidate shares a common word, order_results is empty -> None."""
    case = _case(
        candidates=(_cand("u-x", name="Completely Different", artists=("Nobody",)),),
        name="Africa",
        artists=("Toto",),
    )
    assert record_v4.compute_v4_pick(case) is None


def test_record_file_writes_picks(tmp_path: Path) -> None:
    """The CLI updater fills v4_pick_index and, for v4-recorded, expected_pick_index."""
    corpus = [
        {
            "case_id": "v4-recorded-case",
            "source": "v4-recorded",
            "description": "views tiebreak",
            "track": {
                "name": "Test Song",
                "artists": ["Test Artist"],
                "duration_ms": 200_000,
                "album": {"name": "Test Album", "year": None},
            },
            "candidates": [
                {
                    "provider": "ytmusic",
                    "provider_id": "a",
                    "url": "u-a",
                    "name": "Test Song",
                    "artists": ["Test Artist"],
                    "duration_ms": 200_000,
                    "album": "Test Album",
                    "verified": False,
                    "popularity": 500,
                },
                {
                    "provider": "ytmusic",
                    "provider_id": "b",
                    "url": "u-b",
                    "name": "Test Song",
                    "artists": ["Test Artist"],
                    "duration_ms": 200_000,
                    "album": "Test Album",
                    "verified": False,
                    "popularity": 100,
                },
            ],
            "expected_pick_index": None,
            "v4_pick_index": None,
        },
        {
            "case_id": "hand-verified-case",
            "source": "hand-verified",
            "description": "human ground truth is preserved",
            "track": {
                "name": "Test Song",
                "artists": ["Test Artist"],
                "duration_ms": 200_000,
                "album": {"name": "Test Album", "year": None},
            },
            "candidates": [
                {
                    "provider": "ytmusic",
                    "provider_id": "a",
                    "url": "u-a",
                    "name": "Test Song",
                    "artists": ["Test Artist"],
                    "duration_ms": 200_000,
                    "album": "Test Album",
                    "verified": False,
                    "popularity": 100,
                },
                {
                    "provider": "ytmusic",
                    "provider_id": "b",
                    "url": "u-b",
                    "name": "Test Song",
                    "artists": ["Test Artist"],
                    "duration_ms": 200_000,
                    "album": "Test Album",
                    "verified": False,
                    "popularity": 100,
                },
            ],
            "expected_pick_index": 0,  # human-authored, must be preserved
            "v4_pick_index": None,
        },
    ]
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")

    rc = record_v4.main([str(path)])
    assert rc == 0

    updated = json.loads(path.read_text(encoding="utf-8"))

    # v4-recorded: views tiebreak -> index 0; expected mirrors v4 pick.
    assert updated[0]["v4_pick_index"] == 0
    assert updated[0]["expected_pick_index"] == 0

    # hand-verified: v4 pick filled (shadowing -> index 1) but human ground
    # truth (0) is left untouched.
    assert updated[1]["v4_pick_index"] == 1
    assert updated[1]["expected_pick_index"] == 0
