# spotDL v5 `core.download` Implementation Plan (Plan 4 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `packages/core/src/spotdl_core/download/` — spec §5.4's download pipeline. v4's ~860-line `Downloader.search_and_download` god-method is decomposed into a pipeline of small, individually-testable typed steps threaded through a frozen `DownloadContext`: plan output path (templating, restrict modes, OS length limits, overwrite/skip/archive decisions) → fetch audio (yt-dlp) → convert (ffmpeg, bitrate modes, move-not-reencode fast path, passthrough args) → embed metadata (mutagen; mp3/m4a/flac/ogg/opus/wav presets, cover art, plain+synced lyrics incl. SYLT, ISRC, source URL) → post-process (.lrc, m3u, archive update, SponsorBlock). Full v4 feature parity (spec §5.4). Every blocking third-party call is injected behind a seam so the **default test suite is fully offline**.

**Architecture:** `core.download` is a sub-package of `packages/core` (spec §5). It has no knowledge of HTTP servers, databases, or UI; it consumes the domain model (`core.model`, Plan 1) and the shared exception taxonomy (`core.providers.errors`, Plan 2). It is a **single-track engine**: `DownloadEngine.download(request, on_progress=None) -> DownloadOutcome` downloads exactly one track. It contains **no queueing, batching, or concurrency orchestration** — that is the server's job (Plan 7). The engine runs each blocking step (yt-dlp, ffmpeg subprocess, mutagen) in a thread executor so it is async-friendly. All external I/O (yt-dlp, ffmpeg binary, cover HTTP fetch, synced-lyrics search, SponsorBlock) is reached through **injected collaborators / protocols** (no module-level singletons), which is also the seam the offline tests fill with fakes. ffmpeg discovery/auto-download stays **out of core**: the binary is located via a config parameter; acquisition is a CLI/installer concern (Plan 8/11).

**Tech Stack:** Python 3.13, pydantic v2 (frozen models), yt-dlp (audio fetch + SponsorBlock postprocessors), mutagen (tag embedding), stdlib `subprocess`/`asyncio`/`shutil`/`pathlib`. Optional runtime: `syncedlyrics` (for `.lrc` generation, lazily imported). Tests: pytest + pytest-asyncio; fake fetcher/cover/lyrics seams for the offline default suite; convert/tag tests exercise a real ffmpeg + real mutagen and **skip** when the ffmpeg binary is absent (CI installs ffmpeg via `FedericoCarboni/setup-ffmpeg`).

## Global Constraints

