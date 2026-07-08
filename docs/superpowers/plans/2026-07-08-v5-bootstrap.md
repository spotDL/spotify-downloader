# spotDL v5 Bootstrap Implementation Plan (Plan 1 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the v4 reference copy, the orphan `v5` branch, and a working monorepo skeleton: uv workspace, `packages/core` with the domain model, `apps/server` and `apps/cli` skeletons proving the embedded-server pattern, `apps/web` scaffold, enforced dependency boundaries, and CI.

**Architecture:** Monorepo per the approved spec (`docs/superpowers/specs/2026-07-08-v5-monorepo-rewrite-design.md`): `packages/core` (domain model — providers/matching/download come in later plans), `apps/server` (FastAPI, deployment modes), `apps/cli` (Typer; talks to the server via in-process ASGI, never imports core), `apps/web` (React/Vite). Dependency direction `core ← server ← cli` is machine-enforced with import-linter from day one.

**Tech Stack:** Python 3.13, uv workspace, pydantic v2, FastAPI, pydantic-settings, Typer, httpx, ruff, mypy (strict), pytest, import-linter; Node 22, pnpm 9, Vite, React 19, TypeScript, vitest.

## Global Constraints

- Python `>=3.13`; Node `>=22`; pnpm `9`; single uv lockfile at the workspace root.
- Package names/versions: `spotdl-core`, `spotdl-server`, `spotdl` (CLI app dir `apps/cli`) — all start at version `5.0.0a0`.
- Dependency direction: `core ← server ← cli`. `spotdl_cli` must never import `spotdl_core` directly (import-linter contract, CI-enforced).
- No code is copied from the `xnetcat-rewrite` branch. v4 code is only ported where a later plan explicitly says so.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- `make check` (lint + typecheck + test + web-check) must pass at the end of every task.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## Plan series roadmap (later plans, for context — not part of this plan)

2. `core.providers` (registry, capability Protocols, URL/platform-ID parsing, Spotify anonymous-token + credential fallback, Deezer, iTunes, MusicBrainz, YTMusic metadata; lyrics providers)
3. `core.matching` + golden corpus tooling and CI gate
4. `core.download` pipeline (yt-dlp, ffmpeg, mutagen, post-processing)
5. Server foundation (SQLAlchemy/Alembic schema, resolve/search/entity endpoints)
6. Server community layer (auth, votes, reports, admin, rate limiting)
7. Server downloads (job queue, WebSocket progress, browser delivery)
8. Generated API clients + full CLI commands + v4 compat shim
9. Textual TUI
10. Web UI (full pages)
11. Deploy: Railway, GHCR images, compose, docs site, release automation

---

### Task 1: v4 reference copy

**Files:**
- Create: `~/Projects/xnetcat/spotdl-v4-reference/` (outside the repo — plain files, no `.git`)

**Interfaces:**
- Consumes: `master` branch of `/Users/xnetcat/Projects/xnetcat/spotify-downloader`
- Produces: a browsable v4 tree used as reference by all later plans (especially matching/golden-corpus work)

- [ ] **Step 1: Export master's tree**

Run (from `/Users/xnetcat/Projects/xnetcat/spotify-downloader`):
```bash
mkdir -p ~/Projects/xnetcat/spotdl-v4-reference
git archive master | tar -x -C ~/Projects/xnetcat/spotdl-v4-reference
```

- [ ] **Step 2: Verify the copy**

Run:
```bash
test -f ~/Projects/xnetcat/spotdl-v4-reference/pyproject.toml \
  && test -f ~/Projects/xnetcat/spotdl-v4-reference/spotdl/utils/matching.py \
  && echo OK
```
Expected: `OK`

No commit (this directory is outside any repo).

---

### Task 2: Orphan `v5` branch in a worktree, seeded with license, spec, and roadmap

**Files:**
- Create: worktree `~/Projects/xnetcat/spotdl-v5` on new orphan branch `v5`
- Create: `README.md`, `LICENSE`, `.gitignore`, `docs/superpowers/specs/2026-07-08-v5-monorepo-rewrite-design.md` (copied), `docs/superpowers/plans/2026-07-08-v5-bootstrap.md` (copied)

**Interfaces:**
- Produces: the empty-history branch and directory every later task works in

