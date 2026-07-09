# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "rapidfuzz>=3.10.1,<4",
#     "python-slugify[unidecode]>=8.0.4,<9",
#     "pykakasi>=2.3.0,<3",
#     "yt-dlp>=2025.09.26,<2027",   # imported by spotdl.utils.formatter (never invoked)
#     "spotipy>=2.24.0,<3",         # imported via spotdl.types.song -> spotdl.utils.spotify
#     "requests>=2.32.3,<3",        # imported by spotdl.utils.spotify
#     "rich>=13.9.4,<14",           # imported by spotdl.utils.logging
#     "typing_extensions>=4.0,<5",  # imported by spotdl.types.options (via spotdl.utils.config)
# ]
# ///
"""Offline recorder: replays spotDL v4's matcher pick over stored candidate sets.

This is workspace tooling, not a published package. Run it as a standalone
PEP-723 script (no network, import-time-only deps supplied by ``uv``)::

    uv run --script scripts/corpus/record_v4.py packages/core/tests/matching/corpus/*.json

or import :func:`compute_v4_pick` from it in a test. For every case it computes
the index of the candidate that v4's ``order_results`` + ``get_best_result``
would pick, writes it into ``v4_pick_index``, and -- only for ``v4-recorded``
cases -- mirrors it into ``expected_pick_index`` (``hand-verified`` ground truth
is left untouched).

It calls **only pure functions** (``order_results`` / ``get_best_matches``); it
never instantiates ``AudioProvider`` and never imports ``spotdl.providers.audio``,
so no I/O happens. v4's ``spotdl/__init__.py`` eagerly imports the whole app, so
we register stub parent packages before importing the leaf submodules -- this
loads ``spotdl.utils.matching`` without running the package ``__init__``. The
stubbed submodule chain still transitively imports ``yt_dlp`` / ``spotipy`` /
``requests`` / ``rich`` at module load (never used for I/O); those are pinned in
the PEP-723 header above.
"""

import argparse
import json
import sys
import types
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

V4 = Path("~/Projects/xnetcat/spotdl-v4-reference").expanduser()


def _stub_pkg(name: str, path: Path) -> None:
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]  # make it a package without running __init__.py
    sys.modules[name] = mod


sys.path.insert(0, str(V4))
_stub_pkg("spotdl", V4 / "spotdl")
_stub_pkg("spotdl.utils", V4 / "spotdl" / "utils")
_stub_pkg("spotdl.types", V4 / "spotdl" / "types")

from spotdl.types.result import Result  # type: ignore[import-not-found]  # noqa: E402
from spotdl.types.song import Song  # type: ignore[import-not-found]  # noqa: E402
from spotdl.utils.matching import (  # type: ignore[import-not-found]  # noqa: E402
    get_best_matches,
    order_results,
)


def to_v4_song(t: Any) -> "Song":
    """Reconstruct a v4 ``Song`` from a corpus track (all ~20 fields required)."""
    return Song(
        name=t.name,
        artists=list(t.artists),
        artist=t.artists[0],
        genres=[],  # placeholder, unread by order_results
        disc_number=1,  # placeholder
        disc_count=1,  # placeholder
        album_name=t.album.name if t.album else "",  # read by calc_album_match
        album_artist=t.artists[0],  # placeholder
        duration=round(t.duration_ms / 1000),  # read by calc_time_match (seconds)
        year=(t.album.year if t.album and t.album.year else 0),  # placeholder
        date="",  # placeholder
        track_number=1,  # placeholder
        tracks_count=1,  # placeholder
        song_id=t.provider_id or t.name,  # debug-log key only
        explicit=t.explicit,  # may be None; order_results guards on `is not None`
        publisher="",  # placeholder
        url="",  # placeholder
        isrc=t.isrc,
        cover_url=None,  # placeholder
        copyright_text=None,  # placeholder
    )


def to_v4_result(c: Any) -> "Result":
    """Reconstruct a v4 ``Result`` from a corpus candidate."""
    return Result(
        source=c.provider,
        url=c.url,
        verified=c.verified,
        name=c.name,
        duration=(c.duration_ms or 0) / 1000,
        author=(c.artists[0] if c.artists else ""),
        result_id=c.provider_id,
        isrc_search=False,  # stored sets are not ISRC-search mode
        search_query=None,
        artists=tuple(c.artists) or None,
        views=c.popularity,  # stored views -> no get_views network call
        explicit=None,
        album=c.album,
    )


