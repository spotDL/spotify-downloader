# spotDL v5 `core.matching` + Golden Corpus Gate Implementation Plan (Plan 3 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `packages/core/src/spotdl_core/matching/` — a provider-agnostic track→audio-candidate matcher that meets or beats spotDL v4 — plus the golden-corpus tooling (`scripts/corpus/`) and the CI accuracy gate (`packages/core/tests/matching/test_corpus.py`). The matcher is structured as four pure sub-modules (`text`, `features`, `scoring`, `select`) behind one public entry point (`api.match`). v4's battle-tested arithmetic (slug/ratio helpers, the `order_results` combination, `get_best_result` tiebreak, the ISRC short-circuit) is ported verbatim into feature functions and a **versioned, serializable** `ScoringConfig`; nothing battle-tested is silently lost.

**Architecture:** Implements spec §5.3 (redesigned provider-agnostic matcher, versioned weights + hard gates, golden-corpus CI gate) and the matching slice of §11 (golden corpus as a CI gate with an accuracy report per matcher version). Matching lives entirely in `packages/core`; it has no knowledge of HTTP, DB, search, or network. It consumes `Track + list[AudioCandidate]` (from `core.model`, built in Plan 1) and produces `list[Match]` with `FeatureVector`s attached. It never fetches anything — `popularity` replaces v4's network `get_views` tiebreak, and there is no "search" step (candidate acquisition is a `core.providers` concern from Plan 2).

**Design decision (state this to reviewers):** the v5.0 matcher is a **structural** redesign, not an arithmetic one. The provider-agnostic API, the pure feature functions, the typed hard-gate rejections, and the versioned/serializable config are new. But the *numbers* — thresholds, the `(artist + name)/2` core, the conditional album/duration blends, the exp-decay duration curve, the forbidden-word penalty, the 8-point near-tie window, the popularity tiebreak — are ported verbatim from v4's `order_results` / `get_best_result` and expressed as `MATCHER_V5_DEFAULT`. This maximizes the chance of passing the golden-corpus gate on day one while making every constant explicitly recalibratable (`matcher_version`) per the spec's A/B goal. Future matcher versions change only config or add features; the v5.0 default is deliberately v4-faithful.

**Tech Stack:** Python 3.13, pydantic v2 (frozen models), `rapidfuzz`, `python-slugify[unidecode]`, `pykakasi`. New dev/tooling: PEP-723 inline-script recorder run with `uv run --script`. No new web deps.

## Global Constraints

- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Python `>=3.13`; single uv lockfile at the workspace root; `uv sync --all-packages` after any dependency change.
- New `packages/core` runtime dependencies, floors consistent with v4's `pyproject.toml`:
  - `rapidfuzz>=3.10.1,<4`
  - `python-slugify[unidecode]>=8.0.4,<9`
  - `pykakasi>=2.3.0,<3`
  - dev group gains `types-python-slugify>=8.0.2.20240310,<9` (mypy strict).
- TDD is mandatory: write the failing test(s) first, watch them fail for the right reason, then implement. Use superpowers:test-driven-development.
- No singletons and no module-level mutable global state. `MATCHER_V5_DEFAULT` is a frozen pydantic instance (immutable value, not mutable state); the `functools.lru_cache` on `slugify`/`ratio` is a pure memoization cache (allowed — it is v4-faithful and observably pure).
- Every test directory is a package: create `__init__.py` in each new `tests/**/` directory it introduces.
- `make check` (lint + typecheck + test + web-check) must pass green at the end of **every** task.
- No `core` module may import from `spotdl_server`, `spotdl_cli`, `httpx`, `fastapi`, or any I/O/network library. The import-linter `layers` contract (Plan 1, Task 7) enforces this; matching must not break it.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## Prerequisites (from earlier plans — do not re-do)

- Plan 1 delivered: uv workspace, `packages/core` skeleton, `core.model` (`Track`, `AudioCandidate`, `FeatureVector`, `Match`, `MatchStatus`, `ProviderId`, `AlbumRef`), the `Makefile`, `.importlinter`, and CI (`.github/workflows/ci.yml` with the `python` and `web` jobs).
- The v4 reference tree exists at `~/Projects/xnetcat/spotdl-v4-reference/` (Plan 1, Task 1). This plan reads it as the source of truth for ported semantics and drives the corpus recorder from it. **The corpus recorder is the only tool that imports v4 code; nothing in `packages/core` ever does.**

---

## Task graph

| Task | Title | Depends on |
|---|---|---|
| 1 | Dependencies + package skeletons | — |
| 2 | Contract change: amend `FeatureVector` (+ matching-local types) | 1 |
| 3 | `core.matching.text` — normalization & fuzzy helpers | 1 |
| 4 | `core.matching.features` — feature extraction | 2, 3 |
| 5 | `core.matching.scoring` — versioned config, gates, `score()` | 2, 4 |
| 6 | `core.matching.select` + `api.match` | 5 |
| 7 | Corpus format + models + validator (`scripts/corpus/`) | 2 |
| 8 | Corpus recorder (v4 runner, offline) + online harvester | 7 |
| 9 | Seed corpus (~100–300 cases) + committed baseline | 8 |
| 10 | CI gate `test_corpus.py` + workflow wiring | 6, 9 |

---

### Task 1: Add dependencies and create the matching package skeleton

**Files:**
- Modify: `packages/core/pyproject.toml` (add runtime deps)
- Modify: `pyproject.toml` (workspace root dev group — add `types-python-slugify`)
- Create: `packages/core/src/spotdl_core/matching/__init__.py`
- Create: `packages/core/tests/matching/__init__.py`

**Interfaces:**
- Produces: importable empty `spotdl_core.matching` package; `rapidfuzz`, `slugify`, `pykakasi` resolvable in the core venv. No public API yet.

- [ ] **Step 1: Add the runtime dependencies**

In `packages/core/pyproject.toml`, replace the `dependencies` list with:
```toml
dependencies = [
    "pydantic>=2.9,<3",
    "rapidfuzz>=3.10.1,<4",
    "python-slugify[unidecode]>=8.0.4,<9",
    "pykakasi>=2.3.0,<3",
]
```

In the workspace-root `pyproject.toml`, add to the `dev` dependency group:
```toml
    "types-python-slugify>=8.0.2.20240310,<9",
```

- [ ] **Step 2: Create package + test-package markers**

`packages/core/src/spotdl_core/matching/__init__.py`:
```python
"""Provider-agnostic track -> audio-candidate matching."""
```
`packages/core/tests/matching/__init__.py`: empty file.

- [ ] **Step 3: Sync and verify imports resolve**

Run:
```bash
uv sync --all-packages
uv run python -c "import rapidfuzz, slugify, pykakasi, spotdl_core.matching; print('ok')"
```
Expected: `ok`. Then `make check` green (`uv.lock` updated — commit it).

- [ ] **Step 4: Commit**
```bash
git add packages/core/pyproject.toml pyproject.toml uv.lock packages/core/src/spotdl_core/matching packages/core/tests/matching
git commit -m "chore(core): add matching deps (rapidfuzz, slugify, pykakasi) and package skeleton"
```

---

### Task 2: Contract change — amend `FeatureVector` and add matching-local types

**Why this is a contract change (call out to reviewers):** Plan 1's `FeatureVector` has a single `artist_similarity: float` and a bare `forbidden_word_penalty: float`. v4 computes **two** distinct artist signals (main-artist vs other-artists) and a **composed** artist score after three fixup passes, and it treats forbidden words as a **set** whose penalty magnitude is a scoring weight (`-15` each), not a feature. To port faithfully and keep scoring declarative, the feature vector must carry the raw signals; the penalty *magnitude* moves into `ScoringConfig` (Task 5). This task amends the shared `core.model` type. It is additive/renaming within a pre-release package; there are no external consumers yet (Plans 5+ read it but are unwritten).

**Files:**
- Modify: `packages/core/src/spotdl_core/model/entities.py` (redefine `FeatureVector`)
- Modify: `packages/core/tests/model/test_entities.py` (adjust any `FeatureVector` construction if present)

**Interfaces (CONTRACT — verbatim):**

Replace the existing `FeatureVector` class with exactly:
```python
class FeatureVector(_Frozen):
    """Raw per-(track, candidate) signals. All *_similarity in 0..100.

    These are pure signals only. Penalty *magnitudes*, blend thresholds, and
    weights live in matching.scoring.ScoringConfig so they are versioned and
    recalibratable without touching the model.
    """

    title_similarity: float
    main_artist_similarity: float
    other_artist_similarity: float
    artist_similarity: float  # composed (main+other averaged, then v4 fixups)
    album_similarity: float | None  # None when candidate has no album
    duration_delta_s: float  # abs(track - candidate) seconds
    duration_similarity: float  # 0..100, exp-decay transform of duration_delta_s
    isrc_equal: bool
    verified_source: bool
    common_word_overlap: bool  # at least one shared title word (v4 check_common_word)
    forbidden_words: tuple[str, ...]  # one element per matched FORBIDDEN_WORDS *entry* (duplicates kept:
    #   v4's list holds remix/reverb/live twice and penalizes per entry, so a "remix" hit appears twice here)
    explicit_mismatch: bool
    popularity_prior: float  # 0..1, normalized candidate popularity (0.0 when unknown)
```