- [ ] **Step 1: Create the orphan worktree**

Run (from `/Users/xnetcat/Projects/xnetcat/spotify-downloader`):
```bash
git worktree add --orphan -b v5 ~/Projects/xnetcat/spotdl-v5
```
If your git predates `--orphan` for worktrees (< 2.42), use:
```bash
git worktree add --detach ~/Projects/xnetcat/spotdl-v5 master
cd ~/Projects/xnetcat/spotdl-v5
git checkout --orphan v5
git rm -rf .
```

- [ ] **Step 2: Verify empty state**

Run (in `~/Projects/xnetcat/spotdl-v5`):
```bash
git status --porcelain && git branch --show-current
```
Expected: no tracked files, branch `v5`.

- [ ] **Step 3: Seed base files**

Copy license and docs from the main checkout:
```bash
cd ~/Projects/xnetcat/spotdl-v5
git -C /Users/xnetcat/Projects/xnetcat/spotify-downloader show master:LICENSE > LICENSE
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp /Users/xnetcat/Projects/xnetcat/spotify-downloader/docs/superpowers/specs/2026-07-08-v5-monorepo-rewrite-design.md docs/superpowers/specs/
cp /Users/xnetcat/Projects/xnetcat/spotify-downloader/docs/superpowers/plans/2026-07-08-v5-bootstrap.md docs/superpowers/plans/
```

Write `README.md`:
```markdown
# spotDL v5

Ground-up rewrite of spotify-downloader as a monorepo: a self-hostable
server (metadata, search, matching, lyrics, community curation), the
`spotdl` CLI/TUI, and a web UI.

**Status: pre-alpha rewrite.** Stable v4 lives on the `master` branch.

- Design spec: `docs/superpowers/specs/2026-07-08-v5-monorepo-rewrite-design.md`
- Layout: `apps/server`, `apps/cli`, `apps/web`, `packages/core`

## Development

Requires: uv, Python 3.13+, pnpm 9, Node 22+.

    make sync        # install python workspace
    make web-install # install web deps
    make check       # lint + typecheck + test everything
```

Write `.gitignore`:
```gitignore
__pycache__/
*.py[cod]
.venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
dist/
build/
*.egg-info/
node_modules/
apps/web/dist/
.coverage
coverage.xml
.env
.DS_Store
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: bootstrap v5 orphan branch (license, spec, plan, readme)"
```

---

### Task 3: uv workspace root + `packages/core` skeleton + Makefile

**Files:**
- Create: `pyproject.toml` (workspace root), `Makefile`
- Create: `packages/core/pyproject.toml`, `packages/core/src/spotdl_core/__init__.py`, `packages/core/src/spotdl_core/py.typed`, `packages/core/tests/test_package.py`

**Interfaces:**
- Produces: importable `spotdl_core` package with `__version__: str = "5.0.0a0"`; `make sync|lint|typecheck|test` targets used by every later task

- [ ] **Step 1: Write the workspace root `pyproject.toml`**

```toml
[project]
name = "spotdl-workspace"
version = "0.0.0"
requires-python = ">=3.13"

[tool.uv]
package = false

[tool.uv.workspace]
members = ["packages/core", "apps/server", "apps/cli"]

[tool.uv.sources]
spotdl-core = { workspace = true }
spotdl-server = { workspace = true }

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "mypy>=1.14",
    "ruff>=0.9",
    "import-linter>=2.1",
    "httpx>=0.28",
]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.13"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["packages/core/tests", "apps/server/tests", "apps/cli/tests"]
```

Note: `apps/server` and `apps/cli` are listed as members now; they are created in Tasks 5–6. Until then `uv sync` would fail, so Step 4 creates minimal stubs for both in this task.

- [ ] **Step 2: Write `packages/core/pyproject.toml`**

```toml
[project]
name = "spotdl-core"
version = "5.0.0a0"
description = "spotDL core: domain model, providers, matching, download engine"
requires-python = ">=3.13"
license = "MIT"
dependencies = ["pydantic>=2.9,<3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/spotdl_core"]
```

- [ ] **Step 3: Write the package init and a smoke test**

`packages/core/src/spotdl_core/__init__.py`:
```python
"""spotDL core: domain model, providers, matching, download engine."""

__version__ = "5.0.0a0"
```

