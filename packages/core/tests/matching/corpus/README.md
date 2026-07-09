# Golden matching corpus

This directory holds the **golden corpus** that gates matcher accuracy in CI.
Each file is a JSON array of `CorpusCase` objects; the on-disk contract is
defined and enforced by `scripts/corpus/schema.py` (pydantic, `extra="forbid"`).
Cases are seeded in Task 9 — this directory ships empty until then except for
this README.

## File format

A corpus file is a JSON array. Each element is one `CorpusCase`:

```jsonc
[
  {
    "case_id": "remix-trap-01",          // unique, kebab-case ([a-z0-9] + hyphens)
    "source": "hand-verified",           // "hand-verified" | "v4-recorded"
    "description": "clean original vs a remix that shares the title",
    "track": {                            // the Spotify-side ground-truth track
      "name": "Song Title",
      "artists": ["Real Artist", "Feature Artist"],  // >= 1, main artist first
      "duration_ms": 210000,
      "album": { "name": "The Album", "year": 2020 },  // optional
      "isrc": "USABC1234567",             // optional
      "explicit": false,                  // optional (tri-state: omit = unknown)
      "provider": "spotify",              // optional ProviderId value
      "provider_id": "..."                // optional
    },
    "candidates": [                       // >= 1 audio candidates, in a fixed order
      {
        "provider": "ytmusic",            // required ProviderId value
        "provider_id": "abc123",
        "url": "https://music.youtube.com/watch?v=abc123",
        "name": "Song Title",
        "artists": ["Real Artist"],       // optional (default [])
        "duration_ms": 211000,            // optional
        "album": "The Album",             // optional
        "isrc": "USABC1234567",           // optional
        "verified": true,                 // optional (default false)
        "popularity": 90                  // optional; provider-native scale
      }
    ],
    "expected_pick_index": 0,             // ground truth: index into candidates, or null
    "v4_pick_index": 0,                   // what v4's matcher chose (recorder fills)
    "notes": ""                           // optional free-form
  }
]
```

## Semantics

- **`expected_pick_index`** is the *ground truth* — the index of the candidate a
  correct matcher must pick. For `hand-verified` cases a human sets it. For
  `v4-recorded` cases it equals `v4_pick_index` (we trust v4 there).
- **`v4_pick_index`** is what spotDL v4's matcher chose on exactly these
  candidates (the recorder fills it for both kinds). It lets the CI gate measure
  v4's accuracy against ground truth on `hand-verified` traps, so v5 can *beat*
  v4, not merely agree with it.
- **`expected_pick_index: null`** means the correct answer is **no match** — v5
  `match()` should return an empty result (or a head the gate treats as "no
  pick").

## Rules enforced by the schema / validator

- `case_id` is kebab-case and unique across all corpus files.
- `source` is one of `hand-verified` / `v4-recorded`.
- `track.artists` has at least one entry; `candidates` has at least one entry.
- `expected_pick_index` and `v4_pick_index` are `null` or in
  `[0, len(candidates))`.
- Unknown keys are rejected (`extra="forbid"`).

## Validating

```bash
python -m scripts.corpus.validate "packages/core/tests/matching/corpus/*.json"
```

Prints `N cases, K hand-verified, M v4-recorded` and exits non-zero on any
structural error (bad JSON, unknown key, out-of-range index, duplicate
`case_id`).
