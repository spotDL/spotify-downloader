# Golden-corpus tooling (`scripts/corpus/`)

Workspace tooling for the matching golden corpus. This directory is dev tooling
under `scripts/` — a consumer of `spotdl_core`, deliberately outside the
`core <- server <- cli` layer chain, and never imported by any published package.

| File | Role | Network |
|---|---|---|
| `schema.py` | Pydantic models for the corpus JSON contract + `to_track`/`to_candidates` mappers (single conversion point into `spotdl_core.model`). | offline |
| `validate.py` | CLI structural validator (`python -m scripts.corpus.validate <glob>...`); unique `case_id`s, in-range pick indices. | offline |
| `record_v4.py` | **Offline** recorder: replays v4's matcher pick over stored candidates and writes `v4_pick_index` (+ `expected_pick_index` for `v4-recorded` cases). PEP-723 script. | **offline** |
| `harvest.py` | **Online, one-shot** maintainer tool: fetches real v4 candidate sets from Spotify + YouTube Music into provisional cases. PEP-723 script. | **ONLINE — excluded from CI** |

## Corpus files

One corpus file is a JSON array of `CorpusCase`, committed under
`packages/core/tests/matching/corpus/*.json`. Each case pins a `track`, its
candidate `AudioCandidate`s, the human/`v4` ground-truth pick indices, and a
`source` of either `v4-recorded` or `hand-verified`.

## `record_v4.py` — offline v4 pick recorder

Replays spotDL v4's **pure** matcher (`spotdl.utils.matching.order_results` +
the pure selection from `AudioProvider.get_best_result`) over stored candidate
sets. It makes **zero network calls**: it never instantiates `AudioProvider`
(no `YoutubeDL`) and never imports `spotdl.providers.audio.*`.

v4's `spotdl/__init__.py` eagerly imports the whole application, so a plain
import of `spotdl.utils.matching` would drag in the CLI/downloader. The recorder
sidesteps this by pre-registering **stub parent packages** (`spotdl`,
`spotdl.utils`, `spotdl.types`) whose `__path__` points into the read-only v4
reference tree, then importing only the leaf modules. That leaf chain still
loads `yt_dlp` / `spotipy` / `requests` / `rich` / `typing_extensions` **at
import time only** (never used for I/O); the PEP-723 header pins them so `uv`
supplies them in an ephemeral venv.

It replicates v4 **bug-for-bug**, including the loop-variable shadowing in
`get_best_result`: on a near-tie window with **no view variance**
(`highest_views in (0, lowest_views)`), v4 returns the *last-iterated* entry, not
the top-scored one. The recorder reproduces that, because its job is to record
v4's *actual* pick. (If the Task 10 gate later fails specifically on such a
no-variance near-tie where v5's deliberate fix disagrees, reclassify that case as
`hand-verified` with human ground truth rather than weakening the gate.)

`v4-recorded` cases get `expected_pick_index = v4_pick_index`; `hand-verified`
cases keep their human-authored `expected_pick_index` untouched.

Run it (offline):

```bash
uv run --script scripts/corpus/record_v4.py packages/core/tests/matching/corpus/*.json
# preview without writing:
uv run --script scripts/corpus/record_v4.py --dry-run packages/core/tests/matching/corpus/*.json
```

### Tests

`tests/test_record_v4.py` imports `compute_v4_pick` as a module function (never a
subprocess). Because the recorder imports the v4 reference tree and its
import-time deps — neither of which exists in a clean CI checkout — the test
**skips cleanly** when that import fails, keeping the default `make check` suite
fully offline. To actually run it, supply the deps ephemerally:

```bash
uv run --with yt-dlp --with spotipy --with requests --with rich \
    pytest scripts/corpus/tests/test_record_v4.py -v
```

## `harvest.py` — online candidate harvester (NOT run in CI)

**Excluded from CI and from `make check`.** It hits the network (Spotify metadata
+ YouTube Music search) and needs Spotify credentials. Run once by a maintainer
to seed/refresh the corpus; `record_v4.py` then fills the picks offline.

```bash
export SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=...
uv run --script scripts/corpus/harvest.py \
    -o packages/core/tests/matching/corpus/harvested.json
uv run --script scripts/corpus/record_v4.py \
    packages/core/tests/matching/corpus/harvested.json
```

Seed URLs default to the ~40 curated (and commented-out) Spotify track URLs in
`~/Projects/xnetcat/spotdl-v4-reference/tests/test_matching.py`; override with
`--urls-file`. `--fetch-views` additionally resolves each candidate's view count
into `popularity` via yt-dlp (accurate but slow — one metadata extract per
candidate). Without it, `popularity` stays `null`.

To reduce live YTMusic calls, a maintainer may instead replay v4's VCR cassettes
under `~/Projects/xnetcat/spotdl-v4-reference/tests/providers/audio/cassettes/test_ytmusic/*.yaml`.
That replay path is a supported manual alternative; the harvester itself talks to
the live provider.