Create empty marker file `packages/core/src/spotdl_core/py.typed`.

`packages/core/tests/test_package.py`:
```python
import spotdl_core


def test_version() -> None:
    assert spotdl_core.__version__ == "5.0.0a0"
```

- [ ] **Step 4: Create minimal `apps/server` and `apps/cli` stubs so the workspace resolves**

`apps/server/pyproject.toml`:
```toml
[project]
name = "spotdl-server"
version = "5.0.0a0"
description = "spotDL server"
requires-python = ">=3.13"
license = "MIT"
dependencies = ["spotdl-core"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/spotdl_server"]
```

`apps/server/src/spotdl_server/__init__.py`:
```python
"""spotDL server."""

__version__ = "5.0.0a0"
```

`apps/cli/pyproject.toml`:
```toml
[project]
name = "spotdl"
version = "5.0.0a0"
description = "spotDL command-line interface"
requires-python = ">=3.13"
license = "MIT"
dependencies = ["spotdl-server"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/spotdl_cli"]
```

`apps/cli/src/spotdl_cli/__init__.py`:
```python
"""spotDL command-line interface."""

__version__ = "5.0.0a0"
```

Create empty `py.typed` markers: `apps/server/src/spotdl_server/py.typed`, `apps/cli/src/spotdl_cli/py.typed`.

- [ ] **Step 5: Write the `Makefile`**

```makefile
.PHONY: sync lint typecheck test check web-install web-check

sync:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports

typecheck:
	uv run mypy packages/core/src apps/server/src apps/cli/src

test:
	uv run pytest

web-install:
	pnpm -C apps/web install

web-check:
	pnpm -C apps/web run type-check
	pnpm -C apps/web run test

check: lint typecheck test web-check
```

Note: `lint` includes `lint-imports`, which needs the `.importlinter` file from Task 7. Until Task 7, run `uv run ruff check .` etc. individually, or expect `lint-imports` to fail with "Could not read any configuration" — that is fine; full `make check` becomes the gate from Task 7 onward.

- [ ] **Step 6: Sync and run the test**

Run:
```bash
uv sync --all-packages
uv run pytest packages/core/tests -v
```
Expected: `test_version PASSED`, exit 0. Also run:
```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy packages/core/src apps/server/src apps/cli/src
```
Expected: no errors. (`uv.lock` is created — commit it.)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: uv workspace, core/server/cli package skeletons, makefile"
```

---

### Task 4: `core.model` — enums and domain entities

**Files:**
- Create: `packages/core/src/spotdl_core/model/__init__.py`, `packages/core/src/spotdl_core/model/enums.py`, `packages/core/src/spotdl_core/model/entities.py`
- Test: `packages/core/tests/model/test_enums.py`, `packages/core/tests/model/test_entities.py`

**Interfaces:**
- Produces (used by every later plan):
  - `EntityType`, `ProviderId`, `MatchStatus`, `LyricsKind` (StrEnums)
  - `ArtistRef(name, provider=None, provider_id=None)`
  - `AlbumRef(name, album_artist=None, year=None, track_count=None, cover_url=None)`
  - `Track(name, artists: tuple[str, ...], duration_ms: int, album=None, isrc=None, explicit=None, track_number=None, disc_number=None, genres=(), year=None, provider=None, provider_id=None)` with property `main_artist -> str`
  - `AudioCandidate(provider, provider_id, url, name, artists=(), duration_ms=None, album=None, isrc=None, verified=False, popularity=None)`
  - `FeatureVector(title_similarity, artist_similarity, album_similarity, duration_delta_s, isrc_equal, verified_source, forbidden_word_penalty, explicit_mismatch, popularity_prior)`
  - `Match(candidate, score, matcher_version, status=MatchStatus.AUTO, features=None)`
  - `Lyrics(kind, text, source)`
  - All models are frozen (immutable) pydantic models.

- [ ] **Step 1: Write the failing tests**

`packages/core/tests/model/test_enums.py`:
```python
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId


def test_entity_type_values() -> None:
    assert EntityType.TRACK == "track"
    assert set(EntityType) == {"track", "album", "artist", "playlist"}