Notes for the implementer:
- `Match.features: FeatureVector | None` (Plan 1) is unchanged and now carries the amended shape.
- Do **not** add scoring decisions (score, rejections) to `FeatureVector` — those are matching-local (Task 5), not model state.

- [ ] **Step 1: Update the model test** — if `test_entities.py` constructs a `FeatureVector`, update the fields to the new shape; otherwise add a construction smoke test asserting a fully-populated `FeatureVector` is frozen. Run it; watch it fail against the old class.
- [ ] **Step 2: Amend `FeatureVector`** as specified above.
- [ ] **Step 3:** `uv run pytest packages/core/tests/model -v` green; `uv run mypy packages/core/src` clean.
- [ ] **Step 4: Commit**
```bash
git add packages/core/src/spotdl_core/model/entities.py packages/core/tests/model
git commit -m "feat(core)!: amend FeatureVector for provider-agnostic matcher (split artist signals, raw forbidden-word set)"
```

---

### Task 3: `core.matching.text` — normalization & fuzzy helpers (verbatim v4 port)

**Files:**
- Create: `packages/core/src/spotdl_core/matching/text.py`
- Test: `packages/core/tests/matching/test_text.py`

**Interfaces (CONTRACT — exact signatures):**
```python
def slugify(string: str) -> str: ...                     # lru_cache'd, v4-faithful incl. Japanese
def ratio(string1: str, string2: str) -> float: ...      # lru_cache'd fuzz.ratio, 0..100
def sequence_ratio(seq1: tuple[str, ...], seq2: tuple[str, ...]) -> float: ...  # fuzz.ratio on token tuples
def song_title(name: str, artists: tuple[str, ...]) -> str: ...  # v4 create_song_title
def fill_string(strings: tuple[str, ...], main_string: str, string_to_check: str) -> str: ...
def clean_string(words: tuple[str, ...], string: str, *, sort: bool = False, join_str: str = "-") -> str: ...
def sort_tokens(tokens: tuple[str, ...], join_str: str = "-") -> str: ...
def based_sort(strings: list[str], based_on: list[str]) -> tuple[list[str], list[str]]: ...
```

These are pure ports of `spotdl.utils.formatter.{slugify,ratio,create_song_title}` and `spotdl.utils.matching.{fill_string,create_clean_string,sort_string,based_sort}`. Two deviations, both deliberate:
1. **`ratio` accepts only `str`.** v4's `ratio` is sometimes called on *tuples* (in `artists_match_fixup1`). That path is preserved by the separate `sequence_ratio(tuple, tuple)` helper, which calls `fuzz.ratio` on the sequences exactly as `rapidfuzz` does for v4. Splitting keeps the `lru_cache` type-clean under mypy strict.
2. Collection params are `tuple[...]` (hashable, immutable) rather than v4's `List`, so cached call sites stay hashable and match the frozen-model convention. `based_sort` mutates via local `sorted()` and returns new lists (v4 sorted in place; the port must **not** mutate inputs — copy first).

**CONTRACT — verbatim `slugify` behavior (this is the single piece the spec says is kept verbatim, incl. pykakasi Japanese handling):**
```python
import re
from functools import lru_cache

import pykakasi
from rapidfuzz import fuzz
from slugify import slugify as _py_slugify

# Hiragana, katakana, half/full-width forms, CJK unified + extension-A.
JAP_REGEX = re.compile(
    "[　-〿぀-ゟ゠-ヿ＀-ﾟ一-龯㐀-䶿]"
)
# Everything except ASCII letters/digits, hyphen, and ! @ $ becomes a separator.
DISALLOWED_REGEX = re.compile(r"[^-a-zA-Z0-9\!\@\$]+")

_KKS = pykakasi.kakasi()


@lru_cache(maxsize=4096)
def slugify(string: str) -> str:
    # Fast path: no Japanese characters -> plain python-slugify.
    if not JAP_REGEX.search(string):
        return _py_slugify(string, regex_pattern=DISALLOWED_REGEX.pattern)

    # Japanese path: python-slugify mangles kana/kanji, so romanize with
    # pykakasi (Hepburn) first, inserting hyphens between kana-vs-romaji runs,
    # then slugify the romaji.
    normal_slug = _py_slugify(string, regex_pattern=JAP_REGEX.pattern)
    results = _KKS.convert(normal_slug)

    result = ""
    for index, item in enumerate(results):
        result += item["hepburn"]
        if not (
            item["kana"] == item["hepburn"]
            or item == results[-1]
            or results[index + 1]["kana"] == results[index + 1]["hepburn"]
        ):
            result += "-"

    return _py_slugify(result, regex_pattern=DISALLOWED_REGEX.pattern)


@lru_cache(maxsize=8192)
def ratio(string1: str, string2: str) -> float:
    return fuzz.ratio(string1, string2)


def sequence_ratio(seq1: tuple[str, ...], seq2: tuple[str, ...]) -> float:
    return fuzz.ratio(seq1, seq2)
```
> Note: v4's kana loop has a redundant duplicated `item["kana"] == item["hepburn"]` clause; the port collapses it to a single clause (behavior-identical). Keep the `results[index + 1]` look-ahead exactly — it is guarded by the `item == results[-1]` short-circuit.

**CONTRACT — slugify behavior table (each row is a required test case):**

| Input | Output | Rule exercised |
|---|---|---|
| `"Hello World"` | `"hello-world"` | ASCII lower + space→hyphen |
| `"AC/DC"` | `"ac-dc"` | disallowed `/` → separator |
| `"Beyoncé"` | `"beyonce"` | diacritic fold (unidecode) |
| `"Motörhead"` | `"motorhead"` | diacritic fold |
| `"Song (feat. X)"` | `"song-feat-x"` | parens → separators |
| `"Café!@$"` | `"cafe!@$"` | `! @ $` preserved verbatim |
| `"P!nk"` | `"p!nk"` | `!` preserved mid-token |
| `"  spaced  out  "` | `"spaced-out"` | leading/trailing/collapsed whitespace |
| `"AaaA---bbb"` | `"aaaa-bbb"` | collapse repeat separators |
| `"解憶"` (Ai kamano) | non-empty ASCII romaji, no CJK codepoints | Japanese → Hepburn romaji path |
| `"光"` | non-empty ASCII romaji | single-kanji Japanese path |
| `"ポップコーン"` (katakana) | non-empty ASCII romaji | katakana path |
| `""` | `""` | empty string is stable |

> The Japanese rows assert **properties** (result is non-empty, contains no codepoint matching `JAP_REGEX`, is a valid slug), not brittle exact romaji strings — pykakasi romaji is stable but asserting exact strings couples the test to a library version. Add one *golden* exact-string assertion for `"解憶"` captured from the installed pykakasi so drift is visible, marked with a comment that it may need refresh on a pykakasi bump.

**CONTRACT — `ratio` / `sequence_ratio` / `song_title` behavior (required tests):**

| Call | Expected |
|---|---|
| `ratio("abc", "abc")` | `100.0` |
| `ratio("", "")` | `0.0` (rapidfuzz convention for two empty strings) |
| `ratio("hello", "hallo")` | `> 70` and `< 100` |
| `ratio(a, b) == ratio(a, b)` (repeat) | identical (cache is pure) |
| `sequence_ratio(("a","b"), ("a","b"))` | `100.0` |
| `sequence_ratio(("a","b","c"), ("c","b","a"))` | `< 100` (order matters, mirrors v4 fixup1) |
| `song_title("Name", ("A", "B"))` | `"A, B - Name"` |
| `song_title("Name", ("A",))` | `"A - Name"` |
| `song_title("Name", ())` | `"Name"` |

**CONTRACT — `fill_string` / `clean_string` / `sort_tokens` / `based_sort` (port + required tests):**

- `fill_string(strings, main_string, string_to_check)`: for each `s` in `strings`, let `slug = slugify(s).replace("-", "")`; if `slug` is a substring of `string_to_check.replace("-","")` but **not** of the running `main_string` (hyphens stripped), append `"-{slug}"` to `main_string`. Return the augmented string. (v4 `fill_string`, verbatim.) Test: `fill_string(("Feat Artist",), "song-name", "song-name-featartist")` appends `"-featartist"`; a token already present is not re-added.
- `clean_string(words, string, *, sort, join_str)`: `string := slugify(string).replace("-","")`; keep each slugified/dehyphenated `word` **not** already a substring of `string`; join with `join_str` (sorted first if `sort`). (v4 `create_clean_string`.) Test with a word present (dropped) and absent (kept); `sort=True` orders lexicographically.
- `sort_tokens(tokens, join_str)`: sort a copy lexicographically, join. (v4 `sort_string`, non-mutating.)
- `based_sort(strings, based_on)`: reproduce v4 exactly — sort both, build `{value: index}` map over `based_on`, re-sort `strings` by `map.get(x, -1)` reverse, reverse `based_on`, return `(strings, based_on)`. **Must copy inputs** (v4 mutated caller lists — the port must not). Test the docstring example ordering from v4: aligning `["a","b","c"]` against `["c","b","a"]`.