- Python `>=3.13`; single uv lockfile at the workspace root.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Dependency direction (spec §3, machine-enforced by import-linter): `core ← server ← cli`. `spotdl_core` (and therefore everything in `core.download`) must **never** import `spotdl_server` or `spotdl_cli`. `core.download` may import only `core.model`, `core.providers.errors`, the standard library, and third-party libraries.
- New **runtime** dependencies go in `packages/core/pyproject.toml`; new **test-only** dependencies go in the root `pyproject.toml` `[dependency-groups].dev`. Exact version floors are given per task and match v4's `pyproject.toml` where a dependency is shared.
- **ffmpeg is a binary, not a pip dependency.** It is never installed via pip; core locates it via `DownloadConfig.ffmpeg_path` (default `"ffmpeg"`, resolved on `PATH`).
- No code is copied wholesale from the `xnetcat-rewrite` branch. v4 (`~/Projects/xnetcat/spotdl-v4-reference/`) is an **algorithm/shape reference only** (exact paths cited per task). Behaviour is ported deliberately and tested; code is rewritten against the v5 model.
- **No module-level mutable singletons.** Collaborators (fetcher, cover downloader, lyrics search, ffmpeg path, temp/output dirs) are constructed by the caller and injected into `DownloadEngine`.
- TDD: every task writes failing tests first (RED), then implements to green (GREEN). The **default `make check` suite is fully offline** — no network, and no dependency on an installed ffmpeg for lint/typecheck/collection. Tests needing a real ffmpeg binary are guarded by a `requires_ffmpeg` autoskip fixture.
- All test directories are packages (`__init__.py` present); pytest runs with `--import-mode=importlib` (configured in Plan 1's root `pyproject.toml`).
- `make check` (lint + typecheck + test + web-check) must pass at the end of **every** task.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## What already exists (Plans 1–3, do not recreate)

- `spotdl_core.model` — `ProviderId`, `EntityType`, `LyricsKind`, `MatchStatus` enums; frozen `Track`, `AlbumRef`, `ArtistRef`, `AudioCandidate`, `Lyrics`, `Match`, `FeatureVector`. This plan **amends** `Track`/`AlbumRef` (Task 2) for full VARS/tag parity.
  - `Track(name, artists: tuple[str,...], duration_ms: int, album: AlbumRef|None, isrc, explicit, track_number, disc_number, genres: tuple[str,...], year, provider, provider_id)`; property `main_artist`.
  - `AlbumRef(name, album_artist, year, track_count, cover_url)`.
  - `AudioCandidate(provider, provider_id, url, name, artists=(), duration_ms=None, album=None, isrc=None, verified=False, popularity=None)`.
  - `Lyrics(kind: LyricsKind, text: str, source: ProviderId)`.
- `spotdl_core.providers.errors` — the **shared** exception taxonomy (Plan 2, Task 1). Already defined there and re-exported from `spotdl_core.providers`:
  - `SpotdlError` (root); `DownloadFailed(message, *, step: str)`; `ConversionFailed(message)` (sets `step="convert"`); `MetadataEmbedFailed(message)` (sets `step="embed"`).
  - This plan **appends** `AudioFetchFailed` and `PostProcessingFailed` (Task 1) to the same file, matching the existing pattern.
- `spotdl_core.matching.api.match(track, candidates) -> list[Match]` (Plan 3) produces the ranked `Match` list; the head `Match.candidate` is the `AudioCandidate` fed into a `DownloadRequest`. `core.download` does **not** import `core.matching` — the caller (server, Plan 7) picks the candidate and constructs the request.
- Root `pyproject.toml`: ruff (E,F,I,UP,B,SIM; line-length 100), mypy strict, pytest `asyncio_mode = "auto"`, `addopts = "--import-mode=importlib"`, `testpaths` includes `packages/core/tests`.

## Package layout produced by this plan

```
packages/core/src/spotdl_core/download/
├─ __init__.py         # public API re-exports (Task 3+)
├─ context.py          # DownloadRequest, DownloadConfig, DownloadContext,
│                      #   DownloadOutcome, enums, ProgressEvent/ProgressCallback,
│                      #   Step type, TemplateFields  (Task 3)  [CONTRACT]
├─ paths.py            # template rendering (all VARS), restrict modes,
│                      #   smart_split length handling, overwrite/skip/archive
│                      #   PURE decision functions, archive load/save  (Task 4)  [CONTRACT for VARS + step sig]
├─ fetch.py            # Fetcher protocol + YtDlpFetcher + FetchStep  (Task 5)  [CONTRACT for Fetcher/FetchResult]
├─ convert.py          # FFMPEG_CODECS table, bitrate resolution, ffmpeg arg
│                      #   building, move-fast-path, ConvertStep  (Task 6)  [CONTRACT for codec table]
├─ tags.py             # mutagen presets per container + embed + EmbedStep  (Task 7)  [CONTRACT for presets]
├─ post.py             # lrc / m3u / archive-update / SponsorBlock  (Task 8)
└─ engine.py           # DownloadEngine.download(request, on_progress)  (Task 9)  [CONTRACT for entry point]

packages/core/tests/download/
├─ __init__.py
├─ conftest.py               # requires_ffmpeg autoskip, silent-audio fixtures, fakes
├─ fixtures/tiny.m4a         # committed few-KB real audio (fetch/convert seam input)
├─ fixtures/tiny.opus        # committed few-KB real audio (webm/opus copy path)
└─ test_*.py
```

---

### Task 1: Package scaffold, dependencies, test policy, and error-taxonomy additions

**Files:**
- Modify: `packages/core/pyproject.toml` (add runtime deps `yt-dlp`, `mutagen`; add optional `syncedlyrics`)
- Modify: `packages/core/src/spotdl_core/providers/errors.py` (append two download subclasses)
- Modify: `packages/core/src/spotdl_core/providers/__init__.py` (extend `__all__`)
- Create: `packages/core/src/spotdl_core/download/__init__.py`
- Create: `packages/core/tests/download/__init__.py`, `packages/core/tests/download/conftest.py`, `packages/core/tests/download/test_errors.py`
- Create committed fixtures: `packages/core/tests/download/fixtures/tiny.m4a`, `packages/core/tests/download/fixtures/tiny.opus`

**Interfaces produced (relied on by every later task and by Plan 7):**
- Runtime deps available; `AudioFetchFailed` / `PostProcessingFailed` in the taxonomy; the `requires_ffmpeg` autoskip fixture and the silent-audio session fixtures; committed tiny audio inputs.

**Contract vs freedom:** The two new exception classes, their inheritance, and their fixed `step` values are a **CONTRACT** (Plan 7 maps `step` to API error codes). The test-policy plumbing is free to refactor.

- [ ] **Step 1: Add runtime dependencies.** In `packages/core/pyproject.toml` extend `dependencies` (floors match v4 `pyproject.toml`):
```toml
    "yt-dlp>=2025.09.26,<2027",
    "mutagen>=1.47.0,<2",
```
Add an optional extra for `.lrc` generation (kept optional so a broken `syncedlyrics` cannot break imports):
```toml
[project.optional-dependencies]
lrc = ["syncedlyrics>=1.0.1,<2"]
```
Run `uv sync --all-packages`.

- [ ] **Step 2: Write the failing test `packages/core/tests/download/test_errors.py`.**
```python
import pytest

from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    MetadataEmbedFailed,
    PostProcessingFailed,
    SpotdlError,
)


@pytest.mark.parametrize(
    ("exc", "step"),
    [
        (AudioFetchFailed("x"), "fetch"),
        (ConversionFailed("x"), "convert"),
        (MetadataEmbedFailed("x"), "embed"),
        (PostProcessingFailed("x"), "post"),
    ],
)
def test_download_subclasses_carry_step(exc: DownloadFailed, step: str) -> None:
    assert isinstance(exc, DownloadFailed)
    assert isinstance(exc, SpotdlError)
    assert exc.step == step


def test_generic_download_failed_requires_step() -> None:
    err = DownloadFailed("boom", step="fetch")
    assert err.step == "fetch"
```

- [ ] **Step 3: RED.** `uv run pytest packages/core/tests/download/test_errors.py -v` → ImportError on the two new names.

- [ ] **Step 4: Append to `providers/errors.py`** — **CONTRACT (match exactly), placed after `ConversionFailed`/`MetadataEmbedFailed`:**
```python
class AudioFetchFailed(DownloadFailed):
    """yt-dlp failed to fetch/download the chosen audio candidate."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="fetch")


class PostProcessingFailed(DownloadFailed):
    """A post-processing step (lrc/m3u/archive/SponsorBlock) failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="post")
```
Add `AudioFetchFailed` and `PostProcessingFailed` to `providers/__init__.py` `__all__` (kept sorted). Make `download/__init__.py` re-export the download-relevant errors:
```python
from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    MetadataEmbedFailed,
    PostProcessingFailed,
)
```
(Later tasks extend `download/__init__.py`'s `__all__` with the public models/engine.)

- [ ] **Step 5: Write `packages/core/tests/download/conftest.py`** — the offline-test seam:
```python
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _ffmpeg_present() -> bool:
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def requires_ffmpeg() -> None:
    """Skip a test when no ffmpeg binary is on PATH (CI installs one)."""
    if not _ffmpeg_present():
        pytest.skip("ffmpeg binary not available")


@pytest.fixture(scope="session")
def silent_audio(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Generate 1s silent files per output format with ffmpeg, once per session.
    Skips the whole group when ffmpeg is absent. Used by tag tests (real mutagen)."""
    if not _ffmpeg_present():
        pytest.skip("ffmpeg binary not available")
    import subprocess

    out = tmp_path_factory.mktemp("silent")
    made: dict[str, Path] = {}
    for fmt, codec in [
        ("mp3", ["-codec:a", "libmp3lame"]),
        ("m4a", ["-codec:a", "aac"]),
        ("flac", ["-codec:a", "flac"]),
        ("ogg", ["-codec:a", "libvorbis"]),
        ("opus", ["-codec:a", "libopus"]),
        ("wav", ["-codec:a", "pcm_s16le"]),
    ]:
        path = out / f"silent.{fmt}"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", "1", *codec, str(path)],
            check=True, capture_output=True,
        )
        made[fmt] = path
    return made
```

- [ ] **Step 6: Commit the tiny fixture inputs.** Generate two committed few-KB real audio files used as fetch/convert **inputs** (so the fake fetcher can hand back a genuine media file and convert tests have real content). Run once locally with ffmpeg and `git add` the results:
```bash
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 1 -codec:a aac \
  packages/core/tests/download/fixtures/tiny.m4a
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 1 -codec:a libopus \
  packages/core/tests/download/fixtures/tiny.opus
```
Verify both are < ~50 KB.

- [ ] **Step 7: GREEN + gates.** `uv run pytest packages/core/tests/download -v`; then `make check`.

- [ ] **Step 8: Commit**
```bash
git add packages/core pyproject.toml uv.lock
git commit -m "feat(core/download): scaffold, yt-dlp+mutagen deps, offline test policy, fetch/post error subclasses"
```

---

### Task 2: Contract change — amend `Track`/`AlbumRef` for full VARS + tag parity

**Files:**
- Modify: `packages/core/src/spotdl_core/model/entities.py`
- Modify: `packages/core/tests/model/test_entities.py` (assert the new optional fields)

**Interfaces (CONTRACT):** v4's Song carries fields the v5 `Track`/`AlbumRef` did not model (Plan 1 kept the model minimal). Full VARS/tag parity requires a small, **additive, backwards-compatible** set of optional fields (all default `None`, so every existing Plan 1/2/3 construction stays valid). This mirrors Plan 3 Task 2's precedent (amending `FeatureVector` in a dedicated contract-change task).

Add to **`AlbumRef`**:
```python
    disc_count: int | None = None
```
Add to **`Track`** (after `year`):
```python
    date: str | None = None            # original release date, ISO "YYYY-MM-DD" (v4 {original-date})
    publisher: str | None = None       # label / encoded-by (v4 {publisher})
    copyright_text: str | None = None  # album copyright line
    popularity: int | None = None      # 0–100 popularity prior (POPM rating / m4a rtng source)
    cover_url: str | None = None       # track-level cover (retain-track-cover); falls back to album.cover_url
```

Rationale for each (v4 source → v5 field): `{original-date}`→`Track.date`; `{publisher}`→`Track.publisher`; `{disc-count}`→`AlbumRef.disc_count`; POPM/`rtng`/WAV popularity comment→`Track.popularity`; `TCOP`/album copyright→`Track.copyright_text`; per-track cover art & `retain-track-cover`→`Track.cover_url` (else `AlbumRef.cover_url`). `{list-name}`/`{list-position}`/`{list-length}` are **not** track fields — they are download-time playlist context and live on `DownloadRequest` (Task 3). `{track-id}`→`Track.provider_id`. The audio **source URL** (`{comment}`/download_url) is `AudioCandidate.url`; the **track URL** (`WOAS`) is supplied via `DownloadRequest.track_url` (Task 3).

- [ ] **Step 1:** Add failing assertions: a `Track` built with `date="2020-05-01", publisher="Label", popularity=73, copyright_text="© 2020", cover_url="http://x/c.jpg"` round-trips; an `AlbumRef(name="A", disc_count=2)` round-trips; a `Track` built with none of the new fields still validates (defaults `None`). RED.
- [ ] **Step 2:** Add the fields. Keep models frozen. `make check` green (Plans 1–3 tests unaffected since all new fields are optional; mypy strict clean).
- [ ] **Step 3: Commit**
```bash
git add packages/core/src/spotdl_core/model packages/core/tests/model/test_entities.py
git commit -m "feat(core/model): additive Track/AlbumRef fields for full download VARS + tag parity"
```

---

### Task 3: `core.download.context` — request/config/context/outcome models, enums, progress, Step type

**Files:**
- Create: `packages/core/src/spotdl_core/download/context.py`
- Modify: `packages/core/src/spotdl_core/download/__init__.py`
- Create: `packages/core/tests/download/test_context.py`

**Interfaces produced (the spine every step and Plan 7 consume):**

**Contract vs freedom:** Every public name, field, and default below is a **CONTRACT** — Plan 7 builds `DownloadRequest`s from server settings and reads `DownloadOutcome`, and Tasks 4–9 read/write `DownloadContext`. Implementers may add private helpers but must not rename or re-type these.

- [ ] **Step 1: Write `test_context.py`** asserting: default request round-trips; enums have the exact string values below; `DownloadContext.updated(...)` returns a new frozen context with the field changed and everything else preserved (immutability); `DownloadOutcome` factory helpers set `status`/`skip_reason`/`failed_step` correctly; a `ProgressCallback` fake is invokable with a `ProgressEvent`. RED.

- [ ] **Step 2: Implement `context.py`** — **CONTRACT (match exactly):**
```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from spotdl_core.model import AudioCandidate, Lyrics, Track


# --- enums ----------------------------------------------------------------

class OutputFormat(StrEnum):
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    OPUS = "opus"
    WAV = "wav"


class OverwriteMode(StrEnum):
    SKIP = "skip"          # keep existing file, do nothing
    FORCE = "force"        # re-download, replacing existing
    METADATA = "metadata"  # keep audio, re-embed metadata only


class RestrictMode(StrEnum):
    NONE = "none"      # no restriction (sanitize only)
    ASCII = "ascii"    # NFKD -> ASCII transliteration (v4 restrict="ascii", non-strict)
    STRICT = "strict"  # yt-dlp strict filename sanitization (v4 restrict="strict")


class SkipReason(StrEnum):
    ALREADY_EXISTS = "already_exists"      # file present, overwrite=skip
    SKIP_FILE = "skip_file"                # ".skip" sidecar present, respect_skip_file
    IN_ARCHIVE = "in_archive"              # track url in the archive set
    EXPLICIT_FILTERED = "explicit_filtered"  # explicit track, skip_explicit


class OutcomeStatus(StrEnum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    FAILED = "failed"


class ProgressPhase(StrEnum):
    PLAN = "plan"
    FETCH = "fetch"
    CONVERT = "convert"
    EMBED = "embed"
    POST = "post"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


# Bitrate is a validated string: "auto" (derive from source), "disable" (no
# -b:a/-q:a and enables the move-not-reencode fast path), an integer string
# like "320" -> VBR quality (-q:a), or "<n>k"/"<n>K" -> CBR (-b:a). See Task 6.
Bitrate = str
BITRATE_AUTO: Bitrate = "auto"
BITRATE_DISABLE: Bitrate = "disable"


# --- progress -------------------------------------------------------------

class ProgressEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: ProgressPhase
    percent: int | None = None      # 0–100 within the phase, when known
    message: str | None = None


# Consumed later by the server WS relay (Plan 7) and the CLI progress bars
# (Plan 8). Synchronous, best-effort, must never raise into the pipeline.
ProgressCallback = Callable[[ProgressEvent], None]


# --- request / config -----------------------------------------------------

class DownloadRequest(BaseModel):
    """Everything about downloading ONE track. Immutable; built by the caller
    (server, Plan 7) from resolved metadata + the chosen match candidate."""

    model_config = ConfigDict(frozen=True)

    track: Track
    candidate: AudioCandidate            # chosen audio source (head of matching.match())
    output_template: str                 # v4 `output`; empty string -> default template
    output_format: OutputFormat = OutputFormat.MP3
    bitrate: Bitrate = BITRATE_AUTO
    overwrite: OverwriteMode = OverwriteMode.SKIP
    restrict: RestrictMode = RestrictMode.NONE
    max_filename_length: int | None = None

    # metadata / tagging
    lyrics: Lyrics | None = None
    embed_lyrics: bool = True
    skip_album_art: bool = False
    retain_track_cover: bool = False
    id3_separator: str = "/"
    track_url: str | None = None         # canonical track URL for WOAS tag (spotify link)

    # post-processing
    generate_lrc: bool = False
    sponsor_block: bool = False

    # skip / overwrite / archive inputs (evaluated purely in Task 4)
    respect_skip_file: bool = False
    create_skip_file: bool = False
    skip_explicit: bool = False
    archive: frozenset[str] = frozenset()   # already-downloaded track URLs
    known_paths: tuple[Path, ...] = ()      # duplicate files found by a prior scan
    detect_formats: tuple[OutputFormat, ...] = ()  # extra extensions to treat as "exists"

    # playlist context for {list-*} template vars and m3u
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None


@dataclass(frozen=True)
class DownloadConfig:
    """Process-level I/O configuration, injected once into the engine. Not
    per-track. ffmpeg is a binary located here, never a pip dependency."""

    output_dir: Path
    temp_dir: Path
    ffmpeg_path: str = "ffmpeg"                 # resolved on PATH by default
    cookie_file: Path | None = None            # yt-dlp cookiefile
    proxy: str | None = None                   # http(s) proxy for yt-dlp + cover fetch
    ytdlp_args: tuple[str, ...] = ()           # passthrough to yt-dlp (already tokenized)
    ffmpeg_args: tuple[str, ...] = ()          # passthrough appended to the ffmpeg command


# --- threaded pipeline context --------------------------------------------

class DownloadContext(BaseModel):
    """Frozen state threaded through the pipeline. Each step returns a new
    context via `.updated(...)`. `arbitrary_types_allowed` covers `Path` and
    the raw yt-dlp info dict."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: DownloadRequest
    output_path: Path | None = None      # set by the plan step (final destination)
    temp_path: Path | None = None        # fetched audio in the temp dir
    final_path: Path | None = None       # after convert/move -> equals output_path on success
    source_url: str | None = None        # resolved audio download URL (candidate.url)
    source_abr: float | None = None      # audio bitrate reported by the fetcher (for "auto")
    source_info: dict[str, Any] | None = None  # raw yt-dlp info (SponsorBlock input)
    skip_reason: SkipReason | None = None

    def updated(self, **changes: Any) -> "DownloadContext":
        return self.model_copy(update=changes)


# A pipeline step: async, typed context in -> typed context out. Concrete
# steps are small callables (usually classes capturing an injected
# collaborator) implementing this signature. The engine composes them.
Step = Callable[[DownloadContext], "Awaitable[DownloadContext]"]  # noqa: F821


# --- outcome --------------------------------------------------------------

class DownloadOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    status: OutcomeStatus
    track: Track
    path: Path | None = None
    skip_reason: SkipReason | None = None
    failed_step: str | None = None     # "plan"|"fetch"|"convert"|"embed"|"post" (from DownloadFailed.step)
    error: str | None = None           # human-readable message for the batch error summary

    @classmethod
    def downloaded(cls, track: Track, path: Path) -> "DownloadOutcome":
        return cls(status=OutcomeStatus.DOWNLOADED, track=track, path=path)

    @classmethod
    def skipped(cls, track: Track, reason: SkipReason, path: Path | None = None) -> "DownloadOutcome":
        return cls(status=OutcomeStatus.SKIPPED, track=track, skip_reason=reason, path=path)

    @classmethod
    def failed(cls, track: Track, *, step: str, error: str) -> "DownloadOutcome":
        return cls(status=OutcomeStatus.FAILED, track=track, failed_step=step, error=error)
```
Fix the `Step` alias import (`from collections.abc import Awaitable`) — shown inline above for readability; implement it as a proper import at the top.

- [ ] **Step 3: GREEN + gates.** Update `download/__init__.py` `__all__` to export the models, enums, `ProgressEvent`, `ProgressCallback`, `Step`, `Bitrate` constants. `make check` green; mypy strict clean.

- [ ] **Step 4: Commit**
```bash
git commit -am "feat(core/download): context — request/config/context/outcome models, enums, progress, step type"
```

---

### Task 4: `core.download.paths` — templating (all VARS), restrict modes, length limits, pure skip/archive logic

**Files:**
- Create: `packages/core/src/spotdl_core/download/paths.py`
- Create: `packages/core/tests/download/test_paths.py`

**References (port behaviour, rewrite against v5 model):** `spotdl/utils/formatter.py` (`VARS`, `format_query`, `create_file_name`, `sanitize_string`, `restrict_filename`, `smart_split`, `create_path_object`), and the skip/overwrite/archive branches of `spotdl/download/downloader.py:search_and_download` (lines ~468–643) and `download_multiple_songs` (archive filter ~288–329).

**Contract vs freedom:** The **template-variable table below is a CONTRACT** (documented user-facing feature) — every variable must render from the named source. Function signatures are contract; regex/sanitization internals are implementation but must reproduce v4 behaviour (test-locked).

**Template-variable table (port of v4 `VARS`, complete — variable → v5 source):**

| Template var | v5 source expression | Notes (v4 parity) |
|---|---|---|
| `{title}` | `track.name` | |
| `{artists}` | `", ".join(track.artists)` | short mode drops artists already in the slugified title, main artist re-inserted |
| `{artist}` | `track.main_artist` | |
| `{album}` | `track.album.name if track.album else ""` | |
| `{album-artist}` | `track.album.album_artist if track.album else ""` | |
| `{genre}` | `track.genres[0] if track.genres else ""` | first genre only |
| `{disc-number}` | `track.disc_number` | |
| `{disc-count}` | `track.album.disc_count if track.album else ""` | (Task 2 field) |
| `{duration}` | `round(track.duration_ms / 1000)` | seconds |
| `{year}` | `track.year` | |
| `{original-date}` | `track.date` | ISO date (Task 2 field) |
| `{track-number}` | `f"{track.track_number:02d}"` when set else `""` | zero-padded to 2 |
| `{tracks-count}` | `track.album.track_count if track.album else ""` | |
| `{isrc}` | `track.isrc` | |
| `{track-id}` | `track.provider_id` | |
| `{publisher}` | `track.publisher` | (Task 2 field) |
| `{list-length}` | `request.list_length` | playlist context |
| `{list-position}` | `str(list_position).zfill(len(str(list_length)))` | zero-padded to list width |
| `{list-name}` | `request.list_name` | |
| `{output-ext}` | `request.output_format.value` | required if template contains it |

`VARS: tuple[str, ...]` lists all 20 tokens above (contract; used to detect "template has no variables → append default").

- [ ] **Step 1: Write `test_paths.py`.** Cover:
  - `render_template`: every VARS token substituted from a fully-populated `Track`+`AlbumRef`+request-list-context; missing `album`/list values render empty; `{output-ext}` present without an ext raises `ValueError`; `None`-valued `{list-*}` collapse `//`→`/` (v4 `format_query`).
  - short-mode dedup: title "Artist - Song" with artists `("Artist",)` → `{artists}` renders just the main artist.
  - `build_output_path`: `""` template → `{artists} - {title}.{output-ext}`; template with no vars + non-empty → `<template>/{artists} - {title}.{output-ext}`; trailing-slash template appends default; template not ending in `.{output-ext}` gets it appended.
  - restrict: `RestrictMode.STRICT` → yt-dlp strict sanitize + `_-_`→`-`; `RestrictMode.ASCII` → NFKD ASCII; empty result → `_`; `NONE` → unchanged (sanitize only).
  - length: with `max_filename_length` small, `build_output_path` falls back to short mode, then to shortened artist/title via `smart_split`, then to `{artist} - {title}` template; a still-too-long default template raises `ValueError` (v4 behaviour).
  - `smart_split`: separators `["-", ",", " ", ""]`; returns the longest prefix ≤ max at the first separator that fits; hard-truncates when none fit.
  - `plan_skip` PURE decisions (see contract below): skip-file present + `respect_skip_file`; existing file + `overwrite=SKIP`; url in `archive`; explicit + `skip_explicit`; returns `None` when nothing applies.
  - `find_duplicates`: `known_paths` and `detect_formats` extension variants that exist are returned; the exact `output_path` is excluded.
  - archive round-trip: `load_archive`/`save_archive` read/write one-URL-per-line, sorted on save.
  RED.

- [ ] **Step 2: Implement `paths.py`.** Public surface (CONTRACT):
```python
VARS: tuple[str, ...]

def render_template(track, request, template, *, output_ext, short=False) -> str: ...
    # port format_query: substitute all VARS, sanitize each value, collapse // when
    # list-* is None; return the filled string.

def build_output_path(request, config, *, short=False) -> Path: ...
    # port create_file_name: normalize template (default/append rules), render,
    # create_path_object sanitize, enforce max_filename_length via short mode +
    # smart_split fallback (recursive, terminating at "{artist} - {title}"),
    # apply restrict mode; return an ABSOLUTE path under config.output_dir.

def restrict_filename(path: Path, mode: RestrictMode) -> Path: ...  # STRICT/ASCII/NONE

def smart_split(string: str, max_length: int, separators: list[str] | None = None) -> str: ...

def find_duplicates(output_path, known_paths, detect_formats) -> list[Path]: ...

def plan_skip(request, output_path, duplicates) -> SkipReason | None: ...
    # PURE: no filesystem writes. Reads existence of output_path / ".skip" sidecar,
    # membership in request.archive, explicit flag. Returns the first matching
    # SkipReason or None. (overwrite=METADATA is NOT a skip — handled by the engine.)

def archive_should_add(outcome_ok: bool, add_unavailable: bool) -> bool: ...  # v4 archive add rule

def load_archive(path: Path) -> frozenset[str]: ...   # {} if file absent
def save_archive(path: Path, urls: frozenset[str]) -> None: ...  # sorted, one per line
```
Implementation notes: keep `render_template`/`build_output_path`/`smart_split`/`restrict_filename` **pure** (no I/O) except `find_duplicates`/`plan_skip`/`load_archive`/`save_archive` which touch the filesystem via `Path.exists()`/read/write only. Port v4's `sanitize_string` (strip `/?\\*|<>`, `"`→`'`, `:`→`-`) and `create_path_object` per-part regex. The v4 `slugify`/`pykakasi` japanese handling used by short-mode dedup is available from Plan 3's `core.matching.text` — **import and reuse it** (do not re-port) so slugify semantics stay single-sourced.

- [ ] **Step 3: GREEN + gates.** `make check` green.

- [ ] **Step 4: Commit**
```bash
git commit -am "feat(core/download): paths — full VARS templating, restrict modes, length limits, pure skip/archive logic"
```

---

### Task 5: `core.download.fetch` — yt-dlp audio fetch behind an injectable seam

**Files:**
- Create: `packages/core/src/spotdl_core/download/fetch.py`
- Create: `packages/core/tests/download/test_fetch.py`

**References:** `spotdl/providers/audio/base.py` (`__init__` yt-dlp options, format selection per output format, cookiefile, `args_to_ytdlp_options`, `get_download_metadata`) and `search_and_download` fetch block (downloader.py ~647–697).

**Contract vs freedom:** `Fetcher`, `FetchResult`, and `FetchStep` are a **CONTRACT** (the offline seam + Plan 7 wiring). The concrete `YtDlpFetcher` internals (option dict, extractor args) are implementation.

- [ ] **Step 1: Write `test_fetch.py`** (offline — no yt-dlp network):
  - `FakeFetcher` returns a `FetchResult` pointing at a copy of `fixtures/tiny.m4a` in a `tmp_path` temp dir. `FetchStep(FakeFetcher()).__call__(ctx)` returns a context with `temp_path` set to an existing file, `source_url`, `source_abr`, `source_info` populated.
  - a `FakeFetcher` that raises → `FetchStep` wraps it as `AudioFetchFailed` (step="fetch").
  - `ytdl_format_for(OutputFormat.M4A) == "bestaudio[ext=m4a]/bestaudio/best"`, `OPUS == "bestaudio[ext=webm]/bestaudio/best"`, others == `"bestaudio"` (pure function, unit-tested without yt-dlp).
  - `build_ytdlp_options(config, output_format, temp_dir)` includes `cookiefile`, `outtmpl` under temp_dir, `format` per above, and merges `config.ytdlp_args` (parsed via yt-dlp's `parse_options`, lazily imported — mark this one test `requires_ytdlp`? No: `parse_options` is import-only, no network, so it runs in the default suite). Proxy from `config.proxy` becomes the `proxy` option.
  - progress: `FetchStep` installs a yt-dlp progress hook adapter that maps yt-dlp status dicts to `ProgressEvent(phase=FETCH, percent=...)` and calls the injected `ProgressCallback`; unit-test the adapter directly with a synthetic `{"status":"downloading","downloaded_bytes":..,"total_bytes":..}`.
  RED.

- [ ] **Step 2: Implement `fetch.py`** — **CONTRACT:**
```python
class FetchResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    path: Path                 # downloaded file in the temp dir
    ext: str                   # container extension without dot (e.g. "webm", "m4a")
    source_url: str            # the URL yt-dlp actually fetched
    abr: float | None = None   # average audio bitrate reported by yt-dlp (kbps)
    info: dict[str, Any] = {}  # raw yt-dlp info dict (SponsorBlock input)


class Fetcher(Protocol):
    async def fetch(
        self, candidate: AudioCandidate, *, output_format: OutputFormat,
        temp_dir: Path, on_progress: ProgressCallback | None = None,
    ) -> FetchResult: ...


def ytdl_format_for(output_format: OutputFormat) -> str: ...

class YtDlpFetcher:
    """Concrete Fetcher backed by yt-dlp (lazily imported in __init__/fetch)."""
    def __init__(self, config: DownloadConfig) -> None: ...
    async def fetch(self, candidate, *, output_format, temp_dir, on_progress=None) -> FetchResult:
        # runs the blocking YoutubeDL.extract_info(url, download=True) via asyncio.to_thread;
        # temp file = temp_dir / f"{info['id']}.{info['ext']}"; abr = info.get("abr");
        # raises AudioFetchFailed on any yt-dlp error or missing metadata.

class FetchStep:
    def __init__(self, fetcher: Fetcher, on_progress: ProgressCallback | None = None) -> None: ...
    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        # calls fetcher.fetch(request.candidate, ...); returns ctx.updated(
        #   temp_path=result.path, source_url=result.source_url,
        #   source_abr=result.abr, source_info=result.info)
        # wraps any non-AudioFetchFailed exception into AudioFetchFailed.
```
Implementation notes: cookiefile/proxy/passthrough all flow from `DownloadConfig`. Port `args_to_ytdlp_options` semantics (v4 formatter) for merging `config.ytdlp_args` over defaults; keep the actual `yt_dlp` import lazy so `import spotdl_core.download.fetch` works without yt-dlp fully initialized and the default suite never touches the network.

- [ ] **Step 3: GREEN + gates.** `make check` green.

- [ ] **Step 4: Commit**
```bash
git commit -am "feat(core/download): fetch — yt-dlp fetcher behind an injectable seam, format selection, progress hook"
```

---

### Task 6: `core.download.convert` — ffmpeg conversion, bitrate modes, move-fast-path (+ CI ffmpeg)

**Files:**
- Create: `packages/core/src/spotdl_core/download/convert.py`
- Create: `packages/core/tests/download/test_convert.py`
- Modify: `.github/workflows/ci.yml` (install ffmpeg on the python job)

**References:** `spotdl/utils/ffmpeg.py` (`FFMPEG_FORMATS`, `convert`, argument building, bitrate handling, error capture) and downloader.py convert/move block (~699–782).

**Contract vs freedom:** The **`FFMPEG_CODECS` table and the move-fast-path + bitrate-resolution rules are a CONTRACT** (output-format parity). Progress parsing and subprocess plumbing are implementation.

**Codec table (port of v4 `FFMPEG_FORMATS`):**

| OutputFormat | ffmpeg codec args |
|---|---|
| `mp3` | `["-codec:a", "libmp3lame"]` |
| `flac` | `["-codec:a", "flac", "-sample_fmt", "s16"]` |
| `ogg` | `["-codec:a", "libvorbis"]` |
| `opus` | `["-codec:a", "libopus"]` |
| `m4a` | `["-codec:a", "aac"]` |
| `wav` | `["-codec:a", "pcm_s16le"]` |

**Special-case codec selection (port of v4 `convert`):**
- output `opus` and input ext ≠ `webm` → force `["-c:a", "libopus"]`.
- (`output opus` & input `webm`) **or** (`output m4a` & input `m4a`), **and** no bitrate/ffmpeg_args → `["-vn", "-c:a", "copy"]` (stream copy).
- otherwise → the `FFMPEG_CODECS[output_format]` row.
- base args always include: `-nostdin -y -i <in> -movflags +faststart` then codec, then bitrate, then passthrough, then `<out>`.

**Bitrate resolution (`resolve_bitrate(request_bitrate, source_abr) -> str | None`):**
- `"auto"` → `f"{int(source_abr)}k"` if `source_abr` else `"128k"`.
- `"disable"` → `None` (no `-b:a`/`-q:a`).
- all-digits (e.g. `"0".."9"`, `"320"`) → applied as `["-q:a", value]` (VBR).
- else (e.g. `"320k"`) → `["-b:a", value]` (CBR).

**Move-fast-path (`should_move(input_ext, output_format, bitrate) -> bool`):** `True` when `bitrate in {"auto","disable"}` **and** `input_ext == output_format.value`. (v4 additionally suppressed the fast path for the piped provider unless bitrate was "disable"; v5's fetcher is provider-agnostic here, so we key purely on ext+bitrate. Documented deviation.)

- [ ] **Step 1: Write `test_convert.py`:**
  - PURE (no ffmpeg): `resolve_bitrate` for all four branches; `should_move` truth table; `build_ffmpeg_command(...)` produces the exact argv for representative cases (mp3 default+auto bitrate; opus from webm → copy; m4a from m4a no-bitrate → copy; flac with `-sample_fmt s16`; CBR `320k` → `-b:a 320k`; VBR `0` → `-q:a 0`; passthrough `ffmpeg_args` appended before output).
  - `requires_ffmpeg`: `ConvertStep` on a copy of `fixtures/tiny.m4a` → `output_format=OutputFormat.mp3` produces an mp3 at `output_path`, `ctx.final_path == output_path`, temp file removed.
  - `requires_ffmpeg`: move-fast-path — input `.m4a`, output `m4a`, bitrate `disable` → file is **moved** (byte-identical, no re-encode); assert via content hash equality with the source.
  - failure: a bogus ffmpeg path (`ffmpeg_path="/nonexistent/ffmpeg"`) or a corrupt input → `ConversionFailed` whose message contains captured stderr; the partial output file is removed.
  RED.

- [ ] **Step 2: Implement `convert.py`** — **CONTRACT:**
```python
FFMPEG_CODECS: dict[OutputFormat, list[str]]  # the table above

def resolve_bitrate(bitrate: Bitrate, source_abr: float | None) -> str | None: ...
def should_move(input_ext: str, output_format: OutputFormat, bitrate: Bitrate) -> bool: ...
def build_ffmpeg_command(
    ffmpeg: str, input_file: Path, input_ext: str, output_file: Path,
    output_format: OutputFormat, bitrate: str | None, ffmpeg_args: tuple[str, ...],
) -> list[str]: ...

class ConvertStep:
    def __init__(self, config: DownloadConfig, on_progress: ProgressCallback | None = None) -> None: ...
    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        # if should_move(...): shutil.move(temp_path, output_path)
        # else: resolve bitrate, build command, run ffmpeg via asyncio.to_thread over
        #   subprocess; parse -progress stream -> ProgressEvent(phase=CONVERT); on
        #   non-zero returncode capture stdout+stderr and raise ConversionFailed(<stderr>),
        #   deleting any partial output_path first.
        # always remove temp_path afterwards; return ctx.updated(final_path=output_path).
```
Implementation notes: `output_path` must already exist as a parent dir — `ConvertStep` calls `output_path.parent.mkdir(parents=True, exist_ok=True)`. ffmpeg is invoked as `[config.ffmpeg_path, *args]`; never shell out. Capture stderr into the `ConversionFailed` message (v4 wrote a sidecar error file — v5 puts the stderr in the exception; the server/CLI decides on persistence). Port v4's `-progress -` / `-nostats` / DUR/TIME regex for percent, but degrade gracefully (no progress) when the callback is `None`.

- [ ] **Step 3: Edit `.github/workflows/ci.yml`.** In the existing `python` job (Plan 1, Task 9), add an ffmpeg install step **before** `uv run pytest` so convert/tag tests run (not skip) in CI:
```yaml
      - uses: FedericoCarboni/setup-ffmpeg@v3
        with:
          ffmpeg-version: release
```
Local dev without ffmpeg still passes `make check` (those tests auto-skip via `requires_ffmpeg`/`silent_audio`).

- [ ] **Step 4: GREEN + gates.** `make check` green (ffmpeg present → convert tests run; absent → skip). Confirm the skip path locally by temporarily hiding ffmpeg from `PATH` if feasible.

- [ ] **Step 5: Commit**
```bash
git add packages/core .github/workflows/ci.yml
git commit -m "feat(core/download): convert — ffmpeg codec table, bitrate modes, move-fast-path, stderr capture; CI installs ffmpeg"
```

---

### Task 7: `core.download.tags` — mutagen embedding for all six containers

**Files:**
- Create: `packages/core/src/spotdl_core/download/tags.py`
- Create: `packages/core/tests/download/test_tags.py`

**References:** `spotdl/utils/metadata.py` in full (`M4A_TAG_PRESET`, `MP3_TAG_PRESET`, vorbis-comment keys for flac/ogg/opus, `embed_metadata`, `embed_cover`, `embed_lyrics`, `embed_wav_file`, `LRC_REGEX`).

**Contract vs freedom:** The **tag-preset tables per container are a CONTRACT** (metadata parity; other tools read these). Cover fetching is behind an injectable `CoverDownloader` seam (offline default). The `EmbedStep` signature is contract.

**MP3 (ID3) preset (port of `MP3_TAG_PRESET`):**

| logical | ID3 frame |
|---|---|
| album | `TALB` |
| artist | `TPE1` |
| date | `TDRC` |
| title | `TIT2` |
| year | `TDRC`/`TYER` |
| comment (source/download URL) | `COMM` |
| group | `TIT1` |
| writer | `TEXT` |
| genre | `TCON` |
| tracknumber | `TRCK` (`n/total`) |
| albumartist | `TPE2` |
| discnumber | `TPOS` (`n/total`) |
| compilation | `TCMP` |
| albumart | `APIC` (type 3, `image/jpeg`, desc "Cover") |
| encodedby | `TENC` |
| copyright | `TCOP` |
| tempo | `TBPM` |
| lyrics (plain) | `USLT` (UTF-8) |
| lyrics (synced) | `SYLT` (encoding 3, format 2, type 1) + `USLT` cleaned |
| track url | `WOAS` |
| isrc | `TSRC` |
| popularity | `POPM` (rating = `int(popularity*255/100)`) |

**M4A (MP4 atoms) preset (port of `M4A_TAG_PRESET`):** `album ©alb`, `artist ©ART`, `date/year ©day`, `title ©nam`, `comment ©cmt`, `group ©grp`, `writer ©wrt`, `genre ©gen`, `tracknumber/trackcount trkn` (tuple), `albumartist aART`, `discnumber/disccount disk` (tuple), `compilation cpil`, `albumart covr` (`MP4Cover`, JPEG), `encodedby ©too`, `copyright cprt`, `tempo tmpo`, `lyrics ©lyr`, `explicit rtng` (4 explicit / 2 clean), `woas ----:spotdl:WOAS` (utf-8 bytes), `isrc ----:spotdl:ISRC`.

**FLAC / OGG / OPUS (Vorbis comments):** lowercase keys — `artist`, `albumartist`, `title`, `date`, `encodedby`, `album`, `genre` (title-cased first genre), `copyright`, `discnumber`, `disctotal`, `tracktotal`, `tracknumber`, `woas` (track url), `isrc`; cover via FLAC `Picture` (`add_picture`, clearing existing) or OGG/OPUS base64 `metadata_block_picture`; plain lyrics under `lyrics`.

**WAV (ID3 in RIFF):** `TIT2`, `TPE1`, `TALB`, `TCOM` (publisher), `TCON` (genres), `TDRC` (date), `TRCK` (`n/total`), `WOAS`, `TSRC`; `COMM` for source URL; `TCOP` copyright; `COMM` "Spotify Popularity: N"; `APIC` cover; `USLT`/`SYLT` lyrics — port `embed_wav_file`.

**Lyrics selection:** if `request.embed_lyrics` and `request.lyrics` present — detect LRC vs plain via `LRC_REGEX` on the first 5 lines (LRC timestamps `[mm:ss.xx]`); LRC → embed synced (`SYLT`+cleaned `USLT` for mp3/wav, plain text for others); plain → `USLT`/`lyrics` tag. `Lyrics.kind` (SYNCED/PLAIN) is a hint but the regex detection is authoritative (v4 parity).

**Source/track URLs:** `WOAS`/`woas` = `request.track_url` (canonical track link); `comment`/`COMM`/`download_url` = `request.candidate.url` (audio source). Cover URL = `request.track.cover_url or request.track.album.cover_url` (retain-track-cover honoured by preferring track cover).

- [ ] **Step 1: Write `test_tags.py`** (uses the `silent_audio` session fixture → real files, real mutagen; `requires_ffmpeg` implicit via that fixture):
  - For **each** of mp3/m4a/flac/ogg/opus/wav: embed a fully-populated `Track` then re-open with mutagen and assert title/artist/album/albumartist/genre/tracknumber/discnumber/isrc/date and the source-URL/track-URL land in the right frame/atom/key.
  - mp3: `POPM` rating derived from popularity; `SYLT` present when lyrics are LRC; `USLT` present when lyrics are plain.
  - cover: with an injected `FakeCoverDownloader` returning committed JPEG bytes, assert `APIC`/`covr`/`Picture`/`metadata_block_picture` is set; with `skip_album_art=True` no cover embedded; cover-download failure is swallowed (tags still saved).
  - unknown/corrupt file → `MetadataEmbedFailed`.
  RED.

- [ ] **Step 2: Implement `tags.py`** — **CONTRACT surface:**
```python
MP3_TAG_PRESET: dict[str, str]
M4A_TAG_PRESET: dict[str, str]
LRC_REGEX: re.Pattern[str]

class CoverDownloader(Protocol):
    def fetch(self, url: str) -> bytes | None: ...   # None on any failure (never raises)

class HttpCoverDownloader:
    def __init__(self, proxy: str | None = None, timeout: float = 10.0) -> None: ...
    def fetch(self, url: str) -> bytes | None: ...   # uses stdlib urllib or httpx; swallows errors

def embed_metadata(output_file: Path, request: DownloadRequest, cover: CoverDownloader) -> None:
    # dispatch by output_file.suffix; raise MetadataEmbedFailed on any mutagen error.

class EmbedStep:
    def __init__(self, cover: CoverDownloader, on_progress: ProgressCallback | None = None) -> None: ...
    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        # runs embed_metadata via asyncio.to_thread on ctx.final_path; emits
        # ProgressEvent(phase=EMBED); returns ctx unchanged (or with a flag). Wraps
        # non-MetadataEmbedFailed exceptions into MetadataEmbedFailed.
```
Implementation notes: port the exact mutagen call sequences from `metadata.py` (mp3 double-save with `v2_version=3` / `v23_sep`, m4a tuple atoms, vorbis picture base64, wav RIFF ID3). `embed_cover` uses the injected `CoverDownloader` instead of a direct `requests.get` (that is the offline seam + proxy hook). Guard every "not always present" field with a `None` check.

- [ ] **Step 3: GREEN + gates.** `make check` green.

- [ ] **Step 4: Commit**
```bash
git commit -am "feat(core/download): tags — mutagen presets for mp3/m4a/flac/ogg/opus/wav, cover seam, plain+synced lyrics, ISRC, source URL"
```

---

### Task 8: `core.download.post` — .lrc, m3u, archive update, SponsorBlock

**Files:**
- Create: `packages/core/src/spotdl_core/download/post.py`
- Create: `packages/core/tests/download/test_post.py`

**References:** `spotdl/utils/lrc.py` (`generate_lrc`, `remove_lrc`), `spotdl/utils/m3u.py` (`create_m3u_content`, `gen_m3u_files`, `{list}`/`{list[..]}` templating, playlist numbering, detect_formats), archive add rule (downloader.py ~319–329), SponsorBlock block (downloader.py ~792–823 using `SponsorBlockPP`/`ModifyChaptersPP`).

**Contract vs freedom:** The `{list}` m3u templating semantics and the `SPONSOR_BLOCK_CATEGORIES` set are contract (feature parity). The lyrics-search and SponsorBlock external calls are behind injectable seams (offline default). Note the m3u helpers operate over **many** tracks, so they are module-level utilities the orchestrator (Plan 7) calls — not per-track pipeline steps.

- [ ] **Step 1: Write `test_post.py`:**
  - `.lrc`: with a synced `Lyrics` on the request, `LrcStep` (or `generate_lrc`) writes `<output>.lrc` containing the LRC text; with plain lyrics and an injected `FakeSyncedLyricsSearch` returning `None`, no file is written; the `syncedlyrics` import is lazy (patched out in the test).
  - m3u (pure, no I/O for content): `create_m3u_content(entries, template, output_format)` yields `#EXTM3U`, per-track `#EXTINF:<dur>,<album-artist> - <title>` and the rendered relative path; `detect_formats` picks an existing extension variant when present.
  - `gen_m3u_files`: default filename `{list[0]}.m3u8`; `{list}` token → one file per distinct `list_name`; `{list[0]}` indexed form → single file; a `{list`-containing name with no lists logs a warning and writes nothing.
  - archive: `archive_update(current, results)` adds URLs for successes (and unavailable when `add_unavailable`); `SPONSOR_BLOCK_CATEGORIES` has the 8 v4 keys.
  - SponsorBlock: with an injected `FakeSponsorBlock` returning a modified file, the step swaps `final_path`; when yt-dlp postprocessors are unavailable the step degrades (no-op) rather than failing the download — but a genuine SponsorBlock error raises `PostProcessingFailed`.
  RED.

- [ ] **Step 2: Implement `post.py`.** Surface:
```python
SPONSOR_BLOCK_CATEGORIES: dict[str, str]   # the 8 v4 categories

# --- lrc ---
class SyncedLyricsSearch(Protocol):
    def search(self, query: str) -> str | None: ...
class SyncedLyricsLibrary:  # lazy `syncedlyrics` import; None if extra not installed
    def search(self, query: str) -> str | None: ...
def generate_lrc(request, output_file, search: SyncedLyricsSearch) -> Path | None: ...
    # prefer request.lyrics if it has translation/synced content; else search(display_name);
    # write <output>.lrc via syncedlyrics' saver or a small LRC writer; return the path or None.

# --- m3u (batch utility, called by the orchestrator) ---
class M3uEntry(BaseModel): track: Track; path: Path; list_name: str | None
def create_m3u_content(entries, template, output_format, *, restrict=RestrictMode.NONE,
                       detect_formats=()) -> str: ...
def gen_m3u_files(entries, file_name, template, output_format, *, restrict, detect_formats) -> list[Path]: ...

# --- archive ---
def archive_update(current: frozenset[str], results: Iterable[tuple[str, bool]],
                   *, add_unavailable: bool) -> frozenset[str]: ...

# --- sponsorblock ---
class SponsorBlock(Protocol):
    def process(self, info: dict[str, Any], audio_path: Path) -> Path: ...
class YtDlpSponsorBlock:  # lazy import of SponsorBlockPP/ModifyChaptersPP
    def process(self, info, audio_path) -> Path: ...
class SponsorBlockStep:
    def __init__(self, sponsor_block: SponsorBlock, on_progress=None) -> None: ...
    async def __call__(self, ctx: DownloadContext) -> DownloadContext: ...  # uses ctx.source_info
```
Implementation notes: reuse `paths.render_template`/`build_output_path` for m3u path rendering (single-source templating). `.lrc` generation prefers request lyrics, then the injected search; keep `syncedlyrics` optional (the `lrc` extra) and lazily imported so its absence only disables `.lrc`. SponsorBlock consumes `ctx.source_info` (the raw yt-dlp dict from the fetch step); wrap failures as `PostProcessingFailed`.

- [ ] **Step 3: GREEN + gates.** `make check` green.

- [ ] **Step 4: Commit**
```bash
git commit -am "feat(core/download): post — lrc generation, m3u ({list} templating), archive update, SponsorBlock"
```

---

### Task 9: `core.download.engine` — compose the pipeline, `download(request, on_progress)`

**Files:**
- Create: `packages/core/src/spotdl_core/download/engine.py`
- Modify: `packages/core/src/spotdl_core/download/__init__.py` (export `DownloadEngine`, steps, seams)
- Create: `packages/core/tests/download/test_engine.py`

**References:** the overall control flow of `search_and_download` (downloader.py ~425–863): plan → skip decisions → (metadata-only overwrite path) → fetch → convert/move → SponsorBlock → embed → lrc → outcome; error handling (~848–863) collecting a per-track failure without aborting.

**Contract vs freedom:** `DownloadEngine.download(request, on_progress=None) -> DownloadOutcome` is a **CONTRACT** (spec §5.4; Plan 7's worker calls exactly this). Internal composition order is contract; the class construction (which collaborators are injected) is contract-ish — Plan 7 must be able to build it. **No queueing/concurrency here.**

- [ ] **Step 1: Write `test_engine.py`** (fully offline — inject `FakeFetcher`, `FakeCoverDownloader`, `FakeSyncedLyricsSearch`, `FakeSponsorBlock`; `ConvertStep` uses real ffmpeg so gate the end-to-end cases with `requires_ffmpeg`; pure-plan cases need no ffmpeg):
  - happy path (`requires_ffmpeg`): request for `tiny.m4a` → mp3; outcome `DOWNLOADED`, file at expected templated path, tags present, progress callback saw FETCH→CONVERT→EMBED→DONE.
  - skip (no ffmpeg needed): pre-create the output file, `overwrite=SKIP` → outcome `SKIPPED` reason `ALREADY_EXISTS`, fetcher never called.
  - skip: url in `archive` → `SKIPPED`/`IN_ARCHIVE`, fetcher never called.
  - skip: `.skip` sidecar + `respect_skip_file` → `SKIPPED`/`SKIP_FILE`.
  - skip: explicit track + `skip_explicit` → `SKIPPED`/`EXPLICIT_FILTERED`.
  - metadata-only (`overwrite=METADATA`, existing file): re-embeds without fetching/converting; outcome `DOWNLOADED`.
  - failure isolation: `FakeFetcher` raises → outcome `FAILED`, `failed_step=="fetch"`, `error` populated, **no exception propagates** out of `download`.
  - failure: `ConversionFailed` from a bad ffmpeg path → `FAILED`, `failed_step=="convert"`.
  - move-fast-path (`requires_ffmpeg` not needed — pure move): m4a→m4a bitrate disable, file moved, `DOWNLOADED`.
  - `create_skip_file=True` writes the `.skip` sidecar on success.
  RED.

- [ ] **Step 2: Implement `engine.py`** — **CONTRACT:**
```python
class DownloadEngine:
    def __init__(
        self,
        config: DownloadConfig,
        *,
        fetcher: Fetcher,
        cover: CoverDownloader | None = None,
        lyrics_search: SyncedLyricsSearch | None = None,
        sponsor_block: SponsorBlock | None = None,
    ) -> None: ...

    async def download(
        self, request: DownloadRequest, on_progress: ProgressCallback | None = None,
    ) -> DownloadOutcome:
        """Download exactly one track through the pipeline. Never raises for
        per-track failures — returns a FAILED outcome tagged with the failing
        step (from DownloadFailed.step). Only truly-unexpected errors that are
        not DownloadFailed subclasses are also caught and reported as FAILED
        with step 'unknown'."""
```
Composition (mirrors v4 control flow, decomposed):
1. **plan**: `output_path = paths.build_output_path(request, config)`; `dups = paths.find_duplicates(...)`; `reason = paths.plan_skip(request, output_path, dups)`. If `reason` and not (reason is ALREADY_EXISTS and overwrite in {FORCE, METADATA}) → return `DownloadOutcome.skipped(...)`. Emit `ProgressEvent(PLAN)`.
2. **metadata-only branch**: if file exists and `overwrite == METADATA` → run `EmbedStep` on the existing file (+ optional dup move) and return `downloaded`. (Port v4 ~580–643, simplified.)
3. **force branch**: if file exists and `overwrite == FORCE` → unlink dups (best-effort).
4. `output_path.parent.mkdir(parents=True, exist_ok=True)`.
5. **fetch** (`FetchStep`) → **convert/move** (`ConvertStep`) → optional **SponsorBlock** (`SponsorBlockStep` when `request.sponsor_block` and a `sponsor_block` collaborator exists) → **embed** (`EmbedStep`) → optional **lrc** (`generate_lrc` when `request.generate_lrc`). Emit phase events throughout.
6. On success: optionally write `<output>.skip` when `create_skip_file`; return `DownloadOutcome.downloaded(request.track, output_path)`.
7. Wrap the whole body in a try/except: catch `DownloadFailed` (use `.step`) and any other `Exception` (`step="unknown"`); best-effort clean up a partial output; return `DownloadOutcome.failed(...)`. Each blocking step already offloads to `asyncio.to_thread`, so `download` is a coroutine safe to run under the server's worker pool.

Note: archive **loading/saving** and **m3u generation** are batch concerns the orchestrator (Plan 7) performs around many `download()` calls — the engine only reads `request.archive` (membership) and reports outcomes; it does not mutate the archive file.

- [ ] **Step 3: GREEN + gates.** `make check` green. `uv run lint-imports` still KEPT (core imports only model + providers.errors).

- [ ] **Step 4: Commit**
```bash
git add packages/core
git commit -m "feat(core/download): engine — compose plan/fetch/convert/embed/post into download(request, on_progress)"
```

---

### Task 10: Default-registry-style wiring helper + offline integration smoke test + parity self-check

**Files:**
- Create: `packages/core/src/spotdl_core/download/__init__.py` final public API (extend `__all__`)
- Create: `packages/core/tests/download/test_integration.py`
- Create: `packages/core/tests/download/test_public_api.py`

**Interfaces produced:** a convenience `build_default_engine(config) -> DownloadEngine` that wires the real collaborators (`YtDlpFetcher`, `HttpCoverDownloader`, `SyncedLyricsLibrary`, `YtDlpSponsorBlock`) — the single call Plan 7 uses — plus a finalized `spotdl_core.download` public surface.

- [ ] **Step 1: Write `test_public_api.py`.** Assert `spotdl_core.download` exports (sorted `__all__`): `DownloadEngine`, `build_default_engine`, `DownloadRequest`, `DownloadConfig`, `DownloadContext`, `DownloadOutcome`, `OutcomeStatus`, `OutputFormat`, `OverwriteMode`, `RestrictMode`, `SkipReason`, `Bitrate`, `BITRATE_AUTO`, `BITRATE_DISABLE`, `ProgressEvent`, `ProgressPhase`, `ProgressCallback`, `Step`, `Fetcher`, `FetchResult`, `CoverDownloader`, `SyncedLyricsSearch`, `SponsorBlock`, and the download error subclasses. Assert `import spotdl_core.download` works and `build_default_engine` is importable **without touching the network or ffmpeg** (lazy imports).

- [ ] **Step 2: Write `test_integration.py`** (`requires_ffmpeg`): an end-to-end run through `build_default_engine(config)` but with the fetcher **monkeypatched** to a fake that hands back `fixtures/tiny.opus`, downloading to opus (copy fast path) and to mp3 (re-encode), asserting the output files exist with embedded tags and a `.lrc` is produced when a synced `Lyrics` is on the request. This proves the whole pipeline composes with real ffmpeg + real mutagen while staying offline.

- [ ] **Step 3: Implement `build_default_engine`** and finalize `__init__.py`. `build_default_engine` lazily constructs `YtDlpFetcher(config)`, `HttpCoverDownloader(proxy=config.proxy)`, `SyncedLyricsLibrary()`, `YtDlpSponsorBlock()` and returns `DownloadEngine(config, fetcher=..., cover=..., lyrics_search=..., sponsor_block=...)`.

- [ ] **Step 4: Feature-parity self-check.** Verify the table in "Self-review" below: every spec §5.4 v4 feature maps to a shipped module/function with a test. `make check` green.

- [ ] **Step 5: Commit**
```bash
git add packages/core
git commit -m "feat(core/download): build_default_engine wiring, finalized public API, offline end-to-end integration test"
```

---

## Feature-parity table (spec §5.4 — REQUIRED: every v4 downloader feature → v5 module/task)

| v4 feature | v4 source | v5 module / function | Task |
|---|---|---|---|
| Output path templating (all VARS) | `formatter.format_query` / `create_file_name`; `VARS` | `download.paths.render_template` / `build_output_path`; `paths.VARS` | 4 |
| Full template variable set (20 tokens) | `formatter.VARS` | VARS table + `Track`/`AlbumRef`/`DownloadRequest` fields | 2, 4 |
| Restrict modes (none/ascii/strict) | `formatter.restrict_filename` | `paths.restrict_filename` + `RestrictMode` | 3, 4 |
| OS filename-length handling (smart_split) | `formatter.create_file_name` / `smart_split` | `paths.build_output_path` / `smart_split` | 4 |
| Overwrite modes (skip/force/metadata) | `downloader.search_and_download` | `OverwriteMode` + `paths.plan_skip` + engine branches | 3, 4, 9 |
| `.skip` sidecar (respect/create) | `search_and_download` | `paths.plan_skip` (respect) + engine (create) | 4, 9 |
| Duplicate detection (scan/detect_formats) | `search_and_download` / `known_songs` | `paths.find_duplicates` + `DownloadRequest.known_paths/detect_formats` | 3, 4 |
| Archive files (load/filter/add/save) | `utils.archive.Archive`; downloader archive block | `paths.load_archive`/`save_archive`; `post.archive_update`; `DownloadRequest.archive` | 4, 8 |
| Explicit-track skipping | `search_and_download` (`skip_explicit`) | `SkipReason.EXPLICIT_FILTERED` + `plan_skip` | 3, 4 |
| yt-dlp audio fetch | `providers/audio/base.py` | `fetch.YtDlpFetcher` / `FetchStep` | 5 |
| Format selection per output format | `audio/base.__init__` | `fetch.ytdl_format_for` | 5 |
| Cookie file | `audio/base` `cookiefile` | `DownloadConfig.cookie_file` → `fetch` | 3, 5 |
| Proxy | `downloader` proxy / `GlobalConfig` | `DownloadConfig.proxy` → fetch + cover | 3, 5, 7 |
| yt-dlp passthrough args | `formatter.args_to_ytdlp_options` | `DownloadConfig.ytdlp_args` → `fetch.build_ytdlp_options` | 3, 5 |
| Progress reporting | `ProgressHandler`/yt-dlp+ffmpeg hooks | `ProgressEvent`/`ProgressCallback` + step hooks | 3, 5, 6, 7 |
| ffmpeg conversion (per-format codecs) | `ffmpeg.FFMPEG_FORMATS`/`convert` | `convert.FFMPEG_CODECS` / `build_ffmpeg_command` / `ConvertStep` | 6 |
| Bitrate modes (auto/disable/CBR/VBR) | `ffmpeg.convert` bitrate block | `convert.resolve_bitrate` | 6 |
| Move-not-reencode fast path | `search_and_download` move block | `convert.should_move` + `ConvertStep` | 6 |
| ffmpeg passthrough args | `ffmpeg.convert` `ffmpeg_args` | `DownloadConfig.ffmpeg_args` | 3, 6 |
| ffmpeg error capture | `ffmpeg.convert` error dict | `ConversionFailed(<stderr>)` | 6 |
| ffmpeg binary location (NOT pip) | `ffmpeg.get_ffmpeg_path` | `DownloadConfig.ffmpeg_path` (auto-download OUT of core → CLI, Plan 8) | 3 |
| Metadata embed — mp3/m4a/flac/ogg/opus/wav | `metadata.embed_metadata`/`embed_wav_file` | `tags.embed_metadata` + preset tables + `EmbedStep` | 7 |
| Cover art fetch + embed | `metadata.embed_cover` | `tags.CoverDownloader`/`HttpCoverDownloader` | 7 |
| Plain + synced lyrics (SYLT/USLT) | `metadata.embed_lyrics` | `tags` LRC detection + SYLT/USLT | 7 |
| ISRC tag | `metadata` `isrc`/`TSRC`/`----:spotdl:ISRC` | `tags` presets | 7 |
| Source URL / track URL tags | `metadata` `WOAS`/`COMM` | `tags` (`track_url` + `candidate.url`) | 7 |
| retain-track-cover | v4 setting | `DownloadRequest.retain_track_cover` + `Track.cover_url` | 2, 7 |
| `.lrc` generation | `lrc.generate_lrc` | `post.generate_lrc` (`syncedlyrics` optional) | 8 |
| m3u + playlist numbering + `{list}` | `m3u.gen_m3u_files`/`create_m3u_content` | `post.gen_m3u_files`/`create_m3u_content` | 8 |
| SponsorBlock | `SponsorBlockPP`/`ModifyChaptersPP` | `post.YtDlpSponsorBlock`/`SponsorBlockStep` | 8 |
| Per-track failure isolation | `search_and_download` try/except | `engine.download` → `DownloadOutcome.failed(step=...)` | 9 |
| Typed error taxonomy (§10) | v4 ad-hoc exceptions | `providers.errors` (`AudioFetchFailed`/`ConversionFailed`/`MetadataEmbedFailed`/`PostProcessingFailed`) | 1 |
| Single-track entry point | `Downloader.download_song` | `DownloadEngine.download(request, on_progress)` | 9 |
| Batch orchestration / m3u / archive-save / concurrency | `download_multiple_songs` | **Out of core — Plan 7 (server workers)**; core exposes the batch utilities | 8, 9 |

---

## Self-review notes

- **Spec coverage:** implements spec §5.4 in full — the five-stage pipeline (plan/fetch/convert/embed/post) as typed steps threaded through `DownloadContext`; the parity list (all formats, full VARS, archive, m3u+numbering+retain-track-cover, cookies, proxy, yt-dlp passthrough, SponsorBlock). ffmpeg auto-download is deliberately **out of core** per the task brief (binary via `DownloadConfig.ffmpeg_path`; acquisition is a CLI/installer concern, Plan 8/11). §10 error taxonomy: consumes `DownloadFailed(step)`/`ConversionFailed`/`MetadataEmbedFailed` from Plan 2 and adds `AudioFetchFailed`/`PostProcessingFailed` in the same module.
- **Type consistency:** `Track`/`AlbumRef` amended additively (Task 2) so every VARS token and tag maps to a real field; `AudioCandidate` (Plan 1) is the chosen source; errors reuse Plan 2's `spotdl_core.providers.errors` (single taxonomy); no new domain enums leak outside `core.download` except by intended re-export. `DownloadEngine.download(...)` matches the spec §5.4 signature exactly and Plan 7 can call it.
- **No singletons / injection:** every external effect (yt-dlp, ffmpeg binary, cover HTTP, synced-lyrics, SponsorBlock) is a constructor-injected collaborator/Protocol; `build_default_engine` is the only place that wires the real ones, and it does so lazily.
- **Offline default suite:** the fetch/cover/lyrics/SponsorBlock seams are faked in the default suite; convert/tag/integration tests that need a real ffmpeg use `requires_ffmpeg`/`silent_audio` autoskips and run in CI where `FedericoCarboni/setup-ffmpeg` installs the binary (CI edit is Task 6, Step 3). Committed tiny audio fixtures (< ~50 KB each) provide real media input without network. No test hits the network.
- **Task ordering keeps `make check` green:** deps+errors+scaffold → model amendment → context (spine) → paths (pure, no deps on later modules) → fetch → convert (+CI ffmpeg) → tags → post → engine (composes all) → wiring + integration. Each task is independently reviewable, RED-first, and green at the end; import-linter stays KEPT throughout (core imports only `model` + `providers.errors`).
- **Boundaries honoured:** no queueing/concurrency/HTTP in core; batch archive-save and m3u generation are exposed as utilities but the per-track engine only reads `request.archive` and reports outcomes — Plan 7 owns orchestration. `core.download` never imports `core.matching`, `spotdl_server`, or `spotdl_cli`.
- **Known deliberate deviations (documented in-task):** conversion move-fast-path keys on ext+bitrate only (drops v4's piped-specific suppression); `ConversionFailed` carries stderr in the message rather than writing a sidecar error file (persistence is the caller's choice); stored match score vs popularity tiebreak is a Plan 3 concern, untouched here.
</content>
</invoke>