def test_provider_ids_include_metadata_and_audio_sources() -> None:
    values = set(ProviderId)
    assert {"spotify", "deezer", "itunes", "musicbrainz"} <= values
    assert {"ytmusic", "youtube", "soundcloud", "bandcamp", "piped"} <= values
    assert {"lrclib", "genius", "musixmatch", "azlyrics"} <= values


def test_match_status_values() -> None:
    assert set(MatchStatus) == {"auto", "community_verified", "rejected"}


def test_lyrics_kind_values() -> None:
    assert set(LyricsKind) == {"plain", "synced"}
```

`packages/core/tests/model/test_entities.py`:
```python
import pytest
from pydantic import ValidationError

from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    Match,
    MatchStatus,
    ProviderId,
    Track,
)


def make_track() -> Track:
    return Track(
        name="Song Name",
        artists=("Main Artist", "Feat Artist"),
        duration_ms=200_000,
        album=AlbumRef(name="Album Name", year=2020),
        isrc="USUM72000001",
    )


def test_track_main_artist_is_first_artist() -> None:
    assert make_track().main_artist == "Main Artist"


def test_track_requires_at_least_one_artist() -> None:
    with pytest.raises(ValidationError):
        Track(name="x", artists=(), duration_ms=1000)


def test_track_is_immutable() -> None:
    track = make_track()
    with pytest.raises(ValidationError):
        track.name = "changed"  # type: ignore[misc]


def test_match_defaults_to_auto_status() -> None:
    candidate = AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="abc123",
        url="https://music.youtube.com/watch?v=abc123",
        name="Song Name",
    )
    match = Match(candidate=candidate, score=91.5, matcher_version="v5.0")
    assert match.status is MatchStatus.AUTO
    assert match.features is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/core/tests/model -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spotdl_core.model'`

- [ ] **Step 3: Implement the model**

`packages/core/src/spotdl_core/model/enums.py`:
```python
from enum import StrEnum


class EntityType(StrEnum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"


class ProviderId(StrEnum):
    # metadata sources
    SPOTIFY = "spotify"
    DEEZER = "deezer"
    ITUNES = "itunes"
    MUSICBRAINZ = "musicbrainz"
    # audio targets (ytmusic is also a metadata source)
    YTMUSIC = "ytmusic"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"
    PIPED = "piped"
    # lyrics sources
    LRCLIB = "lrclib"
    GENIUS = "genius"
    MUSIXMATCH = "musixmatch"
    AZLYRICS = "azlyrics"


class MatchStatus(StrEnum):
    AUTO = "auto"
    COMMUNITY_VERIFIED = "community_verified"
    REJECTED = "rejected"


class LyricsKind(StrEnum):
    PLAIN = "plain"
    SYNCED = "synced"
```

`packages/core/src/spotdl_core/model/entities.py`:
```python
from pydantic import BaseModel, ConfigDict, field_validator

from spotdl_core.model.enums import LyricsKind, MatchStatus, ProviderId


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ArtistRef(_Frozen):
    name: str
    provider: ProviderId | None = None
    provider_id: str | None = None


class AlbumRef(_Frozen):
    name: str
    album_artist: str | None = None
    year: int | None = None
    track_count: int | None = None
    cover_url: str | None = None


class Track(_Frozen):
    name: str
    artists: tuple[str, ...]
    duration_ms: int
    album: AlbumRef | None = None
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    genres: tuple[str, ...] = ()
    year: int | None = None
    provider: ProviderId | None = None
    provider_id: str | None = None

    @field_validator("artists")
    @classmethod
    def _at_least_one_artist(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("a track needs at least one artist")
        return value

    @property
    def main_artist(self) -> str:
        return self.artists[0]


class AudioCandidate(_Frozen):
    provider: ProviderId
    provider_id: str
    url: str
    name: str
    artists: tuple[str, ...] = ()
    duration_ms: int | None = None
    album: str | None = None
    isrc: str | None = None
    verified: bool = False
    popularity: int | None = None


class FeatureVector(_Frozen):
    title_similarity: float
    artist_similarity: float
    album_similarity: float | None
    duration_delta_s: float
    isrc_equal: bool
    verified_source: bool
    forbidden_word_penalty: float
    explicit_mismatch: bool
    popularity_prior: float


class Match(_Frozen):
    candidate: AudioCandidate
    score: float
    matcher_version: str
    status: MatchStatus = MatchStatus.AUTO
    features: FeatureVector | None = None


class Lyrics(_Frozen):
    kind: LyricsKind
    text: str
    source: ProviderId
```