- [ ] **Step 1:** Write `test_text.py` covering every table row above (parametrized). Run; confirm all fail with `ModuleNotFoundError`.
- [ ] **Step 2:** Implement `text.py` per the verbatim contract.
- [ ] **Step 3:** `uv run pytest packages/core/tests/matching/test_text.py -v` green; `uv run mypy packages/core/src` clean (add `# type: ignore[...]` only if `slugify`'s `regex_pattern` kw needs it — prefer `types-python-slugify` resolving it).
- [ ] **Step 4:** `make check` green. Commit:
```bash
git add packages/core/src/spotdl_core/matching/text.py packages/core/tests/matching/test_text.py
git commit -m "feat(core): matching.text — v4-verbatim slugify/ratio/token helpers"
```

---

### Task 4: `core.matching.features` — feature extraction

**Files:**
- Create: `packages/core/src/spotdl_core/matching/features.py`
- Test: `packages/core/tests/matching/test_features.py`

**Interfaces (CONTRACT — exact signatures):**
```python
from spotdl_core.model import AudioCandidate, FeatureVector, Track

FORBIDDEN_WORDS: tuple[str, ...]  # module-level, verbatim from v4

def common_word_overlap(track: Track, candidate: AudioCandidate) -> bool: ...
def title_similarity(track: Track, candidate: AudioCandidate) -> float: ...
def main_artist_similarity(track: Track, candidate: AudioCandidate) -> float: ...
def other_artist_similarity(track: Track, candidate: AudioCandidate) -> float: ...
def artist_similarity(track: Track, candidate: AudioCandidate) -> float: ...  # composed: (main+other avg) then fixup1/2/3
def album_similarity(track: Track, candidate: AudioCandidate) -> float | None: ...
def duration_delta_s(track: Track, candidate: AudioCandidate) -> float: ...
def duration_similarity(track: Track, candidate: AudioCandidate) -> float: ...
def forbidden_words(track: Track, candidate: AudioCandidate) -> tuple[str, ...]: ...
def explicit_mismatch(track: Track, candidate: AudioCandidate) -> bool: ...
def isrc_equal(track: Track, candidate: AudioCandidate) -> bool: ...
def popularity_prior(candidate: AudioCandidate, *, max_popularity: float = 100.0) -> float: ...
def extract_features(track: Track, candidate: AudioCandidate) -> FeatureVector: ...
```

**CONTRACT — `FORBIDDEN_WORDS` (verbatim from v4 — keep it exactly, duplicates and all; the duplicates are load-bearing: v4's `check_forbidden_words` appends one match per list *entry* and `order_results` subtracts 15 per entry, so a `"remix"` hit costs **-30**, `"cover"` -15):**
```python
FORBIDDEN_WORDS: tuple[str, ...] = (
    "bassboosted", "remix", "remastered", "remaster", "reverb", "bassboost",
    "live", "acoustic", "8daudio", "concert", "live", "acapella", "slowed",
    "instrumental", "remix", "cover", "reverb",
)
```

**CONTRACT — one extraction rule per feature (each row is a table-driven test):**

Terminology: `t_name = slugify(track.name)`; `c_name = slugify(candidate.name)`; artists compared as `slugify`'d lists; "candidate artists" = `candidate.artists` (may be empty).

| Feature | Rule (ported from v4) |
|---|---|
| `common_word_overlap` | v4 `check_common_word`: split `slugify(track.name)` on `-`; return `True` iff any non-empty word is a substring of `slugify(candidate.name).replace("-","")`. |
| `title_similarity` | v4 `calc_name_match` **without** the `search_query` branch (dropped — see table below). Build `(m1, m2)` via `create_match_strings` (fill missing artists into each side with `fill_string`, then `based_sort` + rejoin). `name = ratio("-".join(based_sort(c_name.split("-"), t_name.split("-"))[0]), ...[1])`. If `name <= 75`, `name = max(name, ratio(m1, m2))`. Return `name` (0..100). |
| `main_artist_similarity` | v4 `calc_main_artist_match` verbatim: `0.0` if candidate has no artists; if track has >1 artist and candidate has exactly 1, sum `100/len(track.artists)` for each secondary track artist whose sorted tokens are contained in the sorted single candidate-artist; else `ratio(slugify(track.artists[0]), based_sort(track_slugs, cand_slugs)[1][0])`, and if `< 50` and track has multiple artists, take the max over `product(sorted(track_slugs)[:2], based_sort(track_slugs, cand_slugs)[1][:2])`. **Non-mutation caveat:** v4's `based_sort` sorts its arguments *in place*, so by the time v4's `product` fallback runs, its `song_artists` is the lexicographically sorted slug list, and its `sorted_result_artists` (based_sort's second return) is the candidate slug list sorted lexicographically **then reversed**. The v5 port's `based_sort` is non-mutating (Task 3), so the port must feed the fallback these exact lists explicitly: `sorted(track_slugs)` for the track side, `based_sort(...)[1]` for the candidate side — do not accidentally use the original-order lists. |
| `other_artist_similarity` | v4 `calc_artists_match` verbatim: `0.0` if track has 1 artist or candidate has none; `based_sort` both, drop index 0 (main), `zip_longest` the rest, sum `ratio` per pair (missing → `ratio(x, None)` = v4 behavior), divide by `len(remaining track artists)`. |
| `artist_similarity` | **Composed** (this folds v4's `order_results` artist pipeline + all three fixups into one pure function). `score = main_artist_similarity + other_artist_similarity`; `score /= 2 if len(track.artists) > 1 else 1`; then the three fixups with their exact internal gates: **fixup1** — applies only if `not candidate.verified and score <= 50`: `score = max(score, ratio(slugify(track.main_artist), slugify(", ".join(candidate.artists)) if candidate.artists else ""))`; if `score <= 70`: `score = max(score, 100 * (count of track artists whose dehyphenated slug is a substring of dehyphenated c_name) / len(track.artists))`; if still `<= 70`: `score = max(score, sequence_ratio(track_artist_tokens, cand_artist_tokens))` (each side = tuple of all slug tokens of all artists). **fixup2** — applies only if `candidate.verified and score <= 70`: `has_main_artist = (score / (2 if len(track.artists) > 1 else 1)) > 50`; `+5` per artist in `track.artists[int(has_main_artist):]` whose dehyphenated slug is a substring of the dehyphenated second match-string from `create_match_strings`; if `score` still `<= 70`: `score = max(score, ratio(clean_string(track.artists, t_name, sort=True), clean_string(candidate.artists or ("",), c_name, sort=True)))`. **fixup3** — applies only if `score <= 70 and len(candidate.artists) == 1 and len(track.artists) > 1`: `fix = ratio(c_name, slugify(song_title(track.name, (track.main_artist,))))`; if `fix >= 80`: `score = (score + fix) / 2`. Return `min(score, 100)`. Verified input comes from `candidate.verified`. v4's fixup2 fell back to `result.author` when `result.artists` was falsy; v5 candidates have no separate channel-author field, so the fallback is `("",)` (consistent with fixup1's empty-string join for artist-less candidates). |
| `album_similarity` | v4 `calc_album_match`: `None` if `candidate.album` is falsy (v4 returned `0.0`; v5 returns `None` so scoring can distinguish "no album info" from "album mismatch"); else `ratio(slugify(track.album.name if track.album else ""), slugify(candidate.album))`. |
| `duration_delta_s` | `abs(track.duration_ms - (candidate.duration_ms or 0)) / 1000.0`. (When candidate duration is unknown, delta is the full track length → drives `duration_similarity` toward 0, matching v4 where missing duration scored poorly.) |
| `duration_similarity` | v4 `calc_time_match`, exact formula: `exp(-0.1 * duration_delta_s) * 100`. So Δ0s→100, Δ10s→≈36.8, Δ30s→≈4.98, Δ60s→≈0.25. |
| `forbidden_words` | v4 `check_forbidden_words`: `song = slugify(track.name).replace("-","")`, `cand = slugify(candidate.name).replace("-","")`; iterate `FORBIDDEN_WORDS` **in order, duplicates included**, appending each `w` where `w in cand and w not in song`. **No dedup** — `remix`/`reverb`/`live` appear twice in the list, so a hit yields two entries and (via scoring) a double penalty, exactly as v4. |
| `explicit_mismatch` | v4: `track.explicit is not None and candidate` explicit info is not None and they differ. `AudioCandidate` has no `explicit` field in the Plan-1 model → **treat candidate explicit as unknown** ⇒ `explicit_mismatch` is always `False` unless a candidate explicit signal exists. See the note below; do **not** invent a field in this task. |
| `isrc_equal` | `track.isrc is not None and candidate.isrc is not None and normalized equal`, where normalize = `isrc.upper().replace("-", "")` (v4 ISRC regex allows optional hyphens). |
| `popularity_prior` | `0.0` if `candidate.popularity is None`; else `min(max(candidate.popularity / max_popularity, 0.0), 1.0)`. (Spotify-style 0..100 popularity → 0..1; YT view counts are normalized in `select`, not here.) |

`extract_features` assembles the `FeatureVector` by calling every function above once, with `verified_source=candidate.verified`.

**Note on `explicit_mismatch` (flag to reviewers, resolve in scoring plan, not here):** the Plan-1 `AudioCandidate` has no `explicit` field, so this feature is inert (`False`) for now — the v4 explicit-mismatch penalty only ever fired when both sides had explicit metadata, which few audio providers expose. Implement the function to read a candidate explicit signal *if present* (via `getattr(candidate, "explicit", None)`) so it activates automatically if Plan 2 adds the field, but do **not** amend the model here. This is a documented, intentional near-parity gap (see dropped/deferred table).

**Testing:** table-driven, one parametrized test per feature using small hand-built `Track`/`AudioCandidate` fixtures. Mandatory scenario cases (traps that must behave like v4):
- Exact match: identical name/artist/duration → `title≈100`, `artist≈100`, `duration_similarity≈100`, `forbidden_words=()`.
- Remix trap: candidate name `"Song (Remix)"`, track `"Song"` → `forbidden_words == ("remix", "remix")` (matched per list entry, no dedup); candidate `"Song (Cover)"` → `("cover",)` (single-entry word); track already `"Song Remix"` → `forbidden_words=()` (word present in both).
- Multi-artist, candidate collapses all into one artist string → `main_artist_similarity > 0` via the contains path.
- `feat.` notation: track `"Song"` artists `("A","B")`, candidate name `"A, B - Song"` single artist `("A",)` → `artist_similarity` recovered by fixup path (`> 70`).
- CJK title: Japanese track/candidate names slugify to matching romaji → `title_similarity` high; `common_word_overlap` True.
- Duration outlier: Δ45s → `duration_similarity < 5`.
- ISRC: `"USUM71234567"` vs `"us-um7-12-34567"` → `isrc_equal` True; one side `None` → False.
- Popularity: `popularity=None`→0.0; `popularity=100`→1.0; `popularity=50`→0.5.

- [ ] **Step 1:** Write `test_features.py` (all scenarios). Run; confirm failing.
- [ ] **Step 2:** Implement `features.py`, porting the referenced v4 functions. Cross-check each against `~/Projects/xnetcat/spotdl-v4-reference/spotdl/utils/matching.py` line-by-line.
- [ ] **Step 3:** `uv run pytest packages/core/tests/matching/test_features.py -v` green; `uv run mypy packages/core/src` clean.
- [ ] **Step 4:** `make check` green. Commit:
```bash
git add packages/core/src/spotdl_core/matching/features.py packages/core/tests/matching/test_features.py
git commit -m "feat(core): matching.features — v4 signal inventory as pure feature functions"
```

---

### Task 5: `core.matching.scoring` — versioned config, hard gates, `score()`

**Files:**
- Create: `packages/core/src/spotdl_core/matching/scoring.py`
- Test: `packages/core/tests/matching/test_scoring.py`

**Interfaces (CONTRACT — exact public API):**
```python
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from spotdl_core.model import FeatureVector


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class GateReason(StrEnum):
    NO_COMMON_WORD = "no_common_word"
    TITLE_TOO_LOW = "title_too_low"
    ARTIST_TOO_LOW = "artist_too_low"
    DURATION_TOO_LOW = "duration_too_low"
    DURATION_AND_AVERAGE_TOO_LOW = "duration_and_average_too_low"


class GateRejection(_Frozen):
    gate: GateReason
    detail: str  # human-readable, e.g. "title_similarity 42.0 <= 60.0"


class HardGates(_Frozen):
    require_common_word: bool = True
    min_title_similarity: float = 60.0          # v4: name_match <= 60 -> skip
    min_artist_similarity: float = 70.0         # v4: artists_match < 70 -> skip
    min_duration_similarity: float = 25.0       # v4: time_match < 25 -> skip
    low_duration_similarity: float = 50.0       # v4: time_match < 50 ...
    low_average_threshold: float = 75.0         # v4: ... and average < 75 -> skip


class SelectionConfig(_Frozen):
    isrc_short_circuit_min_score: float = 80.0  # v4: ISRC best > 80 -> return
    near_tie_window: float = 8.0                # v4: get_best_matches threshold
    popularity_tiebreak_weight: float = 15.0    # v4: views_score max +15


class ScoringConfig(_Frozen):
    matcher_version: str = "v5.0"
    # combination weights (v4 core is a plain (artist+name)/2 average)
    weight_title: float = 0.5
    weight_artist: float = 0.5
    # forbidden-word penalty magnitude, applied to title before combination
    forbidden_word_penalty: float = 15.0        # v4: name_match -= 15 per word
    # conditional blends (all v4-faithful)
    album_blend_when_verified: bool = True
    album_blend_ceiling: float = 80.0           # v4: verified & album<=80 -> blend
    duration_blend_ceiling: float = 85.0        # v4: average<=85 -> blend time
    explicit_mismatch_penalty: float = 5.0      # v4: -5 on explicit mismatch
    gates: HardGates = HardGates()
    selection: SelectionConfig = SelectionConfig()


class ScoreResult(_Frozen):
    score: float          # 0..100
    rejected: bool
    rejection: GateRejection | None = None  # first gate that fired (v4 short-circuits)


MATCHER_V5_DEFAULT: ScoringConfig = ScoringConfig()


def score(features: FeatureVector, config: ScoringConfig = MATCHER_V5_DEFAULT) -> ScoreResult: ...
```

**Serialization requirement:** `ScoringConfig` must round-trip `config.model_dump_json()` / `ScoringConfig.model_validate_json(...)` losslessly (pydantic gives this free; add a test). This is what lets the server persist `matcher_version` and A/B configs (spec §6.1 `matches.matcher_version`, §9 A/B).

**CONTRACT — the `score()` algorithm (verbatim port of v4 `order_results`'s per-result combination, thresholds read from config, gates short-circuit like v4):**
```python
def score(features, config=MATCHER_V5_DEFAULT):
    g = config.gates

    # Gate 1: common word (v4 check_common_word skip)
    if g.require_common_word and not features.common_word_overlap:
        return ScoreResult(0.0, True, GateRejection(GateReason.NO_COMMON_WORD, "no shared title word"))

    # Title with forbidden-word penalty (v4: name_match -= 15 per word)
    title = features.title_similarity - config.forbidden_word_penalty * len(features.forbidden_words)
    artist = features.artist_similarity

    # Gate 2: title floor (v4: name_match <= 60)  -- uses the penalized value
    if title <= g.min_title_similarity:
        return ScoreResult(0.0, True, GateRejection(GateReason.TITLE_TOO_LOW, f"title {title} <= {g.min_title_similarity}"))

    # Gate 3: artist floor (v4: artists_match < 70)
    if artist < g.min_artist_similarity:
        return ScoreResult(0.0, True, GateRejection(GateReason.ARTIST_TOO_LOW, f"artist {artist} < {g.min_artist_similarity}"))

    # Core combination: (artist + title)/2 == v4 with weight_title=weight_artist=0.5
    average = artist * config.weight_artist + title * config.weight_title

    # Album blend for verified results (v4: verified & album & album<=80)
    if (config.album_blend_when_verified and features.verified_source
            and features.album_similarity is not None
            and features.album_similarity <= config.album_blend_ceiling):
        average = (average + features.album_similarity) / 2

    # Gate 4: duration floor (v4: time_match < 25)
    if features.duration_similarity < g.min_duration_similarity:
        return ScoreResult(0.0, True, GateRejection(GateReason.DURATION_TOO_LOW, ...))

    # Gate 5: weak duration + weak average (v4: time<50 and average<75)
    if features.duration_similarity < g.low_duration_similarity and average < g.low_average_threshold:
        return ScoreResult(0.0, True, GateRejection(GateReason.DURATION_AND_AVERAGE_TOO_LOW, ...))

    # Duration blend when not already confident (v4: average<=85 -> blend time; then explicit)
    if average <= config.duration_blend_ceiling:
        average = (average + features.duration_similarity) / 2
        if features.explicit_mismatch:
            average -= config.explicit_mismatch_penalty

    return ScoreResult(score=min(average, 100.0), rejected=False, rejection=None)
```
> `weight_title + weight_artist` must sum to `1.0` for the default to equal v4's `(artist+name)/2`; a validator on `ScoringConfig` should assert this (pydantic `model_validator`) so a malformed config fails loudly rather than silently rescaling.

**CONTRACT — mapping to v4 (the dropped-guards note, so nothing is silent):** v4's combination had extra guards keyed on `result.isrc_search` and `result.source == "slider.kz"` and a dead `time_match < 0` branch. These are dropped here (see the plan-wide dropped table) because v5 has no search-source concept and no slider.kz provider; the ISRC preference moves to `select` (Task 6). This is intentional and lossless for v1 providers.

**Testing (table-driven):**
- Perfect features → `rejected False`, `score ≈ 100`.
- Each gate fires with the right `GateReason` at its boundary (e.g. `title_similarity=60.0` → `TITLE_TOO_LOW`; `=60.01` passes gate 2).
- Forbidden word pushes a `61` title below the `60` gate: single-entry word (`("cover",)` → `61 - 15 = 46`) → `TITLE_TOO_LOW`; and the double-entry case `("remix", "remix")` costs `-30` (`95 - 30 = 65` passes; `89 - 30 = 59` gates) — the penalty is per **entry**, matching v4's duplicated list.
- Verified + `album_similarity=50` blends the average downward vs unverified identical features.
- Duration blend: `average=70`, `duration_similarity=40` → `(70+40)/2=55`.
- Explicit mismatch subtracts 5 only inside the blend branch.
- `model_dump_json()` round-trips; a config with `matcher_version="v5.1-experiment"` and altered weights scores differently and re-loads identically.
- Invalid config (`weight_title=0.7, weight_artist=0.7`) raises `ValidationError`.

- [ ] **Step 1:** Write `test_scoring.py`. Run; confirm failing.
- [ ] **Step 2:** Implement `scoring.py`.
- [ ] **Step 3:** `uv run pytest packages/core/tests/matching/test_scoring.py -v` green; mypy clean.
- [ ] **Step 4:** `make check` green. Commit:
```bash
git add packages/core/src/spotdl_core/matching/scoring.py packages/core/tests/matching/test_scoring.py
git commit -m "feat(core): matching.scoring — versioned ScoringConfig, typed gates, v4-faithful score()"
```

---

### Task 6: `core.matching.select` + `api.match`

**Files:**
- Create: `packages/core/src/spotdl_core/matching/select.py`
- Create: `packages/core/src/spotdl_core/matching/api.py`
- Modify: `packages/core/src/spotdl_core/matching/__init__.py` (export public surface)
- Test: `packages/core/tests/matching/test_select.py`, `packages/core/tests/matching/test_api.py`

**Interfaces (CONTRACT — exact public API):**
```python
# select.py
from spotdl_core.matching.scoring import ScoreResult, ScoringConfig
from spotdl_core.model import AudioCandidate, FeatureVector, Match


class CandidateScore(_Frozen):
    candidate: AudioCandidate
    features: FeatureVector
    result: ScoreResult


def select(scored: tuple[CandidateScore, ...], config: ScoringConfig = MATCHER_V5_DEFAULT) -> list[Match]: ...


# api.py
def score_candidates(
    track: Track, candidates: tuple[AudioCandidate, ...] | list[AudioCandidate],
    config: ScoringConfig = MATCHER_V5_DEFAULT,
) -> list[CandidateScore]: ...   # ALL candidates incl. rejected, for server-side explainability

def match(
    track: Track, candidates: tuple[AudioCandidate, ...] | list[AudioCandidate],
    config: ScoringConfig = MATCHER_V5_DEFAULT,
) -> list[Match]: ...            # ranked, viable-only; the ONE public entry
```

`match()` is the single public entry the spec calls for. `score_candidates()` is the explainability hook (the server can inspect every candidate's `ScoreResult.rejection`); `match()` = `select(tuple(score_candidates(...)), config)`.

`matching/__init__.py` re-exports: `match`, `score_candidates`, `CandidateScore`, `ScoringConfig`, `MATCHER_V5_DEFAULT`, `ScoreResult`, `GateReason`, `GateRejection`, `extract_features`.

**CONTRACT — selection rules (verbatim port of `get_best_matches` + `get_best_result` + the `search()` ISRC short-circuit, network parts removed):**

Each returned `Match` = `Match(candidate=cs.candidate, score=cs.result.score, matcher_version=config.matcher_version, status=MatchStatus.AUTO, features=cs.features)`. `score` stored is the **base** score; popularity tiebreak affects **ordering only**, not the persisted score (documented deviation — v4 returned the views-adjusted score for the winner only; storing base scores keeps the field meaning consistent across the returned list).

```
def select(scored, config=MATCHER_V5_DEFAULT):
    sel = config.selection
    viable = [cs for cs in scored if not cs.result.rejected]

    # ISRC rule A — UNCONDITIONAL (v4 base.search: exactly one ISRC result and it
    # is verified -> return it with NO score check, before any scoring/gating).
    # Evaluated over ALL scored candidates (incl. gate-rejected), because v4
    # applied it before order_results ever ran.
    isrc_all = [cs for cs in scored if cs.features.isrc_equal]
    if len(isrc_all) == 1 and isrc_all[0].candidate.verified:
        winner = isrc_all[0]
        rest = sorted((cs for cs in viable if cs is not winner),
                      key=lambda cs: cs.result.score, reverse=True)
        return [_to_match(winner)] + [_to_match(cs) for cs in rest]

    if not viable:
        return []

    # ISRC rule B — score-checked short-circuit (v4 base.search: best ISRC
    # result with score > 80 -> return it even if a non-ISRC result scores higher).
    isrc_hits = [cs for cs in viable
                 if cs.features.isrc_equal and cs.result.score >= sel.isrc_short_circuit_min_score]
    if isrc_hits:
        winner = max(isrc_hits, key=lambda cs: cs.result.score)
        rest = sorted((cs for cs in viable if cs is not winner),
                      key=lambda cs: cs.result.score, reverse=True)
        return [_to_match(winner)] + [_to_match(cs) for cs in rest]

    ordered = sorted(viable, key=lambda cs: cs.result.score, reverse=True)
    best = ordered[0].result.score

    # Near-tie window (v4 get_best_matches: within 8 points of the best).
    window = [cs for cs in ordered if best - cs.result.score <= sel.near_tie_window]
    tail = ordered[len(window):]

    if len(window) > 1:
        # Popularity tiebreak (v4 get_best_result views normalization, popularity in place of views).
        pops = [cs.features.popularity_prior for cs in window]
        hi, lo = max(pops), min(pops)
        if hi not in (0.0, lo):
            def adjusted(cs):
                norm = (cs.features.popularity_prior - lo) / (hi - lo)
                return min(cs.result.score + norm * sel.popularity_tiebreak_weight, 100.0)
            window = sorted(window, key=adjusted, reverse=True)

    return [_to_match(cs) for cs in (window + tail)]
```

Notes:
- v4 `get_best_result` returned the single best; v5 `match` returns the **full ranked list** (spec §6.2 `GET /tracks/{id}/matches` returns a list with scores). The head of the list is the equivalent of v4's chosen URL.
- Rule A is v4's unconditional `len(isrc_results) == 1 and isrc_results[0].verified` early return — deliberately **stronger** than rule B (no score threshold, bypasses gates, because v4 returned before scoring even ran). If the rule-A winner was gate-rejected, its `Match.score` is the computed `0.0` — the pin is expressed by ordering, the score field stays honest. Rule B is v4's separate `best_isrc[1] > 80.0` path.
- v4's `get_best_result` early-return `if best > 80 and isrc_search` is folded into rule B above.
- Popularity tiebreak only engages when popularity values actually differ (v4 guarded `highest_views in (0, lowest_views)`), so ties without popularity data preserve score order. **Intentional bug fix:** in that no-variance branch, v4's `get_best_result` reuses `best_result` as the views-loop variable, so it returned the *last-iterated* near-tie entry rather than the top-scored one; v5 preserves score order instead. (The corpus **recorder** must still replicate v4's buggy behavior — see Task 8.)

**Testing:**
- Empty candidates → `[]`; all-rejected → `[]`.
- Single viable → one `Match`, base score preserved.
- ISRC rule A (unconditional): exactly one ISRC-equal candidate, `verified=True`, that even **fails the duration gate** (rejected, score 0) → it is still returned first (v4 returned it before scoring ran); same candidate with `verified=False` → rule A does not fire.
- ISRC rule A does not fire when **two** candidates are ISRC-equal (falls through to rule B / ranking).
- ISRC rule B (score-checked): among two ISRC-equal viable candidates, one scoring 82 beats a non-ISRC candidate scoring 95 (short-circuit wins); two ISRC-equal candidates scoring 79 and 75 do **not** short-circuit (below `isrc_short_circuit_min_score`, and rule A needs exactly one).
- Near-tie + popularity: two candidates at 90 and 88 (within 8) with popularities 0.2 and 0.9 → the higher-popularity one ranks first; the same pair 90 and 78 (outside 8) → score order preserved, popularity ignored.
- `match()` end-to-end on a small hand-built `(track, [good, remix-trap, wrong-artist])` returns the good candidate first and drops the gated ones.
- `score_candidates()` includes rejected candidates with populated `result.rejection`.

- [ ] **Step 1:** Write `test_select.py` + `test_api.py`. Run; confirm failing.
- [ ] **Step 2:** Implement `select.py`, `api.py`, update `__init__.py`.
- [ ] **Step 3:** `uv run pytest packages/core/tests/matching -v` green; mypy clean; `uv run lint-imports` still KEPT (no forbidden imports introduced).
- [ ] **Step 4:** `make check` green. Commit:
```bash
git add packages/core/src/spotdl_core/matching packages/core/tests/matching/test_select.py packages/core/tests/matching/test_api.py
git commit -m "feat(core): matching.select + api.match — ranked matches, ISRC short-circuit, popularity tiebreak"
```

---

### Task 7: Golden-corpus format, models, and validator

**Files:**
- Create: `scripts/corpus/__init__.py`
- Create: `scripts/corpus/schema.py` (pydantic corpus models — the JSON contract)
- Create: `scripts/corpus/validate.py` (CLI validator)
- Create: `packages/core/tests/matching/corpus/` (empty dir + `README.md` describing the format; cases land in Task 9)
- Test: `scripts/corpus/tests/__init__.py`, `scripts/corpus/tests/test_schema.py`

**Interfaces:** `scripts/` is workspace tooling, not a published package. It may import `spotdl_core` (it is a dev consumer, not part of the `core←server←cli` chain; import-linter roots do not include `scripts`). Add `scripts/corpus/tests` to `[tool.pytest.ini_options] testpaths` in the root `pyproject.toml` so `make test` runs schema tests.

**CONTRACT — corpus JSON format (one file = a JSON array of `CorpusCase`; committed under `packages/core/tests/matching/corpus/*.json`):**
```python
# scripts/corpus/schema.py
from pydantic import BaseModel, ConfigDict, Field


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorpusAlbum(_M):
    name: str
    year: int | None = None


class CorpusTrack(_M):
    name: str
    artists: tuple[str, ...] = Field(min_length=1)
    duration_ms: int
    album: CorpusAlbum | None = None
    isrc: str | None = None
    explicit: bool | None = None
    provider: str | None = None       # e.g. "spotify"
    provider_id: str | None = None


class CorpusCandidate(_M):
    provider: str                     # ProviderId value, e.g. "ytmusic"
    provider_id: str
    url: str
    name: str
    artists: tuple[str, ...] = ()
    duration_ms: int | None = None
    album: str | None = None
    isrc: str | None = None
    verified: bool = False
    popularity: int | None = None     # provider-native (Spotify 0..100 or view count)


class CorpusCase(_M):
    case_id: str                      # unique, kebab-case
    source: str                       # "v4-recorded" | "hand-verified"
    description: str                  # trap type / human note
    track: CorpusTrack
    candidates: tuple[CorpusCandidate, ...] = Field(min_length=1)
    expected_pick_index: int | None   # ground truth: index into candidates, or None = "no match expected"
    v4_pick_index: int | None         # what v4's matcher chose on these candidates (filled by recorder)
    notes: str = ""

    # validators (implement): source in the allowed set; case_id kebab & unique
    # (uniqueness checked across a file in validate.py, not per-model); indices
    # in range [0, len(candidates)) or None.


class Corpus(_M):
    cases: tuple[CorpusCase, ...]
```

Semantics:
- `expected_pick_index` is **ground truth** — for `hand-verified` cases a human sets it; for `v4-recorded` cases it equals `v4_pick_index` (we trust v4 there).
- `v4_pick_index` is what v4's matcher chose (the recorder fills it for both kinds). It lets the gate measure v4 accuracy against ground truth on `hand-verified` traps, so v5 can *beat* v4, not just agree with it.
- `expected_pick_index = None` means "the correct answer is no match" — v5 `match()` should return an empty list or a head that the gate treats as "no pick".

**CONTRACT — mapping helpers (used by recorder and the gate test):** `schema.py` also exposes:
```python
def to_track(case_track: CorpusTrack) -> spotdl_core.model.Track: ...
def to_candidates(cands: tuple[CorpusCandidate, ...]) -> list[spotdl_core.model.AudioCandidate]: ...
```
These translate corpus JSON → core model objects (mapping `provider` strings to `ProviderId`, `CorpusAlbum` → `AlbumRef`). This is the single conversion point the CI gate reuses.

**`validate.py`** — CLI (`python -m scripts.corpus.validate <glob>`): loads each file as `list[CorpusCase]`, asserts unique `case_id` across all files, asserts every index in range, prints a summary (`N cases, K hand-verified, M v4-recorded`); non-zero exit on any error. Reused by CI (Task 10) as a cheap structural check.

- [ ] **Step 1:** Write `test_schema.py`: valid case round-trips; `extra="forbid"` rejects unknown keys; out-of-range `expected_pick_index` raises; `to_track`/`to_candidates` produce correct model objects; validator flags duplicate `case_id`.
- [ ] **Step 2:** Implement `schema.py`, `validate.py`; add `scripts/corpus/tests` to `testpaths`.
- [ ] **Step 3:** `uv run pytest scripts/corpus/tests -v` green; mypy clean (add `scripts` to the mypy invocation in the `Makefile` `typecheck` target: `uv run mypy packages/core/src apps/server/src apps/cli/src scripts`).
- [ ] **Step 4:** `make check` green. Commit:
```bash
git add scripts/corpus pyproject.toml Makefile packages/core/tests/matching/corpus
git commit -m "feat(corpus): golden-corpus JSON schema, model mapping, and validator"
```

---

### Task 8: Corpus recorder (offline v4 runner) + online harvester

**Files:**
- Create: `scripts/corpus/record_v4.py` (PEP-723 inline script — computes v4's pick offline from stored candidates)
- Create: `scripts/corpus/harvest.py` (PEP-723 inline script — one-time ONLINE fetch of candidate sets from v4 providers; NOT run in CI)
- Test: `scripts/corpus/tests/test_record_v4.py`

**How the recorder runs v4 offline (this is the decided approach — specify it exactly):**
- `record_v4.py` is a `uv run --script` PEP-723 file. It calls **only pure functions**: `spotdl.utils.matching.order_results` and `spotdl.utils.matching.get_best_matches`. It never instantiates `AudioProvider` (which would build a `YoutubeDL`) and never imports `spotdl.providers.audio.*`, so no network I/O happens.
- **Import bootstrap (exact technique):** v4's `spotdl/__init__.py` imports the entire application (`spotdl.console`, `Downloader`, …), so a plain `sys.path` import of `spotdl.utils.matching` would execute it and drag in mutagen/ytmusicapi/soundcloud/etc. The recorder bypasses it by pre-registering stub parent packages before importing the submodules:
```python
import sys, types
from pathlib import Path

V4 = Path("~/Projects/xnetcat/spotdl-v4-reference").expanduser()

def _stub_pkg(name: str, path: Path) -> None:
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]        # make it a package without running __init__.py
    sys.modules[name] = mod

sys.path.insert(0, str(V4))
_stub_pkg("spotdl", V4 / "spotdl")
_stub_pkg("spotdl.utils", V4 / "spotdl" / "utils")
_stub_pkg("spotdl.types", V4 / "spotdl" / "types")

from spotdl.types.result import Result                              # noqa: E402
from spotdl.types.song import Song                                  # noqa: E402
from spotdl.utils.matching import get_best_matches, order_results   # noqa: E402
```
  With the stubs, the submodule chain still transitively loads `yt_dlp` (via `spotdl.utils.formatter`), `spotipy` + `requests` (via `spotdl.types.song` → `spotdl.utils.spotify`), and `rich` (via `spotdl.utils.logging`) — those packages must be installed (imported at module load, never used for I/O). The PEP-723 header below pins all of them; this is settled here, not deferred to implementation.
- **v4 object reconstruction (verbatim — v4's `Song` is a dataclass with ~20 required fields and NO defaults, so every field must be supplied explicitly):**
```python
def to_v4_song(t: CorpusTrack) -> "Song":   # spotdl.types.song.Song
    return Song(
        name=t.name,
        artists=list(t.artists),
        artist=t.artists[0],
        genres=[],                                        # placeholder, unread by order_results
        disc_number=1,                                    # placeholder
        disc_count=1,                                     # placeholder
        album_name=t.album.name if t.album else "",       # read by calc_album_match
        album_artist=t.artists[0],                        # placeholder
        duration=round(t.duration_ms / 1000),             # read by calc_time_match (seconds)
        year=(t.album.year if t.album and t.album.year else 0),  # placeholder
        date="",                                          # placeholder
        track_number=1,                                   # placeholder
        tracks_count=1,                                   # placeholder
        song_id=t.provider_id or t.name,                  # debug-log key only
        explicit=t.explicit,  # may be None; order_results guards on `is not None`
        publisher="",                                     # placeholder
        url="",                                           # placeholder
        isrc=t.isrc,
        cover_url=None,                                   # placeholder
        copyright_text=None,                              # placeholder
    )


def to_v4_result(c: CorpusCandidate) -> "Result":   # spotdl.types.result.Result
    return Result(
        source=c.provider,
        url=c.url,
        verified=c.verified,
        name=c.name,
        duration=(c.duration_ms or 0) / 1000,
        author=(c.artists[0] if c.artists else ""),
        result_id=c.provider_id,
        isrc_search=False,          # stored sets are not ISRC-search mode
        search_query=None,
        artists=tuple(c.artists) or None,
        views=c.popularity,         # stored views -> no get_views network call
        explicit=None,
        album=c.album,
    )
```
  (`order_results` reads `name`, `artists`, `artist`, `album_name`, `duration`, `explicit`, `song_id` from `Song`; every other required field gets the placeholder above. `Song.explicit` is typed `bool` but the dataclass does not enforce it — pass `t.explicit` through unchanged so a `None` correctly disables v4's explicit branch.)
- It computes v4's pick **without network**: `scores = order_results([to_v4_result(c) for c in case.candidates], to_v4_song(case.track))`; if empty → `None`; else replicate `get_best_result`'s *pure* selection inline: `get_best_matches(scores, 8)`; if one → that; else the views tiebreak over stored `Result.views`. **Replicate v4 bug-for-bug**, including the loop-variable shadowing in `get_best_result`: when views have no variance (`highest_views in (0, lowest_views)`), v4 returns the **last-iterated** near-tie entry, not the top-scored — the recorder must do the same, because its job is to reproduce v4's actual pick. (Consequence for the gate: on v4-recorded no-variance near-ties, v5's deliberate fix may legitimately disagree with `expected_pick_index`; if the Task 10 gate fails specifically on such cases, reclassify them as `hand-verified` with human ground truth rather than weakening the gate.)
- Output: writes `v4_pick_index` into each `CorpusCase` (the index of the candidate whose `url` matches v4's chosen result). For `v4-recorded` cases it also sets `expected_pick_index = v4_pick_index`. For `hand-verified` cases it leaves the human-authored `expected_pick_index` untouched.

**PEP-723 header (both scripts — includes v4's transitive import chain, floors from v4's `pyproject.toml`):**
```python
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
# ]
# ///
```
> These are import-time-only dependencies: the recorder makes zero network calls. `harvest.py` additionally needs `ytmusicapi>=1.11.1,<2` (and Spotify credentials) since it actually drives v4's providers online. **Do not** import `spotdl.providers.audio.*` in `record_v4.py`.

**The harvester (`harvest.py`, run once by a maintainer, ONLINE, never in CI):**
- Reads a list of Spotify track URLs (seeded from `~/Projects/xnetcat/spotdl-v4-reference/tests/test_matching.py` — ~40 curated URLs already there, plus the commented-out ones as extra candidates) and, using v4's own providers from the reference tree, fetches the real `Result` candidate sets for each, serializing them to `CorpusCandidate` JSON (including `views`→`popularity`, `verified`, `duration`, `isrc`, `album`). It writes provisional `CorpusCase`s with `source="v4-recorded"` and no picks; `record_v4.py` then fills the picks offline. Where v4 VCR cassettes already contain YTMusic search interactions (`~/Projects/xnetcat/spotdl-v4-reference/tests/providers/audio/cassettes/test_ytmusic/*.yaml`), the harvester may replay them instead of hitting the network, reducing live calls.
- The harvester is **excluded from CI and from `make check`** (it needs network + Spotify creds). Document this at the top of the file and in `scripts/corpus/README.md`.

- [ ] **Step 1:** Write `test_record_v4.py`: feed a tiny hand-built corpus file with a clear correct candidate, run the recorder's offline pick function (import it as a module function, not via subprocess), assert `v4_pick_index` points at the obvious match. Include one case where two candidates tie on score but differ on `views` → recorder picks the higher-views one (exercises the ported tiebreak), and one near-tie case with **no views variance** → recorder reproduces v4's last-iterated pick (the `get_best_result` shadowing bug, replicated deliberately). Run; confirm failing.
- [ ] **Step 2:** Implement `record_v4.py` with a testable `compute_v4_pick(case: CorpusCase) -> int | None` function plus a thin CLI wrapper (`__main__`). Implement `harvest.py`. Verify the offline import surface (`uv run --script scripts/corpus/record_v4.py --help` works without network).
- [ ] **Step 3:** `uv run pytest scripts/corpus/tests/test_record_v4.py -v` green. Manually smoke the recorder against a 2-case fixture file and confirm picks written.
- [ ] **Step 4:** `make check` green (harvester excluded). Commit:
```bash
git add scripts/corpus/record_v4.py scripts/corpus/harvest.py scripts/corpus/tests/test_record_v4.py scripts/corpus/README.md
git commit -m "feat(corpus): offline v4 pick recorder + online candidate harvester"
```

---

### Task 9: Seed the golden corpus (~100–300 cases) + committed baseline

**Files:**
- Create: `packages/core/tests/matching/corpus/recorded.json` (v4-recorded cases, harvested + recorded)
- Create: `packages/core/tests/matching/corpus/handcrafted.json` (hand-verified trap cases)
- Create: `packages/core/tests/matching/corpus/baseline.json` (committed v4 accuracy baseline)

**Interfaces:**
- Produces: the committed corpus the CI gate (Task 10) reads. CI never runs the harvester/recorder; it reads these JSON files and `baseline.json` only — fully offline, no v4 dependency in CI.

- [ ] **Step 1: Harvest + record the `v4-recorded` set (maintainer, offline CI-safe output).** Run `harvest.py` (online, once) over the ~40 curated URLs from v4's `test_matching.py` plus the commented-out entries, producing candidate sets; then run `record_v4.py` to fill picks. Aim for ~120–250 recorded cases (multiple candidates per track already gives breadth). Store in `recorded.json`. Every case: `source="v4-recorded"`, `expected_pick_index == v4_pick_index`.

- [ ] **Step 2: Hand-author the trap set (`handcrafted.json`, ~40–60 cases, `source="hand-verified"`).** Required trap coverage (at least 3 cases each): remix vs original; live vs studio; cover vs original; slowed/reverb/8d-audio; instrumental vs vocal; CJK titles (romaji-matching, e.g. the `Ai kamano` tracks); multi-artist collapsed into one channel; `feat.`-notation mismatch; duration outliers (right title/artist, wrong length — a long album version vs single); ISRC-equal-but-wrong-name (short-circuit sanity); "no correct answer" (`expected_pick_index=null`) where every candidate is a trap. For each, hand-set `expected_pick_index`, then run `record_v4.py` to fill `v4_pick_index` (this is where v4 may be *wrong*, giving v5 room to beat it).

- [ ] **Step 3: Validate the corpus.** `uv run python -m scripts.corpus.validate "packages/core/tests/matching/corpus/*.json"` → exit 0, unique ids, total in the 100–300 range.

- [ ] **Step 4: Generate the committed baseline.** Write `baseline.json`:
```json
{
  "total": 0,
  "v4_correct": 0,
  "v4_accuracy": 0.0,
  "generated_from": ["recorded.json", "handcrafted.json"],
  "note": "v4 accuracy vs expected_pick_index across the whole corpus; regenerate only when corpus changes"
}
```
Compute `v4_correct = count(v4_pick_index == expected_pick_index)` over all cases, `v4_accuracy = v4_correct / total`. Provide a tiny `scripts/corpus/make_baseline.py` (PEP-723 or a `validate.py --baseline` flag) that emits this deterministically from the committed JSON, so the baseline is reproducible and reviewable.

- [ ] **Step 5:** `make check` green. Commit:
```bash
git add packages/core/tests/matching/corpus scripts/corpus/make_baseline.py
git commit -m "test(corpus): seed golden corpus (recorded + hand-verified traps) and v4 baseline"
```

---

### Task 10: CI gate — `test_corpus.py` accuracy assertion + workflow wiring

**Files:**
- Create: `packages/core/tests/matching/test_corpus.py`
- Modify: `.github/workflows/ci.yml` (add corpus validation + gate to the existing `python` job)

**Interfaces:**
- Produces: the spec §5.3 / §11 release gate — **v5 accuracy on the golden corpus must be ≥ the committed v4 baseline**, with a readable per-case regression report. Runs in the existing offline `python` job (fast, no network, no v4).

**CONTRACT — the gate test:**
```python
# packages/core/tests/matching/test_corpus.py
# 1. Load every corpus/*.json via scripts.corpus.schema.CorpusCase.
# 2. Load baseline.json.
# 3. For each case: track = to_track(...); cands = to_candidates(...);
#    matches = spotdl_core.matching.match(track, cands, MATCHER_V5_DEFAULT)
#    v5_pick_index = index of matches[0].candidate in cands (by (provider, provider_id)),
#                    or None if matches == [].
#    correct = (v5_pick_index == case.expected_pick_index)
# 4. v5_accuracy = correct / total.
# 5. Build a regression report: list every case where v5 is WRONG (v5_pick vs expected),
#    flagging those where v4 was RIGHT (v4_pick == expected) as true regressions.
# 6. assert v5_accuracy >= baseline["v4_accuracy"], with the report in the failure message.
```

Requirements:
- The test **imports `scripts.corpus.schema`** for the models/mapping (schema is dev tooling; the test is core's test suite, not core's runtime — allowed. Ensure `scripts` is importable in the test env: it is, since pytest runs from the repo root and `scripts/corpus/__init__.py` exists; add a `conftest.py` sys.path shim under `packages/core/tests/matching/` only if collection needs it).
- Failure message must be **readable**: one line per regressed case — `case_id | expected=<url> | v5=<url> | v4=<url> | source | description`. Sort true regressions (v4-right, v5-wrong) first.
- Add a second, non-gating assertion helper that prints overall stats (`v5_accuracy`, `v4_accuracy`, counts by source) via `-s`, so the accuracy report per matcher version (spec §11) is visible in CI logs even when green.
- The gate must be **deterministic**: `match()` is pure, corpus + baseline are committed. No flakiness.

**CI wiring** — extend the existing `python` job in `.github/workflows/ci.yml` (do not add a new job; the gate is fast and offline):
```yaml
      - run: uv run python -m scripts.corpus.validate "packages/core/tests/matching/corpus/*.json"
      # (pytest step already present runs test_corpus.py as part of the suite)
```
Place the validate step before `uv run pytest`. The corpus gate itself runs inside the existing `uv run pytest` step (it is a normal test under `testpaths`). Optionally add a focused, labeled run for log visibility:
```yaml
      - run: uv run pytest packages/core/tests/matching/test_corpus.py -v -s
```

- [ ] **Step 1:** Write `test_corpus.py`. On the seeded corpus, run it: it must **pass** (v5 ≥ v4). If it fails, investigate per the regression report — a genuine v5 regression vs v4 on a `v4-recorded` case is a matcher bug to fix in Tasks 3–6 (do **not** weaken the corpus or gate to make it pass; use superpowers:systematic-debugging).
- [ ] **Step 2:** Wire the validate step + optional visibility step into `ci.yml`.
- [ ] **Step 3:** Run the exact CI commands locally: `uv run python -m scripts.corpus.validate "packages/core/tests/matching/corpus/*.json"` then `make check`. All green.
- [ ] **Step 4: Commit and push.**
```bash
git add packages/core/tests/matching/test_corpus.py .github/workflows/ci.yml
git commit -m "test(corpus): CI gate — v5 matcher accuracy must meet or beat v4 baseline"
git push
```
Then verify the run: `gh run watch --branch v5` (or `gh run list --branch v5 --limit 1`) — the `python` job green with the corpus gate passing.

---

## Self-review: v4 heuristic coverage

**Every heuristic in v4 `matching.py` + the matching parts of `formatter.py`/`providers/audio/base.py` is either mapped to a v5 feature/gate/selection rule, or explicitly dropped below.**

### Mapped (nothing battle-tested lost)

| v4 element | v5 home |
|---|---|
| `formatter.slugify` (+ `JAP_REGEX`, `DISALLOWED_REGEX`, pykakasi Hepburn) | `text.slugify` (verbatim) |
| `formatter.ratio` (lru_cache fuzz.ratio) | `text.ratio` (verbatim) |
| `ratio(tuple, tuple)` usage in fixup1 | `text.sequence_ratio` |
| `formatter.create_song_title` | `text.song_title` |
| `matching.fill_string` | `text.fill_string` (used by `features.title_similarity`) |
| `matching.create_clean_string` | `text.clean_string` (used by artist fixup2) |
| `matching.sort_string` | `text.sort_tokens` |
| `matching.based_sort` | `text.based_sort` (non-mutating) |
| `matching.check_common_word` | `features.common_word_overlap` + gate `require_common_word` |
| `matching.check_forbidden_words` + `FORBIDDEN_WORDS` | `features.forbidden_words` + `FORBIDDEN_WORDS` (verbatim) + `scoring.forbidden_word_penalty` |
| `matching.create_match_strings` (song-title path) | folded into `features.title_similarity` |
| `matching.calc_main_artist_match` | `features.main_artist_similarity` |
| `matching.calc_artists_match` | `features.other_artist_similarity` |
| `matching.artists_match_fixup1/2/3` | folded into `features.artist_similarity` |
| `matching.calc_name_match` (song-title path) | `features.title_similarity` |
| `matching.calc_time_match` (`exp(-0.1·Δ)·100`) | `features.duration_similarity` |
| `matching.calc_album_match` | `features.album_similarity` |
| `matching.order_results` combination + all gates | `scoring.score` + `HardGates` |
| forbidden `name_match -= 15` per word | `scoring.forbidden_word_penalty` (default 15) |
| verified album blend (`album<=80`) | `scoring.album_blend_when_verified` + `album_blend_ceiling` |
| duration blend (`average<=85`) | `scoring.duration_blend_ceiling` |
| explicit mismatch `-5` | `scoring.explicit_mismatch_penalty` (feature inert until candidate explicit exists — see below) |
| `matching.get_best_matches` (8-pt window) | `select` near-tie window + `SelectionConfig.near_tie_window` |
| `base.get_best_result` views tiebreak (`·15`) | `select` popularity tiebreak (`popularity_prior` in place of views) + `popularity_tiebreak_weight`. Intentional fix of v4's loop-variable shadowing: in the no-variance branch v4 returned the *last-iterated* near-tie entry, not the top-scored; v5 keeps score order (the corpus recorder replicates the v4 bug when recording picks) |
| `base.search` unconditional ISRC rule (exactly one ISRC result, verified → return, no score check) | `select` ISRC rule A (unconditional, evaluated over all candidates incl. gate-rejected) |
| `base.search` scored ISRC rule (best ISRC result score > 80 → return) | `select` ISRC rule B + `isrc_short_circuit_min_score` |

### Dropped, with reason (REQUIRED table)

| v4 element | Why dropped |
|---|---|
| `create_search_query` branch in `create_match_strings` / `calc_name_match` (custom `--search-query` template) | Search-query construction is a `core.providers` search concern (Plan 2), not matching. Matching receives materialized candidates and always uses the `song_title` path. The branch only fired when a user set a custom search template. |
| `result.source == "slider.kz"` special cases (artist-gate bypass; always-blend-time) | slider.kz is not a v5 audio provider (spec §2 audio list). No provider needs the bypass. |
| `result.isrc_search` flag and its guards (`not isrc_search` in album/duration blends; `isrc_search` early return in `get_best_result`) | v5 has no "ISRC search mode" — ISRC is a per-candidate equality *feature* (`isrc_equal`) resolved in `select`'s short-circuit, not a fetch mode. The blend guards keyed on it collapse to unconditional blends (v4-faithful for non-ISRC-search results, which was the common path). |
| `AudioProvider.get_views` network fallback in the tiebreak | Matching is pure/offline. Popularity comes from `AudioCandidate.popularity` (set by providers upstream); no network in `core.matching`. |
| `base.search` streaming early-returns (`best_score>=80 and verified` per options batch; ISRC-url-in-results early return) | These are network round-trip optimizations for v4's incremental search. v5 scores a fully materialized candidate list at once, so ranking is exhaustive; the accuracy-relevant preferences (ISRC, verified-high-score) are preserved in `select`. |
| `filter_results=False` path (return first result at score 100) | A provider/search toggle, not a matching heuristic. |
| `time_match < 0` branch | Dead code — `exp(-0.1·Δ)·100` is always `> 0`. |
| `debug()` / `MATCH`-level logging throughout | Replaced by typed, structured explainability: `ScoreResult.rejection` (`GateReason`) + full `FeatureVector` per candidate via `score_candidates`. Better for server-side explainability than log scraping. |

### Deferred (near-parity gap, documented)

| Gap | Plan |
|---|---|
| `explicit_mismatch` is inert because Plan-1 `AudioCandidate` has no `explicit` field | `features.explicit_mismatch` reads `getattr(candidate, "explicit", None)` and activates automatically if Plan 2 adds the field. The v4 penalty only fired when both sides had explicit metadata (rare for audio providers), so v1 parity impact is negligible. Flagged, not silently dropped. |

### Type consistency check

- Consumes `Track`, `AudioCandidate`, `AlbumRef`, `ProviderId`, `MatchStatus`, `Match`, `FeatureVector` from `core.model` (Plan 1); the only model change is Task 2's `FeatureVector` amendment, called out as a contract change.
- `match(track, candidates, config=MATCHER_V5_DEFAULT) -> list[Match]` matches the spec §5.3 single-entry design and the server's `GET /tracks/{id}/matches` list shape (§6.2).
- `matcher_version` is a `str` on both `ScoringConfig` and `Match` (Plan 1) — consistent with the DB `matches.matcher_version` column (§6.1) and the A/B goal (§9).
- No TBDs: every threshold has a concrete v4-sourced default; every file path, signature, and test case is specified.

### Spec coverage

Implements spec §5.3 in full (feature extraction, declarative versioned scoring with hard gates, ISRC/near-tie selection, golden-corpus CI gate meeting/beating v4) and the matching slice of §11 (golden corpus as a CI gate with a per-version accuracy report). Community-vote overlay (§5.3 final paragraph) is a **server** concern (Plan 6) and out of scope here — matching only produces `status=AUTO` matches; the server pins `community_verified` / re-matches downvoted ones.
