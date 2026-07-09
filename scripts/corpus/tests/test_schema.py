"""Tests for the golden-corpus JSON schema, model mapping, and validator.

These are pure/offline structural tests: they build ``CorpusCase`` dicts by
hand, round-trip them through the pydantic models, exercise the ``extra=forbid``
and index-range guards, verify the ``to_track`` / ``to_candidates`` conversion
into ``spotdl_core.model`` objects, and check the cross-file duplicate-``case_id``
detection used by the CLI validator.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from spotdl_core.model import AlbumRef, AudioCandidate, ProviderId, Track

from scripts.corpus.schema import (
    Corpus,
    CorpusAlbum,
    CorpusCandidate,
    CorpusCase,
    CorpusTrack,
    to_candidates,
    to_track,
)
from scripts.corpus.validate import (
    Summary,
    _expand,
    duplicate_case_ids,
    load_cases,
    run,
    summarize,
    validate_paths,
)


def _case_dict(**overrides: object) -> dict[str, object]:
    """A minimal, valid ``CorpusCase`` as a plain dict (JSON-shaped)."""
    base: dict[str, object] = {
        "case_id": "basic-remix-trap",
        "source": "hand-verified",
        "description": "candidate 1 is a remix; correct pick is the clean original",
        "track": {
            "name": "Song Title",
            "artists": ["Real Artist", "Feature Artist"],
            "duration_ms": 210_000,
            "album": {"name": "The Album", "year": 2020},
            "isrc": "USABC1234567",
            "explicit": False,
            "provider": "spotify",
            "provider_id": "spotify-track-id",
        },
        "candidates": [
            {
                "provider": "ytmusic",
                "provider_id": "abc123",
                "url": "https://music.youtube.com/watch?v=abc123",
                "name": "Song Title",
                "artists": ["Real Artist"],
                "duration_ms": 211_000,
                "album": "The Album",
                "isrc": "USABC1234567",
                "verified": True,
                "popularity": 90,
            },
            {
                "provider": "ytmusic",
                "provider_id": "def456",
                "url": "https://music.youtube.com/watch?v=def456",
                "name": "Song Title (Remix)",
            },
        ],
        "expected_pick_index": 0,
        "v4_pick_index": 0,
        "notes": "",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Round-trip / schema conformance
# --------------------------------------------------------------------------- #


def test_valid_case_round_trips() -> None:
    case = CorpusCase.model_validate(_case_dict())
    dumped = case.model_dump()
    again = CorpusCase.model_validate(dumped)
    assert again == case
    # JSON round-trip too (this is a JSON contract).
    from_json = CorpusCase.model_validate_json(case.model_dump_json())
    assert from_json == case


def test_corpus_wrapper_round_trips() -> None:
    corpus = Corpus(cases=(CorpusCase.model_validate(_case_dict()),))
    assert Corpus.model_validate(corpus.model_dump()) == corpus


def test_models_are_frozen() -> None:
    case = CorpusCase.model_validate(_case_dict())
    with pytest.raises(ValidationError):
        case.case_id = "mutated"


@pytest.mark.parametrize(
    "container",
    ["case", "track", "album", "candidate"],
)
def test_extra_keys_forbidden(container: str) -> None:
    data = _case_dict()
    if container == "case":
        data["surprise"] = 1
    elif container == "track":
        data["track"]["surprise"] = 1  # type: ignore[index]
    elif container == "album":
        data["track"]["album"]["surprise"] = 1  # type: ignore[index]
    else:
        data["candidates"][0]["surprise"] = 1  # type: ignore[index]
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(data)


# --------------------------------------------------------------------------- #
# Field-level validators
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad_source", ["v4recorded", "recorded", "", "Hand-Verified"])
def test_source_must_be_in_allowed_set(bad_source: str) -> None:
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(_case_dict(source=bad_source))


@pytest.mark.parametrize("source", ["v4-recorded", "hand-verified"])
def test_allowed_sources_accepted(source: str) -> None:
    assert CorpusCase.model_validate(_case_dict(source=source)).source == source


@pytest.mark.parametrize(
    "bad_id",
    ["Not_Kebab", "has spaces", "UPPER", "trailing-", "-leading", "double--dash", "under_score"],
)
def test_case_id_must_be_kebab(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(_case_dict(case_id=bad_id))


@pytest.mark.parametrize("good_id", ["a", "abc", "abc-123", "remix-trap-01", "x1-y2-z3"])
def test_kebab_case_ids_accepted(good_id: str) -> None:
    assert CorpusCase.model_validate(_case_dict(case_id=good_id)).case_id == good_id


def test_candidates_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(_case_dict(candidates=[]))


def test_track_artists_must_be_non_empty() -> None:
    data = _case_dict()
    data["track"]["artists"] = []  # type: ignore[index]
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(data)


# --------------------------------------------------------------------------- #
# Index-range validator (model-level: needs len(candidates))
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("field", ["expected_pick_index", "v4_pick_index"])
@pytest.mark.parametrize("bad", [2, 5, -1])
def test_out_of_range_index_raises(field: str, bad: int) -> None:
    # _case_dict has exactly 2 candidates -> valid indices are 0, 1, or None.
    with pytest.raises(ValidationError):
        CorpusCase.model_validate(_case_dict(**{field: bad}))


@pytest.mark.parametrize("field", ["expected_pick_index", "v4_pick_index"])
def test_none_index_allowed(field: str) -> None:
    case = CorpusCase.model_validate(_case_dict(**{field: None}))
    assert getattr(case, field) is None


def test_in_range_index_allowed() -> None:
    case = CorpusCase.model_validate(_case_dict(expected_pick_index=1, v4_pick_index=1))
    assert case.expected_pick_index == 1


# --------------------------------------------------------------------------- #
# Model mapping: to_track / to_candidates
# --------------------------------------------------------------------------- #


def test_to_track_maps_all_fields() -> None:
    ct = CorpusTrack(
        name="Song Title",
        artists=("Real Artist", "Feature Artist"),
        duration_ms=210_000,
        album=CorpusAlbum(name="The Album", year=2020),
        isrc="USABC1234567",
        explicit=True,
        provider="spotify",
        provider_id="spotify-track-id",
    )
    track = to_track(ct)
    assert isinstance(track, Track)
    assert track.name == "Song Title"
    assert track.artists == ("Real Artist", "Feature Artist")
    assert track.main_artist == "Real Artist"
    assert track.duration_ms == 210_000
    assert track.album == AlbumRef(name="The Album", year=2020)
    assert track.isrc == "USABC1234567"
    assert track.explicit is True
    assert track.provider is ProviderId.SPOTIFY
    assert track.provider_id == "spotify-track-id"


def test_to_track_without_optional_fields() -> None:
    ct = CorpusTrack(name="Bare", artists=("Solo",), duration_ms=100_000)
    track = to_track(ct)
    assert track.album is None
    assert track.isrc is None
    assert track.explicit is None
    assert track.provider is None
    assert track.provider_id is None


def test_to_candidates_maps_all_fields() -> None:
    cands = (
        CorpusCandidate(
            provider="ytmusic",
            provider_id="abc123",
            url="https://music.youtube.com/watch?v=abc123",
            name="Song Title",
            artists=("Real Artist",),
            duration_ms=211_000,
            album="The Album",
            isrc="USABC1234567",
            verified=True,
            popularity=90,
        ),
        CorpusCandidate(
            provider="soundcloud",
            provider_id="def456",
            url="https://soundcloud.com/x/def456",
            name="Other",
        ),
    )
    out = to_candidates(cands)
    assert [type(c) for c in out] == [AudioCandidate, AudioCandidate]
    first = out[0]
    assert first.provider is ProviderId.YTMUSIC
    assert first.provider_id == "abc123"
    assert first.url == "https://music.youtube.com/watch?v=abc123"
    assert first.name == "Song Title"
    assert first.artists == ("Real Artist",)
    assert first.duration_ms == 211_000
    assert first.album == "The Album"
    assert first.isrc == "USABC1234567"
    assert first.verified is True
    assert first.popularity == 90
    # defaults on the bare candidate
    second = out[1]
    assert second.provider is ProviderId.SOUNDCLOUD
    assert second.artists == ()
    assert second.duration_ms is None
    assert second.album is None
    assert second.verified is False
    assert second.popularity is None


def test_mapping_from_parsed_case() -> None:
    case = CorpusCase.model_validate(_case_dict())
    track = to_track(case.track)
    cands = to_candidates(case.candidates)
    assert track.name == "Song Title"
    assert len(cands) == 2
    assert case.candidates[case.expected_pick_index or 0].provider_id == cands[0].provider_id


# --------------------------------------------------------------------------- #
# Validator: duplicate detection, summary, file loading
# --------------------------------------------------------------------------- #


def _write_corpus(path: Path, cases: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(cases), encoding="utf-8")


def test_load_cases_reads_json_array(tmp_path: Path) -> None:
    p = tmp_path / "a.json"
    _write_corpus(p, [_case_dict(case_id="one"), _case_dict(case_id="two")])
    cases = load_cases(p)
    assert [c.case_id for c in cases] == ["one", "two"]


def test_duplicate_case_ids_within_file() -> None:
    cases = [
        CorpusCase.model_validate(_case_dict(case_id="dup")),
        CorpusCase.model_validate(_case_dict(case_id="dup")),
        CorpusCase.model_validate(_case_dict(case_id="unique")),
    ]
    assert duplicate_case_ids(cases) == ["dup"]


def test_no_duplicates_returns_empty() -> None:
    cases = [
        CorpusCase.model_validate(_case_dict(case_id="a")),
        CorpusCase.model_validate(_case_dict(case_id="b")),
    ]
    assert duplicate_case_ids(cases) == []


def test_summarize_counts_by_source() -> None:
    cases = [
        CorpusCase.model_validate(_case_dict(case_id="a", source="hand-verified")),
        CorpusCase.model_validate(_case_dict(case_id="b", source="hand-verified")),
        CorpusCase.model_validate(_case_dict(case_id="c", source="v4-recorded")),
    ]
    assert summarize(cases) == Summary(total=3, hand_verified=2, v4_recorded=1)


def test_validate_paths_ok(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "a.json", [_case_dict(case_id="one")])
    _write_corpus(tmp_path / "b.json", [_case_dict(case_id="two")])
    cases, errors = validate_paths([tmp_path / "a.json", tmp_path / "b.json"])
    assert errors == []
    assert {c.case_id for c in cases} == {"one", "two"}


def test_validate_paths_flags_cross_file_duplicate(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "a.json", [_case_dict(case_id="shared")])
    _write_corpus(tmp_path / "b.json", [_case_dict(case_id="shared")])
    _cases, errors = validate_paths([tmp_path / "a.json", tmp_path / "b.json"])
    assert errors
    assert any("shared" in e for e in errors)


def test_validate_paths_reports_bad_index(tmp_path: Path) -> None:
    bad = _case_dict(case_id="bad-index")
    bad["expected_pick_index"] = 9  # out of range for 2 candidates
    _write_corpus(tmp_path / "bad.json", [bad])
    _cases, errors = validate_paths([tmp_path / "bad.json"])
    assert errors
    assert any("bad.json" in e for e in errors)


def test_expand_skips_baseline_json(tmp_path: Path) -> None:
    """The ``corpus/*.json`` glob must not surface the derived baseline sibling."""
    _write_corpus(tmp_path / "recorded.json", [_case_dict(case_id="one")])
    (tmp_path / "baseline.json").write_text(
        json.dumps({"total": 1, "v4_accuracy": 1.0}), encoding="utf-8"
    )
    matched = _expand([str(tmp_path / "*.json")])
    names = {p.name for p in matched}
    assert names == {"recorded.json"}
    assert "baseline.json" not in names


def test_run_glob_ignores_baseline_json_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Regression: `validate "<corpus>/*.json"` returns 0 despite a sibling
    ``baseline.json`` (a JSON object, not an array of cases) in the same dir."""
    _write_corpus(tmp_path / "recorded.json", [_case_dict(case_id="one")])
    _write_corpus(tmp_path / "handcrafted.json", [_case_dict(case_id="two")])
    (tmp_path / "baseline.json").write_text(
        json.dumps({"total": 2, "v4_correct": 2, "v4_accuracy": 1.0}),
        encoding="utf-8",
    )
    code = run([str(tmp_path / "*.json")])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "baseline.json" not in captured.err
    assert "2 cases" in captured.out