`packages/core/src/spotdl_core/model/__init__.py`:
```python
from spotdl_core.model.entities import (
    AlbumRef,
    ArtistRef,
    AudioCandidate,
    FeatureVector,
    Lyrics,
    Match,
    Track,
)
from spotdl_core.model.enums import EntityType, LyricsKind, MatchStatus, ProviderId

__all__ = [
    "AlbumRef",
    "ArtistRef",
    "AudioCandidate",
    "EntityType",
    "FeatureVector",
    "Lyrics",
    "LyricsKind",
    "Match",
    "MatchStatus",
    "ProviderId",
    "Track",
]
```

Also create empty `packages/core/tests/__init__.py` and `packages/core/tests/model/__init__.py` if pytest collection needs them (it should not with default rootdir settings; skip unless imports collide).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests -v`
Expected: all PASS. Then `uv run mypy packages/core/src` — no errors.

- [ ] **Step 5: Commit**

```bash
git add packages/core
git commit -m "feat(core): domain model enums and frozen entities"
```

---

### Task 5: `apps/server` skeleton — settings, app factory, health + config endpoints

**Files:**
- Create: `apps/server/src/spotdl_server/settings.py`, `apps/server/src/spotdl_server/app.py`
- Modify: `apps/server/pyproject.toml` (add dependencies)
- Test: `apps/server/tests/test_app.py`

**Interfaces:**
- Consumes: nothing from core yet (core is a declared dependency only).
- Produces (relied on by Task 6 and later plans):
  - `DeploymentMode` StrEnum: `HOSTED = "hosted"`, `SELFHOST = "selfhost"`, `EMBEDDED = "embedded"`
  - `Settings(BaseSettings)` with field `mode: DeploymentMode = DeploymentMode.SELFHOST`, env prefix `SPOTDL_` (so `SPOTDL_MODE=hosted` works)
  - `create_app(settings: Settings | None = None) -> FastAPI`
  - `GET /api/v1/health` → `{"status": "ok"}`
  - `GET /api/v1/config` → `{"mode": "<mode>", "features": {"downloads": <bool>}}` where downloads is false only in hosted mode

- [ ] **Step 1: Add server dependencies**

In `apps/server/pyproject.toml`, replace the `dependencies` line with:
```toml
dependencies = [
    "spotdl-core",
    "fastapi>=0.115,<1",
    "uvicorn>=0.34",
    "pydantic-settings>=2.7",
]
```
Run: `uv sync --all-packages`

- [ ] **Step 2: Write the failing tests**

`apps/server/tests/test_app.py`:
```python
import httpx

from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings


def make_client(settings: Settings | None = None) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(settings))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health() -> None:
    async with make_client() as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_config_defaults_to_selfhost_with_downloads() -> None:
    async with make_client() as client:
        resp = await client.get("/api/v1/config")
    body = resp.json()
    assert body["mode"] == "selfhost"
    assert body["features"]["downloads"] is True


async def test_config_hosted_disables_downloads() -> None:
    async with make_client(Settings(mode=DeploymentMode.HOSTED)) as client:
        resp = await client.get("/api/v1/config")
    body = resp.json()
    assert body["mode"] == "hosted"
    assert body["features"]["downloads"] is False


def test_mode_reads_spotdl_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SPOTDL_MODE", "embedded")
    assert Settings().mode is DeploymentMode.EMBEDDED
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest apps/server/tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spotdl_server.app'`

- [ ] **Step 4: Implement settings and app factory**

`apps/server/src/spotdl_server/settings.py`:
```python
from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(StrEnum):
    HOSTED = "hosted"
    SELFHOST = "selfhost"
    EMBEDDED = "embedded"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPOTDL_")

    mode: DeploymentMode = DeploymentMode.SELFHOST
```

