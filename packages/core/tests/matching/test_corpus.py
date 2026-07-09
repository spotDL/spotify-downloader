"""Golden-corpus CI accuracy gate (spec §5.3 / §11 release blocker).

This is the release gate: **v5 matcher accuracy on the committed golden corpus
must be >= the committed v4 baseline** (``baseline.json``). ``match()`` is a pure
function and the corpus + baseline are committed, so the gate is fully
deterministic and offline — no network, no v4 reference tree.

The test imports :mod:`scripts.corpus.schema` for the on-disk models and the one
conversion point into ``spotdl_core.model`` (``to_track`` / ``to_candidates``).
``scripts`` is dev tooling, but this is core's *test* suite (not core's runtime),
and pytest runs from the repo root (``pythonpath = ["."]``), so it imports
cleanly without a sys.path shim.

On failure the assertion message lists every case v5 got wrong — one readable
line per case — with true regressions (v4 was right, v5 is wrong) sorted first.
``test_print_corpus_stats`` is non-gating and prints the per-source accuracy
report so the spec §11 numbers are visible in CI logs (``pytest -s``) even when
the gate is green.
"""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from spotdl_core.matching.api import match
from spotdl_core.matching.scoring import MATCHER_V5_DEFAULT
from spotdl_core.model import AudioCandidate

from scripts.corpus.schema import (
    NON_CORPUS_FILENAMES,
    CorpusCase,
    to_candidates,
    to_track,
)

CORPUS_DIR = Path(__file__).parent / "corpus"


# --------------------------------------------------------------------------- #
# Corpus + baseline loading (committed, deterministic)
# --------------------------------------------------------------------------- #
def discover_corpus_files() -> list[Path]:
    """Every ``corpus/*.json`` case file, skipping derived-metadata siblings."""
    return [
        Path(p)
        for p in sorted(glob.glob(str(CORPUS_DIR / "*.json")))
        if Path(p).name not in NON_CORPUS_FILENAMES
    ]


def load_corpus() -> list[CorpusCase]:
    """Load and validate every corpus case across all case files."""
    cases: list[CorpusCase] = []
    for path in discover_corpus_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path}: top-level JSON must be an array of cases")
        cases.extend(CorpusCase.model_validate(item) for item in data)
    return cases


