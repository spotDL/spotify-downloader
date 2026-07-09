"""Emit the committed v4 accuracy baseline (`baseline.json`) from the corpus JSON.

Deterministic and reproducible: it reads the committed corpus files, counts how
often v4's recorded pick (``v4_pick_index``) equals the ground-truth
(``expected_pick_index``) across *every* case, and writes the baseline the CI
accuracy gate (Task 10) compares v5 against. Regenerate only when the corpus
changes::

    uv run python -m scripts.corpus.make_baseline

By default it reads ``recorded.json`` + ``handcrafted.json`` from the corpus dir
next to this repo's ``packages/core/tests/matching/corpus/`` and writes
``baseline.json`` there. Pass ``--check`` to verify the committed baseline is up
to date without rewriting it (used by CI / review); exits non-zero on drift.

This is workspace tooling under ``scripts/`` — a dev consumer of the corpus
schema, never imported by any published package.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.corpus.schema import CorpusCase

CORPUS_DIR = Path("packages/core/tests/matching/corpus")
GENERATED_FROM = ("recorded.json", "handcrafted.json")
NOTE = (
    "v4 accuracy vs expected_pick_index across the whole corpus; "
    "regenerate only when corpus changes"
)


def load_cases(corpus_dir: Path) -> list[CorpusCase]:
    """Load every ``generated_from`` file as :class:`CorpusCase`, in listed order."""
    cases: list[CorpusCase] = []
    for name in GENERATED_FROM:
        path = corpus_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path}: top-level JSON must be an array of cases")
        cases.extend(CorpusCase.model_validate(item) for item in data)
    return cases


def compute_baseline(cases: Sequence[CorpusCase]) -> dict[str, object]:
    """Compute the baseline dict: total, v4_correct, v4_accuracy, provenance."""
    total = len(cases)
    v4_correct = sum(1 for c in cases if c.v4_pick_index == c.expected_pick_index)
    v4_accuracy = (v4_correct / total) if total else 0.0
    return {
        "total": total,
        "v4_correct": v4_correct,
        "v4_accuracy": v4_accuracy,
        "generated_from": list(GENERATED_FROM),
        "note": NOTE,
    }


def render(baseline: dict[str, object]) -> str:
    """Serialize the baseline as pretty, newline-terminated JSON (stable on disk)."""
    return json.dumps(baseline, indent=2, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="make_baseline.py",
        description="Generate (or --check) the committed v4 accuracy baseline.json.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=CORPUS_DIR,
        help=f"Directory holding the corpus JSON files (default: {CORPUS_DIR}).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify baseline.json matches the corpus without writing; exit 1 on drift.",
    )
    args = parser.parse_args(argv)

    corpus_dir: Path = args.corpus_dir
    baseline = compute_baseline(load_cases(corpus_dir))
    rendered = render(baseline)
    out = corpus_dir / "baseline.json"

    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != rendered:
            print(
                f"error: {out} is out of date; run `uv run python -m scripts.corpus.make_baseline`",
                file=sys.stderr,
            )
            return 1
        print(f"{out}: up to date ({baseline['v4_correct']}/{baseline['total']} v4-correct)")
        return 0

    out.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {out}: total={baseline['total']} v4_correct={baseline['v4_correct']} "
        f"v4_accuracy={baseline['v4_accuracy']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