`apps/server/src/spotdl_server/app.py`:
```python
from typing import Any

from fastapi import FastAPI

from spotdl_server import __version__
from spotdl_server.settings import DeploymentMode, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="spotdl-server", version=__version__)
    app.state.settings = settings

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/config")
    async def config() -> dict[str, Any]:
        return {
            "mode": settings.mode.value,
            "features": {"downloads": settings.mode is not DeploymentMode.HOSTED},
        }

    return app
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest apps/server/tests -v`
Expected: 4 PASS. Then `uv run mypy apps/server/src` — no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/server pyproject.toml uv.lock
git commit -m "feat(server): app factory with deployment modes, health and config endpoints"
```

---

### Task 6: `apps/cli` skeleton — Typer app, embedded server client, `status` command

**Files:**
- Create: `apps/cli/src/spotdl_cli/client.py`, `apps/cli/src/spotdl_cli/__main__.py`
- Modify: `apps/cli/pyproject.toml` (dependencies + console script)
- Test: `apps/cli/tests/test_cli.py`

**Interfaces:**
- Consumes: `create_app`, `Settings`, `DeploymentMode` from `spotdl_server` (Task 5).
- Produces:
  - `embedded_client()` async context manager yielding an `httpx.AsyncClient` wired to an in-process embedded-mode server — the pattern all later CLI work builds on
  - Typer `app` with commands `version` and `status`
  - console script `spotdl` → `spotdl_cli.__main__:main`

- [ ] **Step 1: Add CLI dependencies and entry point**

In `apps/cli/pyproject.toml`, replace the `dependencies` line and add scripts:
```toml
dependencies = [
    "spotdl-server",
    "typer>=0.15",
    "httpx>=0.28",
    "rich>=13.9",
]

[project.scripts]
spotdl = "spotdl_cli.__main__:main"
```
Run: `uv sync --all-packages`

- [ ] **Step 2: Write the failing tests**

`apps/cli/tests/test_cli.py`:
```python
from typer.testing import CliRunner

from spotdl_cli import __version__
from spotdl_cli.__main__ import app

runner = CliRunner()


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_status_reaches_embedded_server() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "server: ok (embedded)" in result.output
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest apps/cli/tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spotdl_cli.__main__'`

- [ ] **Step 4: Implement the client and CLI**

`apps/cli/src/spotdl_cli/client.py`:
```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings


@asynccontextmanager
async def embedded_client() -> AsyncIterator[httpx.AsyncClient]:
    """An httpx client talking to an in-process embedded-mode server."""
    app = create_app(Settings(mode=DeploymentMode.EMBEDDED))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://embedded") as client:
        yield client
```

`apps/cli/src/spotdl_cli/__main__.py`:
```python
import asyncio

import typer

from spotdl_cli import __version__
from spotdl_cli.client import embedded_client

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def version() -> None:
    """Print the spotdl version."""
    typer.echo(__version__)


@app.command()
def status() -> None:
    """Check that the spotdl server is reachable."""

    async def _check() -> str:
        async with embedded_client() as client:
            resp = await client.get("/api/v1/health")
            resp.raise_for_status()
            return str(resp.json()["status"])

    typer.echo(f"server: {asyncio.run(_check())} (embedded)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest apps/cli/tests -v`
Expected: 2 PASS. Also verify the console script end-to-end:
```bash
uv run spotdl status
```
Expected output: `server: ok (embedded)`. Then `uv run mypy apps/cli/src` — no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/cli pyproject.toml uv.lock
git commit -m "feat(cli): typer skeleton with embedded-server status command"
```

---

### Task 7: Dependency-boundary enforcement with import-linter

**Files:**
- Create: `.importlinter`
- Test: `make lint` (contract check is the test)

**Interfaces:**
- Produces: CI-enforced guarantee of the spec's §3 dependency rule.

- [ ] **Step 1: Write `.importlinter`**

```ini
[importlinter]
root_packages =
    spotdl_core
    spotdl_server
    spotdl_cli

[importlinter:contract:layers]
name = Dependency direction: core <- server <- cli
type = layers
layers =
    spotdl_cli
    spotdl_server
    spotdl_core

[importlinter:contract:no_cli_core]
name = CLI must not import core directly (server API only)
type = forbidden
source_modules =
    spotdl_cli
forbidden_modules =
    spotdl_core
```

- [ ] **Step 2: Run the contracts and verify they pass**

Run: `uv run lint-imports`
Expected: both contracts KEPT, exit 0.

- [ ] **Step 3: Prove the contract catches violations**

Temporarily add `import spotdl_core  # noqa: F401` to the top of `apps/cli/src/spotdl_cli/client.py`, run `uv run lint-imports`, and confirm it FAILS with the `no_cli_core` contract BROKEN. Then remove the line and re-run to confirm KEPT again.