def load_baseline() -> dict[str, object]:
    """Load the committed v4 accuracy baseline."""
    return json.loads((CORPUS_DIR / "baseline.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Per-case evaluation
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CaseResult:
    """Outcome of running the v5 matcher on one corpus case."""

    case_id: str
    source: str
    description: str
    expected_index: int | None
    v5_index: int | None
    v4_index: int | None
    expected_url: str
    v5_url: str
    v4_url: str

    @property
    def correct(self) -> bool:
        return self.v5_index == self.expected_index

    @property
    def v4_correct(self) -> bool:
        return self.v4_index == self.expected_index

    @property
    def is_regression(self) -> bool:
        """v4 picked correctly but v5 did not — a genuine regression vs v4."""
        return self.v4_correct and not self.correct

    def report_line(self) -> str:
        return (
            f"{self.case_id} | expected={self.expected_url} | v5={self.v5_url} | "
            f"v4={self.v4_url} | {self.source} | {self.description}"
        )


def _pick_index(candidates: list[AudioCandidate], picked: AudioCandidate | None) -> int | None:
    """Index of ``picked`` in ``candidates`` by ``(provider, provider_id)``."""
    if picked is None:
        return None
    key = (picked.provider, picked.provider_id)
    for i, cand in enumerate(candidates):
        if (cand.provider, cand.provider_id) == key:
            return i
    return None


def _url_at(case: CorpusCase, index: int | None) -> str:
    """The candidate URL at ``index`` for the report, or ``<none>`` for a no-pick."""
    if index is None:
        return "<none>"
    return case.candidates[index].url


def evaluate_case(case: CorpusCase) -> CaseResult:
    """Run the v5 matcher on one case and record its pick vs the ground truth."""
    track = to_track(case.track)
    candidates = to_candidates(case.candidates)
    matches = match(track, candidates, MATCHER_V5_DEFAULT)
    v5_index = _pick_index(candidates, matches[0].candidate if matches else None)
    return CaseResult(
        case_id=case.case_id,
        source=case.source,
        description=case.description,
        expected_index=case.expected_pick_index,
        v5_index=v5_index,
        v4_index=case.v4_pick_index,
        expected_url=_url_at(case, case.expected_pick_index),
        v5_url=_url_at(case, v5_index),
        v4_url=_url_at(case, case.v4_pick_index),
    )


@lru_cache(maxsize=1)
def evaluate_corpus() -> tuple[CaseResult, ...]:
    """Evaluate every corpus case once (cached; ``match()`` is pure)."""
    return tuple(evaluate_case(case) for case in load_corpus())


def build_regression_report(results: tuple[CaseResult, ...]) -> str:
    """Readable per-case report of every v5-wrong case, regressions first."""
    wrong = [r for r in results if not r.correct]
    # True regressions (v4 right, v5 wrong) first, then the rest; stable by case_id.
    wrong.sort(key=lambda r: (not r.is_regression, r.case_id))
    lines = [r.report_line() for r in wrong]
    n_regress = sum(1 for r in wrong if r.is_regression)
    header = (
        f"{len(wrong)} case(s) mispicked by v5 "
        f"({n_regress} true regression(s) vs v4, listed first):"
    )
    return "\n".join([header, *lines])


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #
def test_v5_accuracy_meets_or_beats_v4_baseline() -> None:
    """RELEASE GATE: v5 corpus accuracy must be >= the committed v4 baseline."""
    results = evaluate_corpus()
    baseline = load_baseline()
    total = len(results)
    assert total > 0, "corpus is empty — no cases discovered"

    correct = sum(1 for r in results if r.correct)
    v5_accuracy = correct / total
    v4_accuracy = float(baseline["v4_accuracy"])

    report = build_regression_report(results)
    assert v5_accuracy >= v4_accuracy, (
        f"v5 accuracy {v5_accuracy:.4f} ({correct}/{total}) is below the v4 "
        f"baseline {v4_accuracy:.4f}.\n{report}"
    )


# --------------------------------------------------------------------------- #
# Non-gating visibility: per-matcher-version accuracy report (spec §11)
# --------------------------------------------------------------------------- #
def test_print_corpus_stats() -> None:
    """Print overall + per-source accuracy so CI logs (``-s``) show the report."""
    results = evaluate_corpus()
    baseline = load_baseline()
    total = len(results)
    correct = sum(1 for r in results if r.correct)
    v5_accuracy = correct / total if total else 0.0
    v4_accuracy = float(baseline["v4_accuracy"])

    by_source: dict[str, tuple[int, int]] = {}
    for r in results:
        c, n = by_source.get(r.source, (0, 0))
        by_source[r.source] = (c + (1 if r.correct else 0), n + 1)

    lines = [
        "",
        "=== golden-corpus accuracy (matcher_version=v5.0) ===",
        f"v5_accuracy: {v5_accuracy:.4f} ({correct}/{total})",
        f"v4_baseline: {v4_accuracy:.4f} ({baseline.get('v4_correct')}/{baseline.get('total')})",
        f"delta:       {v5_accuracy - v4_accuracy:+.4f}",
        "by source:",
    ]
    for source in sorted(by_source):
        c, n = by_source[source]
        acc = c / n if n else 0.0
        lines.append(f"  {source:<14} {acc:.4f} ({c}/{n})")

    n_wrong = sum(1 for r in results if not r.correct)
    n_regress = sum(1 for r in results if r.is_regression)
    lines.append(f"mispicked: {n_wrong} ({n_regress} true regression(s) vs v4)")
    if n_wrong:
        lines.append(build_regression_report(results))
    print("\n".join(lines))

    # Non-gating: this test only reports. The gate lives in the test above.
    assert total > 0