def _select_best(scores: Any) -> Any:
    """Replicate v4 ``AudioProvider.get_best_result``'s *pure* selection, bug-for-bug.

    Offline substitutions (settled in the brief): stored ``Result.views`` are used
    verbatim and a missing/zero view count stands in for v4's ``get_views`` network
    fallback (never called here); ``isrc_search`` is always ``False`` for stored
    sets so the ``>80`` ISRC short-circuit never fires (replicated for fidelity).

    The loop-variable shadowing in v4 is preserved deliberately: when the near-tie
    window has no view variance (``highest_views in (0, lowest_views)``), v4 returns
    the **last-iterated** entry -- the lowest-scored within the 8-point window -- not
    the top-scored one. The recorder's job is to reproduce v4's actual pick.
    """
    best_results = get_best_matches(scores, 8)

    # If we have only one result, return it.
    if len(best_results) == 1:
        return best_results[0]

    # Initial best result based on the average match.
    best_result = best_results[0]

    # If the best result is a high-scoring ISRC search, return it (never true here).
    if best_result[1] > 80 and best_result[0].isrc_search:
        return best_result

    if len(best_results) > 1:
        views: list[int] = []
        for best_result in best_results:  # NOTE: intentionally shadows best_result
            views.append(best_result[0].views if best_result[0].views else 0)

        highest_views = max(views)
        lowest_views = min(views)

        if highest_views in (0, lowest_views):
            # v4 bug replicated: returns the last-iterated near-tie entry.
            return best_result

        weighted_results: list[Any] = []
        for index, best_result in enumerate(best_results):
            result_views = views[index]
            views_score = ((result_views - lowest_views) / (highest_views - lowest_views)) * 15
            score = min(best_result[1] + views_score, 100)
            weighted_results.append((best_result[0], score))

        return max(weighted_results, key=lambda x: x[1])

    return best_result


def compute_v4_pick(case: Any) -> int | None:
    """Index of the candidate v4's matcher would pick, or ``None`` if none score.

    Runs v4 entirely offline: ``order_results`` scores the reconstructed results,
    then :func:`_select_best` replays ``get_best_result``'s pure tiebreak. The
    chosen result is mapped back to the originating candidate by ``url``.
    """
    candidates = list(case.candidates)
    results = [to_v4_result(c) for c in candidates]
    scores = order_results(results, to_v4_song(case.track))
    if not scores:
        return None

    chosen_result, _score = _select_best(scores)
    chosen_url = chosen_result.url
    for i, c in enumerate(candidates):
        if c.url == chosen_url:
            return i
    return None  # defensive: chosen url always originates from a candidate


def _dict_to_case(d: dict[str, Any]) -> SimpleNamespace:
    """Adapt a raw corpus-JSON case dict into the attribute shape the pickers read.

    Keeps the standalone script free of any ``spotdl_core``/pydantic dependency:
    the recorder needs only attribute access, which both this namespace and a
    pydantic ``CorpusCase`` satisfy.
    """
    track = d["track"]
    album = track.get("album")
    track_ns = SimpleNamespace(
        name=track["name"],
        artists=tuple(track["artists"]),
        duration_ms=track["duration_ms"],
        album=(
            SimpleNamespace(name=album["name"], year=album.get("year"))
            if album is not None
            else None
        ),
        isrc=track.get("isrc"),
        explicit=track.get("explicit"),
        provider_id=track.get("provider_id"),
    )
    candidates = tuple(
        SimpleNamespace(
            provider=c["provider"],
            provider_id=c["provider_id"],
            url=c["url"],
            name=c["name"],
            artists=tuple(c.get("artists", ())),
            duration_ms=c.get("duration_ms"),
            album=c.get("album"),
            isrc=c.get("isrc"),
            verified=c.get("verified", False),
            popularity=c.get("popularity"),
        )
        for c in d["candidates"]
    )
    return SimpleNamespace(candidates=candidates, track=track_ns, source=d.get("source"))


def record_file(path: Path, *, dry_run: bool = False) -> tuple[int, int]:
    """Fill picks for every case in one corpus file (a JSON array of cases).

    Returns ``(cases, changed)``. For each case ``v4_pick_index`` is (re)computed;
    ``v4-recorded`` cases also get ``expected_pick_index`` mirrored from it, while
    ``hand-verified`` cases keep their human-authored ``expected_pick_index``.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: top-level JSON must be an array of cases")

    changed = 0
    for case_dict in data:
        pick = compute_v4_pick(_dict_to_case(case_dict))
        before = (case_dict.get("v4_pick_index"), case_dict.get("expected_pick_index"))
        case_dict["v4_pick_index"] = pick
        if case_dict.get("source") == "v4-recorded":
            case_dict["expected_pick_index"] = pick
        after = (case_dict.get("v4_pick_index"), case_dict.get("expected_pick_index"))
        if before != after:
            changed += 1

    if not dry_run:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(data), changed


def _iter_paths(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matched = sorted(Path().glob(pattern)) if _is_glob(pattern) else [Path(pattern)]
        paths.extend(matched or [Path(pattern)])
    return paths


def _is_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="record_v4.py",
        description=(
            "Offline: replay spotDL v4's matcher pick over stored corpus candidate "
            "sets and write v4_pick_index (and expected_pick_index for v4-recorded "
            "cases) in place. No network."
        ),
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Corpus JSON file paths or globs (each a JSON array of cases).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute picks and report, but do not write files.",
    )
    args = parser.parse_args(argv)

    paths = _iter_paths(args.files)
    if not paths:
        print(f"error: no files matched: {' '.join(args.files)}", file=sys.stderr)
        return 1

    total_cases = 0
    total_changed = 0
    for path in paths:
        cases, changed = record_file(path, dry_run=args.dry_run)
        total_cases += cases
        total_changed += changed
        verb = "would update" if args.dry_run else "updated"
        print(f"{path}: {cases} cases, {verb} {changed}")
    print(f"total: {total_cases} cases across {len(paths)} file(s), {total_changed} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
