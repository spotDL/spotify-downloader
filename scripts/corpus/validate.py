"""CLI validator for golden-corpus files.

Usage::

    python -m scripts.corpus.validate <glob> [<glob> ...]

Loads each matched file as a JSON array of :class:`CorpusCase`, asserts
``case_id`` is unique across *all* files, asserts every pick index is in range
(enforced by the model on load), prints a one-line summary, and exits non-zero
on any error. Reused by CI (Task 10) as a cheap structural pre-check before the
(more expensive) accuracy gate runs.

Derived-metadata siblings that share the corpus dir but are not arrays of cases
(``schema.NON_CORPUS_FILENAMES``, e.g. ``baseline.json``) are skipped during
glob expansion, so ``corpus/*.json`` validates cleanly (exit 0) without naming
each case file explicitly.
"""

import glob as globmod
import json
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from scripts.corpus.schema import NON_CORPUS_FILENAMES, CorpusCase


@dataclass(frozen=True)
class Summary:
    total: int
    hand_verified: int
    v4_recorded: int

    def format(self) -> str:
        return (
            f"{self.total} cases, "
            f"{self.hand_verified} hand-verified, "
            f"{self.v4_recorded} v4-recorded"
        )


def load_cases(path: Path) -> list[CorpusCase]:
    """Load and validate one corpus file as a list of :class:`CorpusCase`.

    Raises ``ValueError`` if the top-level JSON is not an array, and
    ``pydantic.ValidationError`` if any case is malformed.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: top-level JSON must be an array of cases")
    return [CorpusCase.model_validate(item) for item in data]


def duplicate_case_ids(cases: Iterable[CorpusCase]) -> list[str]:
    """Return the sorted list of ``case_id`` values that appear more than once."""
    counts = Counter(c.case_id for c in cases)
    return sorted(cid for cid, n in counts.items() if n > 1)


def summarize(cases: Sequence[CorpusCase]) -> Summary:
    hand = sum(1 for c in cases if c.source == "hand-verified")
    v4 = sum(1 for c in cases if c.source == "v4-recorded")
    return Summary(total=len(cases), hand_verified=hand, v4_recorded=v4)


def validate_paths(paths: Iterable[Path]) -> tuple[list[CorpusCase], list[str]]:
    """Load every path and collect structural errors.

    Returns ``(cases, errors)``. ``cases`` holds every case that loaded cleanly;
    ``errors`` is a list of human-readable messages (empty == valid).
    """
    cases: list[CorpusCase] = []
    errors: list[str] = []
    for path in paths:
        try:
            cases.extend(load_cases(path))
        except (OSError, ValueError, ValidationError) as exc:
            errors.append(f"{path}: {exc}")
    for dup in duplicate_case_ids(cases):
        errors.append(f"duplicate case_id across corpus: {dup!r}")
    return cases, errors


def _expand(patterns: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matched = sorted(globmod.glob(pattern, recursive=True))
        if not matched and Path(pattern).exists():
            matched = [pattern]
        for p in matched:
            path = Path(p)
            # Skip derived-metadata siblings (e.g. baseline.json) that share the
            # corpus dir but are not JSON arrays of cases, so the plain
            # ``corpus/*.json`` glob keeps validating cleanly (exit 0).
            if path.name in NON_CORPUS_FILENAMES:
                continue
            paths.append(path)
    return paths


def run(patterns: Sequence[str]) -> int:
    """Validate the files matched by ``patterns``; return a process exit code."""
    paths = _expand(patterns)
    if not paths:
        print(f"error: no files matched: {' '.join(patterns)}", file=sys.stderr)
        return 1
    cases, errors = validate_paths(paths)
    for err in errors:
        print(f"error: {err}", file=sys.stderr)
    print(summarize(cases).format())
    return 1 if errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m scripts.corpus.validate <glob> [<glob> ...]", file=sys.stderr)
        return 2
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