- [ ] **Step 4: Run the full lint target**

Run: `make lint`
Expected: ruff check, ruff format, and lint-imports all pass.

- [ ] **Step 5: Commit**

```bash
git add .importlinter
git commit -m "chore: enforce core<-server<-cli boundaries with import-linter"
```

---

### Task 8: `apps/web` scaffold with vitest smoke test

**Files:**
- Create: `apps/web/` via create-vite (react-ts template), then modify `apps/web/package.json`, `apps/web/src/App.tsx`; create `apps/web/src/App.test.tsx`, `apps/web/vitest.config.ts`

**Interfaces:**
- Produces: `pnpm -C apps/web run dev|build|type-check|test` — the workspace Plan 10 builds the real UI in.

- [ ] **Step 1: Scaffold**

Run (from repo root):
```bash
pnpm create vite apps/web --template react-ts
pnpm -C apps/web install
```

- [ ] **Step 2: Add test tooling**

Run:
```bash
pnpm -C apps/web add -D vitest jsdom @testing-library/react @testing-library/jest-dom @vitejs/plugin-react
```

Create `apps/web/vitest.config.ts`:
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

In `apps/web/package.json`, ensure the scripts block contains:
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "type-check": "tsc -b --noEmit",
  "test": "vitest run"
}
```

- [ ] **Step 3: Replace the template App and write the failing test**

`apps/web/src/App.tsx` (replace template content entirely):
```tsx
function App() {
  return (
    <main>
      <h1>spotDL</h1>
      <p>v5 web UI — under construction.</p>
    </main>
  );
}

export default App;
```

`apps/web/src/App.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders the spotDL heading", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "spotDL" })).toBeDefined();
});
```

Remove template cruft the App no longer uses: `apps/web/src/App.css`, `apps/web/src/assets/react.svg`, the `import "./App.css"` line if present, and the logo imports in `App.tsx` (already gone with the replacement above).

- [ ] **Step 4: Run web checks**

Run:
```bash
pnpm -C apps/web run type-check
pnpm -C apps/web run test
```
Expected: type-check clean; 1 test passes.

- [ ] **Step 5: Verify full `make check` now passes end-to-end**

Run: `make check`
Expected: exit 0 (lint, typecheck, pytest, web type-check + test).

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat(web): vite react-ts scaffold with vitest smoke test"
```

---

### Task 9: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: CI gate for the `v5` branch; later plans extend it (Postgres service, golden corpus, Playwright, image builds).

- [ ] **Step 1: Write the workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [v5]
  pull_request:
    branches: [v5]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
      - run: uv sync --all-packages
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run lint-imports
      - run: uv run mypy packages/core/src apps/server/src apps/cli/src
      - run: uv run pytest

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: apps/web/pnpm-lock.yaml
      - run: pnpm -C apps/web install --frozen-lockfile
      - run: pnpm -C apps/web run type-check
      - run: pnpm -C apps/web run test
```

- [ ] **Step 2: Validate locally**

Run the same commands the workflow runs:
```bash
make check
```
Expected: exit 0.

- [ ] **Step 3: Commit and push**

```bash
git add .github
git commit -m "ci: python and web jobs for the v5 branch"
git push -u origin v5
```
Then verify the run: `gh run watch --branch v5` (or `gh run list --branch v5 --limit 1`) — both jobs green.

---

## Self-review notes

- **Spec coverage:** this plan implements spec §3 (layout/tooling/boundaries), the mode skeleton of §4, the model slice of §5.1, and §12 steps 1–2 (reference copy, orphan branch). Everything else is explicitly deferred to Plans 2–11 listed in the roadmap section.
- **Type consistency:** `Settings`/`DeploymentMode`/`create_app` names match between Tasks 5 and 6; `spotdl_core.model` exports match test imports in Task 4.
- **Known seams left on purpose:** `make lint` includes `lint-imports` from Task 3 but the config lands in Task 7 (called out in Task 3 Step 5); `apps/server`/`apps/cli` stubs are created early in Task 3 so the uv workspace resolves.
