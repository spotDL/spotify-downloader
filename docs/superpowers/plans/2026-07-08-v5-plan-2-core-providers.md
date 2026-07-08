# spotDL v5 `core.providers` Implementation Plan (Plan 2 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `packages/core/src/spotdl_core/providers/` — the capability-based provider layer from spec §5.2: runtime-checkable capability Protocols, the typed exception taxonomy (spec §10), one-place URL/platform-ID parsing, shared async HTTP plumbing, a capability registry with deterministic ordering and lazy provider construction, and the v1 providers themselves (Spotify, Deezer, iTunes, MusicBrainz, YTMusic metadata; YTMusic/YouTube/SoundCloud/Bandcamp/Piped audio; LRCLIB/Genius/Musixmatch/AZLyrics lyrics). No provider's failure or scraper breakage may import-break another.

**Architecture:** `core.providers` is a sub-package of `packages/core` (spec §5). It has no knowledge of HTTP servers, databases, or UI; it exposes typed domain objects built on `core.model` (Plan 1). Providers implement any subset of five Protocols; a registry wires them and is the single entry point for the server (Plan 5) to obtain providers by capability. All I/O is async (`httpx`); heavy/fragile third-party deps (`ytmusicapi`, `yt-dlp`, scrapers) are imported lazily inside registry factories so a broken dependency degrades exactly one provider. No module-level mutable singletons: clients are constructed, injected, and closed through async context managers.

**Tech Stack:** Python 3.13, pydantic v2 (frozen models), httpx (async), tenacity (retry/backoff), pyotp (Spotify TOTP), ytmusicapi, yt-dlp, beautifulsoup4 + lxml (scrapers). Tests: pytest + pytest-asyncio + respx (httpx mock router); checked-in JSON response fixtures; live provider tests marked `network` and excluded from default runs.

## Global Constraints

- Python `>=3.13`; single uv lockfile at the workspace root.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Dependency direction (spec §3, machine-enforced by import-linter): `core ← server ← cli`. `spotdl_core` (and therefore everything in `core.providers`) must **never** import `spotdl_server` or `spotdl_cli`. `core.providers` may import only `core.model`, the standard library, and third-party libraries.
- New runtime dependencies go in `packages/core/pyproject.toml`; new test-only dependencies go in the root `pyproject.toml` `[dependency-groups].dev`. Exact version floors are given per task and were verified to exist on PyPI.
- No code is copied wholesale from the `xnetcat-rewrite` branch or v4. Those trees are **API/endpoint/shape references only** (paths cited per task). Design and code are written fresh against the Protocols defined here.
- **No module-level mutable singletons.** HTTP clients are created by a factory, injected into providers, owned by the registry, and closed via `aclose()` / `async with`.
- **Provider isolation is mandatory.** The registry module must import with zero provider third-party deps installed. Provider modules that need a heavy or fragile dependency import it lazily (inside the registry factory or inside the method that uses it), never at provider-module top level in a way that breaks `import spotdl_core.providers`.
- TDD: every task writes failing tests first (RED), then implements to green. Pure-parse tests run from checked-in JSON fixtures with no network. HTTP-behavior tests use `respx`. Tests that hit real provider APIs are marked `@pytest.mark.network` and excluded from `make check`.
- All test directories are packages (`__init__.py` present); pytest runs with `--import-mode=importlib` (already configured in root `pyproject.toml`).
- `make check` (lint + typecheck + test + web-check) must pass at the end of **every** task. `make check` runs `pytest` with `-m "not network"` (configured in Task 1), so network tests never gate CI.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## What already exists (Plan 1, do not recreate)

- `packages/core/src/spotdl_core/model/` — `enums.py` (`EntityType`, `ProviderId`, `MatchStatus`, `LyricsKind`) and `entities.py` (`ArtistRef`, `AlbumRef`, `Track`, `AudioCandidate`, `FeatureVector`, `Match`, `Lyrics` — all frozen pydantic). Re-exported from `spotdl_core.model`.
- `ProviderId` members (exact): `SPOTIFY, DEEZER, ITUNES, MUSICBRAINZ, YTMUSIC, YOUTUBE, SOUNDCLOUD, BANDCAMP, PIPED, LRCLIB, GENIUS, MUSIXMATCH, AZLYRICS` (values are the lowercase strings).
- `Track(name, artists: tuple[str,...], duration_ms: int, album: AlbumRef|None, isrc, explicit, track_number, disc_number, genres: tuple[str,...], year, provider, provider_id)` with property `main_artist`.
- `AudioCandidate(provider, provider_id, url, name, artists=(), duration_ms=None, album=None, isrc=None, verified=False, popularity=None)`.
- `Lyrics(kind: LyricsKind, text: str, source: ProviderId)`.
- Root `pyproject.toml`: ruff (E,F,I,UP,B,SIM; line-length 100), mypy strict, pytest `asyncio_mode = "auto"`, `addopts = "--import-mode=importlib"`, `testpaths` includes `packages/core/tests`.
- `apps/server/tests/conftest.py` strips `SPOTDL_`-prefixed env vars (server only).

## Plan series roadmap (for context — not part of this plan)

Plan 1 bootstrap (done) → **Plan 2 `core.providers` (this plan)** → Plan 3 `core.matching` + golden corpus → Plan 4 `core.download` → Plans 5–7 server → Plan 8 clients + CLI → Plan 9 TUI → Plan 10 web → Plan 11 deploy.

## Package layout produced by this plan

```
packages/core/src/spotdl_core/providers/
├─ __init__.py            # public API re-exports
├─ errors.py              # exception taxonomy (Task 1)  [CONTRACT]
├─ urls.py                # URL / provider:type:id parsing (Task 2)  [CONTRACT]
├─ base.py                # Protocols + ResolvedEntity + HttpProvider (Task 3)  [CONTRACT]
├─ http.py                # client factory + request_json error mapping (Task 4)  [CONTRACT for error map]
├─ registry.py            # ProviderRegistry, ProviderSpec, PROVIDER_ORDER, build_default_registry (Task 5, 12)  [CONTRACT for API]
├─ metadata/
│  ├─ __init__.py
│  ├─ spotify.py          # Task 6
│  ├─ deezer.py           # Task 7
│  ├─ itunes.py           # Task 7
│  └─ musicbrainz.py      # Task 8
├─ audio/
│  ├─ __init__.py
│  ├─ ytmusic.py          # Task 9 (also metadata: Resolves+Searches)
│  ├─ youtube.py          # Task 9
│  ├─ soundcloud.py       # Task 10
│  ├─ bandcamp.py         # Task 10
│  └─ piped.py            # Task 10
└─ lyrics/
   ├─ __init__.py
   ├─ lrclib.py           # Task 11
   ├─ genius.py           # Task 11
   ├─ musixmatch.py       # Task 11
   └─ azlyrics.py         # Task 11

packages/core/tests/providers/
├─ __init__.py
├─ fixtures/<provider>/*.json    # checked-in recorded responses
├─ conftest.py                   # shared fixtures (load_fixture, respx helpers)
└─ test_*.py
```

---

### Task 1: Provider package scaffold, dependencies, test policy, and exception taxonomy

**Files:**
- Modify: `packages/core/pyproject.toml` (add runtime deps), root `pyproject.toml` (dev dep + pytest markers/addopts)
- Create: `packages/core/src/spotdl_core/providers/__init__.py`, `packages/core/src/spotdl_core/providers/errors.py`
- Create: `packages/core/tests/providers/__init__.py`, `packages/core/tests/providers/test_errors.py`

**Interfaces produced (relied on by every later task and by Plans 3–7):**
- The exception taxonomy in `spotdl_core.providers.errors`, re-exported from `spotdl_core.providers`.

**Contract vs freedom:** The exception class names, their inheritance, and the extra attributes (`provider`, `retry_after`, `step`) are a **CONTRACT** — Plans 4–7 map these to API error codes. Implementers may add docstrings but must not rename or re-parent.

- [ ] **Step 1: Add runtime dependencies to `packages/core/pyproject.toml`**

Replace the `dependencies` list with (floors verified on PyPI 2026-07):
```toml
dependencies = [
    "pydantic>=2.9,<3",
    "httpx>=0.28",
    "tenacity>=9.0",
    "pyotp>=2.9",
    "ytmusicapi>=1.8",
    "yt-dlp>=2025.1.0",
    "beautifulsoup4>=4.12",
    "lxml>=5.3",
]
```
Rationale: `httpx` (all HTTP), `tenacity` (retry/backoff in `http.py`), `pyotp` (Spotify anonymous-token TOTP, Task 6), `ytmusicapi` (Task 9), `yt-dlp` (Task 9 YouTube metadata), `beautifulsoup4`+`lxml` (scrapers: Bandcamp/SoundCloud/Genius/Musixmatch/AZLyrics). These are declared as hard deps so tests can install them, but audio/lyrics provider modules that use the fragile ones are imported **lazily** in the registry (Task 5) — see the isolation constraint. MusicBrainz and LRCLIB use `httpx` directly (no extra dep).

- [ ] **Step 2: Add dev dependency and pytest config to the root `pyproject.toml`**

Add `respx>=0.22` to `[dependency-groups].dev`. Update `[tool.pytest.ini_options]`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--import-mode=importlib -m 'not network'"
testpaths = ["packages/core/tests", "apps/server/tests", "apps/cli/tests"]
markers = [
    "network: test hits a real provider API over the network; excluded from default runs and CI",
]
```
`make check` therefore never runs `network` tests. To run them deliberately: `uv run pytest -m network`.

Run: `uv sync --all-packages` and confirm the lockfile updates.

- [ ] **Step 3: Write the failing test `packages/core/tests/providers/test_errors.py`**

```python
import pytest

from spotdl_core.model import ProviderId
from spotdl_core.providers import (
    ConversionFailed,
    DownloadFailed,
    EntityNotFound,
    MetadataEmbedFailed,
    NoMatchFound,
    ProviderAuthError,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)


@pytest.mark.parametrize(
    "exc",
    [ProviderError, ProviderUnavailable, ProviderAuthError, RateLimited, EntityNotFound],
)
def test_provider_errors_are_spotdl_errors(exc: type[Exception]) -> None:
    assert issubclass(exc, ProviderError)
    assert issubclass(exc, SpotdlError)


def test_unsupported_url_and_no_match_are_spotdl_but_not_provider_errors() -> None:
    assert issubclass(UnsupportedURL, SpotdlError)
    assert issubclass(NoMatchFound, SpotdlError)
    assert not issubclass(UnsupportedURL, ProviderError)


def test_provider_error_carries_provider_id() -> None:
    err = ProviderUnavailable("down", provider=ProviderId.SPOTIFY)
    assert err.provider is ProviderId.SPOTIFY
    assert str(err) == "down"


def test_rate_limited_carries_retry_after() -> None:
    err = RateLimited(provider=ProviderId.MUSICBRAINZ, retry_after=1.5)
    assert err.retry_after == 1.5


def test_download_errors_carry_step() -> None:
    assert issubclass(ConversionFailed, DownloadFailed)
    assert issubclass(MetadataEmbedFailed, DownloadFailed)
    assert issubclass(DownloadFailed, SpotdlError)
    assert ConversionFailed().step == "convert"
    assert MetadataEmbedFailed().step == "embed"
    assert DownloadFailed(step="fetch").step == "fetch"
```

- [ ] **Step 4: Run tests to confirm RED**

Run: `uv run pytest packages/core/tests/providers/test_errors.py -v`
Expected: `ModuleNotFoundError` / `ImportError` for `spotdl_core.providers`.

- [ ] **Step 5: Implement `packages/core/src/spotdl_core/providers/errors.py`** — **CONTRACT (match exactly)**

```python
"""Typed exception taxonomy for spotDL core (spec §10).

This is the first consumer, so the full set is defined here. The provider
subset is raised in this plan; the download subset is defined here as the
shared taxonomy root and raised in Plan 4. The server (Plan 5+) maps these to
the stable API error envelope {code, message, detail}.
"""

from __future__ import annotations

from spotdl_core.model import ProviderId


class SpotdlError(Exception):
    """Root of the spotDL exception hierarchy."""


# --- provider layer -------------------------------------------------------

class ProviderError(SpotdlError):
    """Base for provider-layer failures; carries the provider id when known."""

    def __init__(self, message: str = "", *, provider: ProviderId | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class ProviderUnavailable(ProviderError):
    """Provider unreachable, down, dependency import failed, or repeated 5xx."""


class ProviderAuthError(ProviderError):
    """Authentication/token acquisition failed (401/403, bad creds, TOTP failure)."""


class RateLimited(ProviderError):
    """Provider returned 429 after retries were exhausted."""

    def __init__(
        self,
        message: str = "",
        *,
        provider: ProviderId | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, provider=provider)
        self.retry_after = retry_after


class EntityNotFound(ProviderError):
    """The requested entity id/URL resolved to nothing (404 or empty result)."""


class UnsupportedURL(SpotdlError):
    """A URL or `provider:type:id` string could not be parsed to a known ref."""


class NoMatchFound(SpotdlError):
    """Search/match produced no candidate for the given track."""


# --- download layer (raised in Plan 4; defined here as the shared taxonomy) --

class DownloadFailed(SpotdlError):
    """A download-pipeline step failed. `step` names the failing step."""

    def __init__(self, message: str = "", *, step: str) -> None:
        super().__init__(message)
        self.step = step


class ConversionFailed(DownloadFailed):
    """ffmpeg conversion failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="convert")


class MetadataEmbedFailed(DownloadFailed):
    """Tag/metadata embedding failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="embed")
```

- [ ] **Step 6: Implement `packages/core/src/spotdl_core/providers/__init__.py`**

Re-export the full error taxonomy now; later tasks extend `__all__` with Protocols, `PlatformRef`, `parse`, `ProviderRegistry`, etc. For this task export exactly the error names imported in the test. Keep `__all__` sorted.

- [ ] **Step 7: Confirm GREEN + quality gates**

Run: `uv run pytest packages/core/tests/providers -v` (all pass), then `make check` (green). Add `packages/core/tests/providers/__init__.py` (empty).

- [ ] **Step 8: Commit**

```bash
git add packages/core pyproject.toml uv.lock
git commit -m "feat(core/providers): package scaffold, deps, test policy, exception taxonomy"
```

---

### Task 2: `core.providers.urls` — URL / platform-ID parsing (single source of truth)

**Files:**
- Create: `packages/core/src/spotdl_core/providers/urls.py`
- Create: `packages/core/tests/providers/test_urls.py`
- Modify: `packages/core/src/spotdl_core/providers/__init__.py` (export `PlatformRef`, `parse`, `resolve_shortlink`, `strip_intl`)

**Interfaces produced:**
- `PlatformRef` (frozen dataclass): `provider: ProviderId`, `entity_type: EntityType`, `entity_id: str`, `url: str | None = None`.
- `def parse(value: str) -> PlatformRef` — parses a URL **or** a `provider:type:id` string. Raises `UnsupportedURL` if nothing matches.
- `async def resolve_shortlink(client: httpx.AsyncClient, value: str) -> str` — for short domains (`spotify.link`, `deezer.page.link`, `deezer.app.link`), issues a redirect-following request and returns the final URL; returns `value` unchanged for non-short inputs.
- `def strip_intl(url: str) -> str` — removes a `/intl-xx/` locale segment.

**Contract vs freedom:** The **accepted-forms table below is a CONTRACT** — every listed input must parse to exactly the listed `(provider, entity_type, entity_id)`, and every "reject" case must raise `UnsupportedURL`. Regex/implementation details are free. `entity_id` is the raw platform id (no URL, no query string). Query strings (`?si=`, `?utm=`) and trailing slashes are ignored. Parsing is **offline and synchronous**; only `resolve_shortlink` touches the network.

**Accepted-forms table (CONTRACT):**

| Input | provider | entity_type | entity_id |
|---|---|---|---|
| `spotify:track:6rqhFgbbKwnb9MLmUQDhG6` | SPOTIFY | TRACK | `6rqhFgbbKwnb9MLmUQDhG6` |
| `spotify:album:4aawyAB9vmqN3uQ7FjRGTy` | SPOTIFY | ALBUM | `4aawyAB9vmqN3uQ7FjRGTy` |
| `spotify:artist:0OdUWJ0sBjDrqHygGUXeCF` | SPOTIFY | ARTIST | `0OdUWJ0sBjDrqHygGUXeCF` |
| `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M` | SPOTIFY | PLAYLIST | `37i9dQZF1DXcBWIGoYBM5M` |
| `https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6` | SPOTIFY | TRACK | `6rqhFgbbKwnb9MLmUQDhG6` |
| `https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6?si=abc` | SPOTIFY | TRACK | `6rqhFgbbKwnb9MLmUQDhG6` |
| `https://open.spotify.com/intl-de/track/6rqhFgbbKwnb9MLmUQDhG6` | SPOTIFY | TRACK | `6rqhFgbbKwnb9MLmUQDhG6` |
| `https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy` | SPOTIFY | ALBUM | `4aawyAB9vmqN3uQ7FjRGTy` |
| `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M` | SPOTIFY | PLAYLIST | `37i9dQZF1DXcBWIGoYBM5M` |
| `https://open.spotify.com/artist/0OdUWJ0sBjDrqHygGUXeCF` | SPOTIFY | ARTIST | `0OdUWJ0sBjDrqHygGUXeCF` |
| `deezer:track:3135556` | DEEZER | TRACK | `3135556` |
| `https://www.deezer.com/track/3135556` | DEEZER | TRACK | `3135556` |
| `https://www.deezer.com/en/album/302127` | DEEZER | ALBUM | `302127` |
| `https://deezer.com/us/playlist/1234` | DEEZER | PLAYLIST | `1234` |
| `https://www.deezer.com/artist/27` | DEEZER | ARTIST | `27` |
| `https://music.apple.com/us/album/1989/1440935467?i=1440935485` | ITUNES | TRACK | `1440935485` |
| `https://music.apple.com/gb/album/1989/1440935467` | ITUNES | ALBUM | `1440935467` |
| `https://music.apple.com/us/artist/taylor-swift/159260351` | ITUNES | ARTIST | `159260351` |
| `https://music.apple.com/us/playlist/todays-hits/pl.abc123` | ITUNES | PLAYLIST | `pl.abc123` |
| `itunes:track:1440935485` | ITUNES | TRACK | `1440935485` |
| `https://musicbrainz.org/recording/2f3d8f2e-...-uuid` | MUSICBRAINZ | TRACK | `2f3d8f2e-...-uuid` |
| `https://musicbrainz.org/release/<uuid>` | MUSICBRAINZ | ALBUM | `<uuid>` |
| `https://musicbrainz.org/artist/<uuid>` | MUSICBRAINZ | ARTIST | `<uuid>` |
| `musicbrainz:track:<uuid>` | MUSICBRAINZ | TRACK | `<uuid>` |
| `https://music.youtube.com/watch?v=dQw4w9WgXcQ` | YTMUSIC | TRACK | `dQw4w9WgXcQ` |
| `https://music.youtube.com/playlist?list=OLAK5uy_xxx` | YTMUSIC | ALBUM | `OLAK5uy_xxx` |
| `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | YOUTUBE | TRACK | `dQw4w9WgXcQ` |
| `https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx` | YOUTUBE | TRACK | `dQw4w9WgXcQ` |
| `https://youtu.be/dQw4w9WgXcQ` | YOUTUBE | TRACK | `dQw4w9WgXcQ` |
| `https://www.youtube.com/playlist?list=PLxxx` | YOUTUBE | PLAYLIST | `PLxxx` |
| `youtube:track:dQw4w9WgXcQ` | YOUTUBE | TRACK | `dQw4w9WgXcQ` |
| `https://soundcloud.com/artist/track-slug` | SOUNDCLOUD | TRACK | `artist/track-slug` |
| `https://soundcloud.com/artist/sets/playlist-slug` | SOUNDCLOUD | PLAYLIST | `artist/sets/playlist-slug` |
| `https://soundcloud.com/artist` | SOUNDCLOUD | ARTIST | `artist` |
| `https://artist.bandcamp.com/track/song-slug` | BANDCAMP | TRACK | `artist/track/song-slug` |
| `https://artist.bandcamp.com/album/album-slug` | BANDCAMP | ALBUM | `artist/album/album-slug` |
| `https://piped.video/watch?v=dQw4w9WgXcQ` | PIPED | TRACK | `dQw4w9WgXcQ` |
| `<11-char id>` alone, e.g. `dQw4w9WgXcQ` | *(reject unless prefixed)* | — | raise `UnsupportedURL` |
| `provider:type:id` with unknown provider/type | — | — | raise `UnsupportedURL` |
| `https://example.com/foo` | — | — | raise `UnsupportedURL` |
| `""` / whitespace | — | — | raise `UnsupportedURL` |

Notes for the `provider:type:id` grammar: `provider` must be a valid `ProviderId` value; `type` must be a valid `EntityType` value (`track|album|artist|playlist`); Spotify URIs use the same grammar (`spotify:track:…`). SoundCloud/Bandcamp `entity_id` intentionally encodes the path (there is no numeric id in the URL); the SoundCloud/Bandcamp providers (Tasks 10) re-expand it. `strip_intl` runs before matching so `/intl-de/` (and any `/intl-xx/`) is transparent for all hosts.

- [ ] **Step 1: Write `packages/core/tests/providers/test_urls.py`**

Parametrize over the full accepted-forms table above: one test asserting each accepted input yields the exact `PlatformRef` fields, one test asserting each reject case raises `UnsupportedURL`. Add:
```python
def test_strip_intl_removes_locale_segment() -> None:
    assert strip_intl("https://open.spotify.com/intl-de/track/X") == "https://open.spotify.com/track/X"
    assert strip_intl("https://open.spotify.com/track/X") == "https://open.spotify.com/track/X"

@pytest.mark.parametrize("host", ["spotify.link", "deezer.page.link"])
async def test_resolve_shortlink_follows_redirect(respx_mock, host: str) -> None:
    # respx: GET https://{host}/abc -> 302 Location: real canonical URL; assert returned == real URL
    ...

async def test_resolve_shortlink_passthrough_for_non_short_url() -> None:
    # a normal open.spotify.com URL is returned unchanged without any request
    ...
```
Use the `respx` fixture (dev dep). Mark none of these `network`.

- [ ] **Step 2: RED** — `uv run pytest packages/core/tests/providers/test_urls.py -v` fails on import.

- [ ] **Step 3: Implement `urls.py`.** `PlatformRef` as a frozen `@dataclass(slots=True)`. Implement `strip_intl` (regex `re.sub(r"/intl-[a-z]{2}/", "/", url)`), a `provider:type:id` branch (split on `:`, validate against `ProviderId`/`EntityType`), then an ordered list of `(compiled_regex, provider, type_resolver)` entries covering the table. `type_resolver` may be a fixed `EntityType` or a callable (Apple Music: `?i=` present → TRACK else ALBUM; YouTube: `watch?v=`/`youtu.be` → TRACK, `playlist?list=` → PLAYLIST). Strip query/fragment for id extraction except where the id lives in the query (`v=`, `list=`, Apple `i=`). Raise `UnsupportedURL(value)` at the end. `resolve_shortlink` checks the host against `{"spotify.link", "deezer.page.link", "deezer.app.link"}`; if matched, `resp = await client.get(value, follow_redirects=True)` and return `str(resp.url)`; else return `value`.

- [ ] **Step 4: GREEN + gates.** All url tests pass; `make check` green. Export the four names from `providers/__init__.py`.

- [ ] **Step 5: Commit**
```bash
git add packages/core/src/spotdl_core/providers/urls.py packages/core/tests/providers/test_urls.py packages/core/src/spotdl_core/providers/__init__.py
git commit -m "feat(core/providers): single-source URL and provider:type:id parsing"
```

---

### Task 3: `core.providers.base` — capability Protocols, `ResolvedEntity`, `HttpProvider`

**Files:**
- Create: `packages/core/src/spotdl_core/providers/base.py`
- Create: `packages/core/tests/providers/test_base.py`
- Modify: `providers/__init__.py` (export the Protocols, `ResolvedEntity`, `HttpProvider`)

**Interfaces produced (the plugin contract for every provider and for the registry):**

**Contract vs freedom:** Everything in this file is a **CONTRACT**. Protocol method names, signatures, and return types must match exactly — providers (Tasks 6–11) and the registry (Task 5) depend on them, and Plans 3/5 consume them. `HttpProvider` is a concrete helper base; its `__init__(client)` and `aclose()` are contract, but subclasses are free in everything else.

- [ ] **Step 1: Write `packages/core/tests/providers/test_base.py`**

Define fake providers and assert `runtime_checkable` behavior:
```python
from typing import ClassVar
from spotdl_core.model import AudioCandidate, EntityType, Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.base import (
    Enriches, ProvidesAudio, ProvidesLyrics, Provider, ResolvedEntity, Resolves, Searches, HttpProvider,
)
from spotdl_core.providers.urls import PlatformRef


class FakeResolver:
    id: ClassVar[ProviderId] = ProviderId.DEEZER
    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        return ResolvedEntity(provider=self.id, provider_id=ref.entity_id,
                              entity_type=EntityType.TRACK,
                              track=Track(name="x", artists=("a",), duration_ms=1000))


def test_resolver_satisfies_resolves_and_provider() -> None:
    r = FakeResolver()
    assert isinstance(r, Resolves)
    assert isinstance(r, Provider)
    assert not isinstance(r, ProvidesAudio)


def test_resolved_entity_is_frozen() -> None:
    e = ResolvedEntity(provider=ProviderId.DEEZER, provider_id="1", entity_type=EntityType.TRACK)
    with pytest.raises(Exception):
        e.name = "y"  # type: ignore[misc]


async def test_resolved_entity_track_roundtrip() -> None:
    r = FakeResolver()
    e = await r.resolve(PlatformRef(ProviderId.DEEZER, EntityType.TRACK, "1"))
    assert e.track is not None and e.track.name == "x"
```
Also: a fake implementing `ProvidesLyrics` returning `Lyrics(...)`, asserting `isinstance(x, ProvidesLyrics)`; a bare object asserting it is **not** any capability.

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `base.py`** — **CONTRACT (match exactly)**

```python
from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict

from spotdl_core.model import (
    AlbumRef,
    ArtistRef,
    AudioCandidate,
    EntityType,
    Lyrics,
    ProviderId,
    Track,
)
from spotdl_core.providers.urls import PlatformRef


class ResolvedEntity(BaseModel):
    """Provider-layer result of resolving one URL/ref. The populated fields
    depend on `entity_type`:
      TRACK    -> `track` set; `tracks` empty.
      ALBUM    -> `album` set; `tracks` = album track listing.
      ARTIST   -> `artist` set; `tracks` = top tracks (may be empty).
      PLAYLIST -> `name` set; `tracks` = playlist track listing.
    """

    model_config = ConfigDict(frozen=True)

    provider: ProviderId
    provider_id: str
    entity_type: EntityType
    track: Track | None = None
    album: AlbumRef | None = None
    artist: ArtistRef | None = None
    name: str | None = None
    tracks: tuple[Track, ...] = ()


@runtime_checkable
class Provider(Protocol):
    """Every provider exposes its stable id."""

    id: ClassVar[ProviderId]


@runtime_checkable
class Resolves(Provider, Protocol):
    """URL / provider:type:id -> metadata."""

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity: ...


@runtime_checkable
class Searches(Provider, Protocol):
    """Free-text search -> tracks."""

    async def search(self, query: str, *, limit: int = 10) -> list[Track]: ...


@runtime_checkable
class Enriches(Provider, Protocol):
    """Return a copy of `track` with missing fields filled; never removes data."""

    async def enrich(self, track: Track) -> Track: ...


@runtime_checkable
class ProvidesAudio(Provider, Protocol):
    """Return downloadable audio candidates for a track (best-first)."""

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]: ...


@runtime_checkable
class ProvidesLyrics(Provider, Protocol):
    """Return lyrics for a track, or None if not found (None is not an error)."""

    async def lyrics(self, track: Track) -> Lyrics | None: ...


class HttpProvider:
    """Concrete base for providers backed by a single injected httpx client.
    The registry owns the client's lifetime and calls `aclose()`."""

    id: ClassVar[ProviderId]

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def aclose(self) -> None:
        await self._client.aclose()
```

Note for implementers: `runtime_checkable` checks only *presence* of members, not signatures — sufficient for registry capability filtering. Capability Protocols inherit `Provider` so they also require `id`.

- [ ] **Step 4: GREEN + gates.** `make check` green. Export Protocols, `ResolvedEntity`, `HttpProvider` from `providers/__init__.py`.

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(core/providers): capability Protocols, ResolvedEntity, HttpProvider base"
```

---

### Task 4: HTTP plumbing — client factory + `request_json` with retry & error mapping

**Files:**
- Create: `packages/core/src/spotdl_core/providers/http.py`
- Create: `packages/core/tests/providers/test_http.py`
- Modify: `providers/__init__.py` (export `create_client`, `request_json`, `DEFAULT_USER_AGENT`)

**Interfaces produced:**
- `DEFAULT_USER_AGENT: str` — e.g. `"spotdl/5.0 (+https://github.com/spotDL/spotify-downloader)"`.
- `def create_client(*, user_agent: str = DEFAULT_USER_AGENT, base_url: str = "", timeout: float = 15.0, headers: Mapping[str,str] | None = None, follow_redirects: bool = True) -> httpx.AsyncClient` — no global state; each call returns a fresh client with connect-timeout 5s and the given per-provider User-Agent. **Transport-level retries are 0** (`httpx.AsyncHTTPTransport(retries=0)`, the httpx default): `request_json`'s tenacity loop is the *single* owner of all retrying, so the worst-case attempt count is exactly `retries` — no multiplicative hidden retries.
- `async def request_json(client, method, url, *, provider: ProviderId, retries: int = 3, retry_statuses: frozenset[int] = frozenset({429,500,502,503,504}), expect_ok_body: Callable[[Any], None] | None = None, **kwargs) -> Any` — performs the request with exponential backoff (tenacity), returns parsed JSON, and maps failures to the taxonomy.

**Contract vs freedom:** The **error-mapping table is a CONTRACT** (Plan 5 relies on these types). Backoff timing, tenacity wiring, and `create_client` internals are free.

**Error-mapping table (CONTRACT):**

| Condition | Behavior |
|---|---|
| 2xx with JSON body | return parsed JSON |
| 404 | raise `EntityNotFound(provider=provider)` (no retry) |
| 401 or 403 | raise `ProviderAuthError(provider=provider)` (no retry) |
| status in `retry_statuses` | retry up to `retries` with backoff; if still failing and last status is 429 → `RateLimited(provider=provider, retry_after=<Retry-After header seconds or None>)`; otherwise → `ProviderUnavailable(provider=provider)` |
| `httpx.ConnectError` / `httpx.ConnectTimeout` / `httpx.ReadTimeout` / `httpx.TransportError` | retry; on exhaustion → `ProviderUnavailable(provider=provider)` |
| 2xx but body is not JSON | raise `ProviderUnavailable(provider=provider)` |
| `expect_ok_body` callback provided and it raises `EntityNotFound` | propagate (used by APIs that signal "not found" inside a 200 body, e.g. Deezer's `{"error": {...}}`) |

- [ ] **Step 1: Write `packages/core/tests/providers/test_http.py`** using `respx`:
  - `test_request_json_returns_body_on_200`
  - `test_404_raises_entity_not_found`
  - `test_401_raises_provider_auth_error`
  - `test_429_then_200_succeeds` (respx side effect: first 429 then 200; assert returns body; assert 2 calls)
  - `test_persistent_429_raises_rate_limited_with_retry_after` (respx always 429 with `Retry-After: 2`; assert `RateLimited.retry_after == 2.0`)
  - `test_persistent_500_raises_provider_unavailable`
  - `test_connect_error_raises_provider_unavailable`
  - `test_non_json_200_raises_provider_unavailable`
  - `test_expect_ok_body_can_raise_entity_not_found`
  - `test_create_client_sets_user_agent` (make a request through respx, assert the `User-Agent` header)
  Keep `retries` low (e.g. 2) and stub `tenacity` wait to near-zero (inject a `wait`/`sleep` override or pass a tiny multiplier) so the suite is fast. None marked `network`.

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `http.py`.** Use `tenacity` (`AsyncRetrying` with `stop_after_attempt`, `wait_exponential` capped ~2s, `retry_if_exception_type` for a private `_Retryable`). Inside the attempt: issue request, inspect `response.status_code`, translate per the table (raising terminal taxonomy errors for non-retryable, raising `_Retryable` carrying the last status for retryable), parse `response.json()` catching `ValueError`. After the retry loop exhausts, convert the last retryable state to `RateLimited`/`ProviderUnavailable`. Parse `Retry-After` as float seconds. Make the backoff wait injectable for tests (e.g. `_sleep` param defaulting to tenacity's).

- [ ] **Step 4: GREEN + gates.** `make check` green.

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(core/providers): async httpx client factory and request_json error mapping"
```

---

### Task 5: `core.providers.registry` — registration, lazy lookup, capability filtering, ordering

**Files:**
- Create: `packages/core/src/spotdl_core/providers/registry.py`
- Create: `packages/core/tests/providers/test_registry.py`
- Modify: `providers/__init__.py` (export `ProviderRegistry`, `ProviderSpec`, `ProviderContext`, `SpotifyConfig`, `PROVIDER_ORDER`)

**Interfaces produced (the server's single entry point in Plan 5):**

**Contract vs freedom:** The **public API and `PROVIDER_ORDER` are a CONTRACT.** The `build_default_registry` wiring lands incrementally (a stub here; real factories are appended by Tasks 6–11 and finalized in Task 12). Internal caching/introspection is free.

- [ ] **Step 1: Write `packages/core/tests/providers/test_registry.py`** using **fake providers only** (no network, no real provider modules):
  - `test_capable_returns_matching_providers_in_provider_order`: register three fakes out of order (e.g. a `ProvidesLyrics` fake with id GENIUS, a `Resolves` fake with id SPOTIFY, a `Resolves+Searches` fake with id DEEZER); assert `registry.capable(Resolves)` returns `[spotify, deezer]` (PROVIDER_ORDER order) and `capable(ProvidesLyrics)` returns `[genius]`.
  - `test_get_constructs_lazily_and_caches`: a factory counting its invocations; `get(id)` twice returns the same instance and factory ran once.
  - `test_get_unregistered_raises_key_error` (per the CONTRACT block below).
  - `test_get_wraps_factory_failure_as_provider_unavailable`: factory raises `ImportError`; `get(id)` raises `ProviderUnavailable` with `.provider` set.
  - `test_failed_construction_is_cached_for_registry_lifetime`: a counting factory that raises; two `get(id)` calls both raise `ProviderUnavailable` but the factory ran exactly once; the same cached error is visible in `registry.unavailable`.
  - `test_capable_skips_providers_whose_factory_fails`: one good `Resolves` fake + one whose factory raises `ImportError`; `capable(Resolves)` returns only the good one (isolation), and the skipped ids are retrievable via `registry.unavailable` (a property returning `dict[ProviderId, ProviderError]`) — this satisfies "no silent fallbacks": the failure is recorded and surfaceable, not swallowed.
  - `test_aclose_closes_constructed_providers`: fakes with an async `aclose` recording calls; only constructed ones are closed; `async with ProviderRegistry(...)` closes on exit.
  - `test_registry_module_imports_without_provider_deps`: `import spotdl_core.providers.registry` succeeds (module has no top-level provider third-party imports).

- [ ] **Step 2: RED.**

- [ ] **Step 3: Implement `registry.py`** — **CONTRACT for the shapes below:**

```python
PROVIDER_ORDER: tuple[ProviderId, ...] = (
    ProviderId.SPOTIFY, ProviderId.DEEZER, ProviderId.ITUNES, ProviderId.MUSICBRAINZ,
    ProviderId.YTMUSIC, ProviderId.YOUTUBE, ProviderId.SOUNDCLOUD, ProviderId.BANDCAMP,
    ProviderId.PIPED, ProviderId.LRCLIB, ProviderId.GENIUS, ProviderId.MUSIXMATCH,
    ProviderId.AZLYRICS,
)

@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str | None = None
    client_secret: str | None = None
    prefer_anonymous: bool = True            # True: try anonymous first, cc fallback; False: cc first, anonymous fallback
    totp_secret_override: str | None = None  # overrides the pinned anonymous-token TOTP secret (no code release needed)

    @classmethod
    def from_env(cls) -> "SpotifyConfig": ...
    # Reads: SPOTDL_SPOTIFY_CLIENT_ID, SPOTDL_SPOTIFY_CLIENT_SECRET,
    # SPOTDL_SPOTIFY_TOTP_SECRET (-> totp_secret_override),
    # SPOTDL_SPOTIFY_PREFER_ANONYMOUS ("0"/"false" -> False). Unset vars keep defaults.
    # CONTRACT: the pinned TOTP secret is only a *default*; operators must be able to
    # rotate it via SPOTDL_SPOTIFY_TOTP_SECRET without a release (spec §1: no
    # hardcoded-shared-secret failure mode).

@dataclass(frozen=True)
class ProviderContext:
    user_agent: str = DEFAULT_USER_AGENT
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)
    soundcloud_client_id: str | None = None
    genius_token: str | None = None
    piped_instances: tuple[str, ...] = DEFAULT_PIPED_INSTANCES
    ytmusic_language: str = "en"

# factory receives the context and returns a constructed provider
ProviderFactory = Callable[[ProviderContext], Provider]

@dataclass(frozen=True)
class ProviderSpec:
    id: ProviderId
    capabilities: frozenset[type]   # e.g. frozenset({Resolves, Searches})
    factory: ProviderFactory

class ProviderRegistry:
    def __init__(self, context: ProviderContext) -> None: ...
    def register(self, spec: ProviderSpec) -> None: ...          # idempotent by id (later wins); raises if id unknown to PROVIDER_ORDER
    def get(self, provider_id: ProviderId) -> Provider: ...       # lazy construct + cache; ProviderUnavailable on factory failure; raises KeyError if the id was never registered (CONTRACT)
    def capable(self, capability: type[C]) -> list[C]: ...        # PROVIDER_ORDER order; construct lazily; skip (record) construction failures
    @property
    def registered(self) -> tuple[ProviderId, ...]: ...           # in PROVIDER_ORDER
    @property
    def unavailable(self) -> dict[ProviderId, ProviderError]: ... # providers whose construction failed during capable()/get()
    async def aclose(self) -> None: ...                           # aclose() every constructed provider that has it
    async def __aenter__(self) -> "ProviderRegistry": ...
    async def __aexit__(self, *exc: object) -> None: ...
```

Rules (CONTRACT): `capabilities` is declared in the spec so `capable()` can filter **without importing the provider module** (isolation) — it constructs only the matching specs, lazily. `get()`/`capable()` wrap any exception from the factory in `ProviderUnavailable(provider=id)` and store it in `unavailable`; `get()` re-raises, `capable()` skips. **Unregistered id → `KeyError` from `get()`** (distinct from "registered but unavailable"). **Failure caching:** a construction failure is cached for the lifetime of the registry instance — subsequent `get()`/`capable()` calls return/skip using the cached `ProviderUnavailable` without re-running the factory; recovery requires building a new registry (the server, Plan 5, constructs one registry per process/startup, so a restart or config reload retries). Ordering: sort matched specs by `PROVIDER_ORDER.index(id)`. `capable(C)` returns instances (already constructed); `cast` to `list[C]`. Include a `build_default_registry(context) -> ProviderRegistry` that, in this task, registers **nothing** yet (or is a documented stub) — Tasks 6–11 append their `reg.register(...)` calls and Task 12 asserts the full set.

- [ ] **Step 4: GREEN + gates.** `make check` green.

- [ ] **Step 5: Commit**
```bash
git commit -am "feat(core/providers): capability registry with deterministic ordering and lazy isolation"
```

---

### Task 6: Spotify metadata provider (anonymous-token primary + client-credentials fallback, one interface)

**Files:**
- Create: `packages/core/src/spotdl_core/providers/metadata/__init__.py`, `packages/core/src/spotdl_core/providers/metadata/spotify.py`
- Create: `packages/core/tests/providers/fixtures/spotify/{track,album,search,token_anon,token_cc}.json`
- Create: `packages/core/tests/providers/test_spotify.py`
- Modify: `registry.py` `build_default_registry` (register Spotify spec with a lazy factory)

**Interfaces produced:**
- `class SpotifyProvider(HttpProvider)` — `id = ProviderId.SPOTIFY`; implements `Resolves`, `Searches`, `Enriches`. Constructor: `SpotifyProvider(client: httpx.AsyncClient, auth: SpotifyAuth)`.
- `class SpotifyAuth(Protocol)`: `async def bearer_token(self) -> str`.
- `class AnonymousSpotifyAuth` and `class ClientCredentialsSpotifyAuth` implementing `SpotifyAuth`.
- `class LayeredSpotifyAuth(SpotifyAuth)` — ordering follows `SpotifyConfig.prefer_anonymous` (True: anonymous → client-credentials; False: client-credentials → anonymous). **Fallback triggers on any breakage of the primary path**, not just auth rejection: `ProviderAuthError` (401/403), `ProviderUnavailable` (transport failure / repeated 5xx), and malformed token payloads. Both auth implementations must **validate the token payload shape** (a non-empty `str` access token and a plausible expiry) and raise `ProviderAuthError` on a 2xx with a garbage/empty body — never trust an arbitrary 2xx. Records which path is live via `.live_path` (`"anonymous" | "client_credentials"`, for `degraded_sources`, spec §10). Falls back only if the secondary is configured; raises the primary's error otherwise.
- Module-level pure mappers: `map_track(payload: dict) -> Track`, `map_album(payload, tracks) -> ResolvedEntity`, `map_search(payload) -> list[Track]`.

**Design decision (contract-relevant):** Both auth paths yield a **bearer token used against the standard Web API** `https://api.spotify.com/v1`. This unifies the two behind one interface and means the field mapping is identical and **ISRC is present** (`external_ids.isrc` is returned by `/v1/tracks/{id}` regardless of token origin). This deliberately avoids the `spotapi` GraphQL pathfinder approach (which lacks ISRC and requires scraping SHA256 query hashes from the web-player JS). Reference for the anonymous-token TOTP flow: `spotapi/client.py` (external, `TzurSoffer/SpotAPI`) — endpoint `GET https://open.spotify.com/api/token?reason=init&productType=web-player&totp=<code>&totpVer=<ver>`; TOTP built with `pyotp.TOTP(secret).now()` where `secret` is derived by an XOR transform of a pinned secret bytearray (fallback pinned in code; refreshable). Reference for client-credentials: `spotdl-v4-reference/spotdl/utils/spotify.py` — `POST https://accounts.spotify.com/api/token`, `grant_type=client_credentials`, HTTP Basic `client_id:client_secret`.

**Endpoints used (REST, both auth paths):**
- Track: `GET /v1/tracks/{id}`
- Album: `GET /v1/albums/{id}` then paginate `GET /v1/albums/{id}/tracks?offset=&limit=50`
- Artist: `GET /v1/artists/{id}` + `GET /v1/artists/{id}/albums?...` (top tracks via `GET /v1/artists/{id}/top-tracks?market=US`)
- Playlist: `GET /v1/playlists/{id}` then paginate `.tracks.next`
- Search: `GET /v1/search?q=&type=track&limit=`
- Enrich: fetch `/v1/tracks/{id}` (or `/v1/artists/{id}` for genres) and fill missing `isrc`, `genres`, cover.

**Field paths → `Track`:** `name`, `id`→`provider_id`, `duration_ms` (kept in ms — model stores ms), `explicit`, `external_ids.isrc`→`isrc`, `disc_number`, `track_number`, `artists[].name`→`artists`, `album.name`+`album.release_date[:4]`+largest `album.images[].url`→`AlbumRef`, `album.total_tracks`. `popularity` is captured only for `AudioCandidate` contexts (not on `Track`).

**Contract vs freedom:** `SpotifyAuth` Protocol and `SpotifyProvider` public constructor/capabilities are contract. The exact TOTP secret handling and pagination are implementation (reference-guided). Mapper field paths above are the contract the fixtures test.

- [ ] **Step 1: Record fixtures.** Write a small `@pytest.mark.network` helper test (or a `scripts/` snippet) that, given creds or the anon flow, hits `/v1/tracks/{id}`, `/v1/albums/{id}` (+tracks page), `/v1/search`, and saves raw JSON to `fixtures/spotify/`. Also save one anonymous token response (`token_anon.json`) and one client-credentials token response (`token_cc.json`). Redact nothing structural; you may blank real access-token strings. These fixtures are checked in and are the source of truth for parse tests.

- [ ] **Step 2: Write `test_spotify.py`** (all non-network except one guarded live test):
  - Pure mapper tests from fixtures: `test_map_track_from_fixture` (assert name/artists/duration_ms/isrc/track_number/album), `test_map_album_sets_entity_type_and_tracks`, `test_map_search_returns_tracks`.
  - `AnonymousSpotifyAuth` via respx: `test_anon_auth_fetches_and_caches_token` (respx serves `open.spotify.com/api/token`; assert token returned; second call within expiry does not re-request), `test_anon_auth_refreshes_before_expiry`.
  - `ClientCredentialsSpotifyAuth` via respx: `test_cc_auth_posts_basic_and_returns_token`.
  - `AnonymousSpotifyAuth` payload validation: `test_anon_auth_rejects_malformed_token_payload` (respx serves 200 with `{}` / missing `accessToken` → `ProviderAuthError`).
  - `LayeredSpotifyAuth`: `test_layered_falls_back_to_cc_on_anon_auth_error` (anon token endpoint 401 → cc used; `.live_path == "client_credentials"`), `test_layered_falls_back_to_cc_on_anon_transport_failure` (anon endpoint raises `httpx.ConnectError` via respx side effect → `ProviderUnavailable` internally → cc used), `test_layered_falls_back_to_cc_on_malformed_anon_payload` (200-with-garbage body → cc used), `test_layered_prefers_cc_when_prefer_anonymous_false` (cc tried first; anon endpoint never called), `test_layered_raises_when_both_fail`.
  - Provider via respx (inject a stub `auth` returning a fixed token): `test_resolve_track_url_returns_track`, `test_resolve_album_paginates`, `test_search_returns_tracks`, `test_resolve_404_raises_entity_not_found`.
  - `@pytest.mark.network def test_live_anonymous_resolve_known_track()` — resolve `spotify:track:6rqhFgbbKwnb9MLmUQDhG6`, assert `track.isrc` present and `duration_ms > 0`. Excluded from `make check`.

- [ ] **Step 3: RED.**

- [ ] **Step 4: Implement `spotify.py`.** Pure mappers first (make the fixture tests pass), then auth classes (respx tests), then `SpotifyProvider` using `resolve(ref)` dispatch on `ref.entity_type`, `request_json` for all calls with `provider=ProviderId.SPOTIFY`, and `Authorization: Bearer <await auth.bearer_token()>` per request. TOTP secret resolution order (CONTRACT, per `SpotifyConfig` in Task 5): `ctx.spotify.totp_secret_override` (populated from `SPOTDL_SPOTIFY_TOTP_SECRET` by `SpotifyConfig.from_env`) → the pinned default from `spotapi/client.py`; the pinned value is only a default and must be rotatable without a release. `AnonymousSpotifyAuth.__init__` takes `totp_secret: str | None = None`. Validate token payloads (non-empty `accessToken` str + expiry) before accepting; refresh token 30s before `accessTokenExpirationTimestampMs`.

- [ ] **Step 5: Register in `build_default_registry`** with a **lazy** factory:
```python
def _spotify_factory(ctx: ProviderContext) -> Provider:
    from spotdl_core.providers.metadata.spotify import build_spotify_provider
    return build_spotify_provider(ctx)
reg.register(ProviderSpec(ProviderId.SPOTIFY, frozenset({Resolves, Searches, Enriches}), _spotify_factory))
```
`build_spotify_provider(ctx)` creates the client via `create_client(user_agent=ctx.user_agent, base_url="https://api.spotify.com")` and a `LayeredSpotifyAuth` from `ctx.spotify`.

- [ ] **Step 6: GREEN + gates.** `uv run pytest packages/core/tests/providers/test_spotify.py` (network deselected) green; `make check` green.

- [ ] **Step 7: Commit**
```bash
git commit -am "feat(core/providers): Spotify metadata (anon-token + client-credentials behind one interface)"
```

---

### Task 7: Deezer + iTunes metadata providers (open APIs)

**Files:**
- Create: `providers/metadata/deezer.py`, `providers/metadata/itunes.py`
- Create fixtures: `fixtures/deezer/{track,album,search}.json`, `fixtures/itunes/{search,lookup_track,lookup_album}.json`
- Create tests: `test_deezer.py`, `test_itunes.py`
- Modify: `registry.py` `build_default_registry` (register both, lazy factories)

**Deezer (`DeezerProvider`, `id = DEEZER`, implements `Resolves`, `Searches`, `Enriches`):**
- Base `https://api.deezer.com`, no auth. Endpoints: `/track/{id}`, `/album/{id}` (tracks under `.tracks.data[]`, re-fetch each `/track/{id}` for full fields), `/artist/{id}` + `/artist/{id}/top?limit=100`, `/playlist/{id}`, `/search/track?q=<quoted>&limit=`.
- Deezer signals not-found via **HTTP 200 with `{"error": {"message": "..."}}`** — pass an `expect_ok_body` to `request_json` that raises `EntityNotFound` when `data.get("error")` is present.
- Field paths → `Track`: `title`→name; `artist.name` + `contributors[].name`→artists; `album.title`+`album.cover_xl`+year from `album.release_date[:4]`→`AlbumRef`; **`duration` is SECONDS → multiply by 1000 for `duration_ms`**; `isrc`, `explicit_lyrics`→explicit, `disk_number`, `track_position`→track_number.

**iTunes (`ITunesProvider`, `id = ITUNES`, implements `Searches`, `Resolves`, `Enriches`):**
- Search: `GET https://itunes.apple.com/search?term=<quote_plus>&media=music&entity=song&limit=`. Lookup (for `resolve`): `GET https://itunes.apple.com/lookup?id={id}` (track/album/artist); expand an album's tracks with `?id={collectionId}&entity=song`. No auth.
- Not-found: iTunes returns `{"resultCount": 0, "results": []}` — treat empty results as `EntityNotFound` on `resolve`, `[]` on `search`.
- Field paths → `Track`: `trackName`→name; `artistName`→artists; `collectionName`→album; **`trackTimeMillis` is MS → `duration_ms` directly**; `artworkUrl100` upgraded `100x100`→`600x600` for cover; `releaseDate[:4]`→year; `trackExplicitness == "explicit"`→explicit; `primaryGenreName`→genres. **No ISRC** from iTunes (leave `isrc=None`).
- URL resolve relies on `PlatformRef` from Task 2 (`music.apple.com/...` → ITUNES with the numeric id); use the **Lookup API** by id rather than scraping `music.apple.com` (cleaner, no bs4, no JSON-LD — a deliberate improvement over the reference scraper).

**Contract vs freedom:** Duration-unit handling (Deezer ×1000, iTunes as-is) and the "200-body error" handling for Deezer are contract-critical (they are the classic mapping bugs). Everything else is implementation, reference-guided by `sources/deezer.py` and `sources/apple_music.py`.

- [ ] **Step 1: Record fixtures** (network helper or manual `curl` saved to JSON) for the endpoints above.
- [ ] **Step 2: Write tests.** Pure mapper tests from fixtures (assert the duration units especially — a `test_deezer_duration_seconds_to_ms` and `test_itunes_duration_is_ms`), respx tests for `resolve`/`search`/not-found (Deezer 200-error body → `EntityNotFound`; iTunes empty → `EntityNotFound`/`[]`), plus one `@pytest.mark.network` live resolve each (`deezer:track:3135556`, `itunes:track:<known>`).
- [ ] **Step 3: RED → Step 4: implement → Step 5: register (lazy factories, caps `{Resolves,Searches,Enriches}`).**
- [ ] **Step 6: GREEN + gates.** `make check` green.
- [ ] **Step 7: Commit** `feat(core/providers): Deezer and iTunes metadata providers`

---

### Task 8: MusicBrainz metadata provider (open API, 1 rps, mandatory User-Agent)

**Files:**
- Create: `providers/metadata/musicbrainz.py`
- Create fixtures: `fixtures/musicbrainz/{recording,isrc_lookup,search}.json`
- Create test: `test_musicbrainz.py`
- Modify: `registry.py` `build_default_registry`

**Interface (`MusicBrainzProvider`, `id = MUSICBRAINZ`, implements `Resolves`, `Searches`, `Enriches`):**
- Direct `httpx` to `https://musicbrainz.org/ws/2/` with `fmt=json` (no `musicbrainzngs` dep — one httpx path, consistent with the rest). Endpoints:
  - Recording by MBID: `GET /ws/2/recording/{mbid}?fmt=json&inc=artists+releases+isrcs`
  - ISRC lookup (enrich): `GET /ws/2/isrc/{isrc}?fmt=json&inc=artists+releases`
  - Search: `GET /ws/2/recording?query=<lucene>&fmt=json&limit=`; lucene `recording:"{track}" AND artist:"{artist}"` (+ `AND release:"{album}"` when known).
- **User-Agent is mandatory** and descriptive: set it explicitly on the client (`ctx.user_agent`, which already includes a contact URL). MusicBrainz rejects generic/empty UAs.
- **Rate limit 1 request/second** — implement a provider-owned async limiter (an `asyncio.Lock` + monotonic timestamp, or an `asyncio.Semaphore`-based token gate) that guarantees ≥1.0s spacing between outbound MB requests within this provider instance. This is a **contract** requirement of the plan; document it in the module.
- Field paths → `Track`: `title`→name; `artist-credit[].name` (or `.artist.name`)→artists; **`length` is MS → `duration_ms`**; `isrcs[0]` or the looked-up isrc→isrc; first `releases[0].title`+`releases[0].date[:4]`→`AlbumRef`; search score under `score`/`ext:score` (accept ≥ 80 for name lookups).

**Contract vs freedom:** The 1 rps limiter and mandatory UA are contract. Lucene query shaping and merge behavior are implementation (reference `providers/metadata/musicbrainz.py`).

- [ ] **Step 1: Record fixtures** for recording-by-MBID, isrc lookup, and a search response.
- [ ] **Step 2: Write tests.** Pure mapper tests (duration ms, artist-credit flattening, isrc from `isrcs`), respx tests for resolve/search/404, and a `test_rate_limiter_spaces_requests` that patches the clock/sleep and asserts two back-to-back calls are spaced ≥1.0s (inject the sleep function so the test is instant but verifies the gap logic). One `@pytest.mark.network` live recording lookup.
- [ ] **Step 3: RED → Step 4: implement → Step 5: register (caps `{Resolves,Searches,Enriches}`, lazy factory that builds a client with the descriptive UA).**
- [ ] **Step 6: GREEN + gates.** `make check` green.
- [ ] **Step 7: Commit** `feat(core/providers): MusicBrainz metadata provider with 1rps limiter`

---

### Task 9: Audio — YTMusic (metadata + audio) and YouTube (yt-dlp, metadata only)

**Files:**
- Create: `providers/audio/__init__.py`, `providers/audio/ytmusic.py`, `providers/audio/youtube.py`
- Create fixtures: `fixtures/ytmusic/{search_songs,search_videos}.json`, `fixtures/youtube/ytdlp_search.json`
- Create tests: `test_ytmusic.py`, `test_youtube.py`
- Modify: `registry.py` `build_default_registry`

**YTMusic (`YTMusicProvider`, `id = YTMUSIC`, implements `ProvidesAudio`, `Resolves`, `Searches`):**
- Library `ytmusicapi` (`from ytmusicapi import YTMusic` — **lazy**, imported inside the factory / a `_client()` accessor, never at module top level). `ytmusicapi` is synchronous → wrap calls in `asyncio.to_thread`.
- `audio_candidates(track)`: build query from `track.main_artist + " - " + track.name`; call `YTMusic.search(query, filter="songs", limit=limit)` and (if few results) `filter="videos"`. Map each result → `AudioCandidate(provider=YTMUSIC, provider_id=videoId, url=f"https://music.youtube.com/watch?v={videoId}", name=title, artists=tuple(a["name"] for a in artists), duration_ms=parse "m:ss"→ms, album=album.name, verified=(resultType=="song"), popularity=None)`.
- `resolve(ref)` for `music.youtube.com` refs and `search(query)` returning `list[Track]` (from song results).

**YouTube (`YouTubeProvider`, `id = YOUTUBE`, implements `ProvidesAudio`):**
- Uses **yt-dlp for metadata only** (`from yt_dlp import YoutubeDL` — **lazy**). Search via yt-dlp `ytsearch{N}:{query}` with `extract_flat` for speed; each entry → `AudioCandidate(provider=YOUTUBE, provider_id=id, url=webpage_url or https://www.youtube.com/watch?v=id, name=title, artists=(uploader,), duration_ms=duration*1000, verified=False, popularity=view_count)`. Do **not** download audio here (that is Plan 4). Run yt-dlp in `asyncio.to_thread`. Prefer this over Invidious/pytube (both fragile; yt-dlp is already a hard dep and is the download engine).

**Testing note (important):** ytmusicapi and yt-dlp are network libraries with no clean HTTP seam for respx. So: split each provider into a pure `_map_results(raw: list[dict]) -> list[AudioCandidate]` mapper (tested from checked-in JSON fixtures capturing real `YTMusic.search(...)` / yt-dlp `extract_info(...)` output), and a thin fetch method. Unit tests test the mapper from fixtures + test the fetch method with the library call **monkeypatched** to return the fixture. Live `@pytest.mark.network` tests call the real libraries and are excluded from CI.

**Contract vs freedom:** The `_map_results` fixture-tested mappers and the `AudioCandidate` field population (esp. `verified` and duration→ms) are contract. Library invocation details are implementation.

- [ ] **Step 1: Record fixtures** by calling `YTMusic().search(...)` and `YoutubeDL({...}).extract_info("ytsearch5:...", download=False)` once, saving raw JSON.
- [ ] **Step 2: Write tests.** `test_ytmusic_map_songs_sets_verified_true`, `test_ytmusic_map_videos_verified_false`, `test_ytmusic_duration_mmss_to_ms`, `test_ytmusic_audio_candidates_monkeypatched`; `test_youtube_map_from_ytdlp_fixture`, `test_youtube_duration_seconds_to_ms`, `test_youtube_audio_candidates_monkeypatched`. Two `@pytest.mark.network` live searches.
- [ ] **Step 3: RED → Step 4: implement (lazy imports!) → Step 5: register** (YTMusic caps `{ProvidesAudio, Resolves, Searches}`; YouTube caps `{ProvidesAudio}`; both factories lazy-import their library).
- [ ] **Step 6: GREEN + gates.** Verify `import spotdl_core.providers.registry` still works even if ytmusicapi/yt-dlp import were to fail (they are lazy). `make check` green.
- [ ] **Step 7: Commit** `feat(core/providers): YTMusic and YouTube audio providers (metadata via yt-dlp)`

---

### Task 10: Audio — SoundCloud, Bandcamp, Piped

**Files:**
- Create: `providers/audio/soundcloud.py`, `providers/audio/bandcamp.py`, `providers/audio/piped.py`
- Create fixtures: `fixtures/soundcloud/search.json` (raw `__sc_hydration` blob), `fixtures/bandcamp/{search.html,tralbum.json}`, `fixtures/piped/{search,streams}.json`
- Create tests: `test_soundcloud.py`, `test_bandcamp.py`, `test_piped.py`
- Modify: `registry.py` `build_default_registry`

**All three implement `ProvidesAudio` (`audio_candidates(track)`), plus `Resolves` where a public URL maps cleanly.** All are **fragile scrapers / public-instance dependent** — mark them and keep each isolated (lazy `bs4` import inside methods; failures raise `ProviderUnavailable`, never crash the registry).

- **SoundCloud (`id = SOUNDCLOUD`):** No official client_id needed in the scraping approach. Search `GET https://soundcloud.com/search/sounds?q=<quote>`; extract the `__sc_hydration` JSON (regex `window\.__sc_hydration\s*=\s*(\[.*?\]);`) with `bs4`; collect items where `hydratable=="sound"`/`kind=="track"` from `data.collection[]`. Fields: `title`, `user.username`, `duration` (ms → ms as-is; SoundCloud `duration` is already ms), `id`→provider_id, `permalink_url`→url, `playback_count`→popularity. `ctx.soundcloud_client_id` is accepted and, if present, used for the optional API path; otherwise scrape.
- **Bandcamp (`id = BANDCAMP`):** Search `GET https://bandcamp.com/search?q=<quote>&item_type=t`; parse `li.searchresult` with `bs4` for track links. Track detail: fetch the track page and extract the `data-tralbum` / `TralbumData` JSON (regex) → `trackinfo[]`, `current.title`, `artist`, `art_id`, `release_date`. Duration from `trackinfo[0].duration` (seconds → ×1000). Art `https://f4.bcbits.com/img/a{art_id}_10.jpg`.
- **Piped (`id = PIPED`):** `httpx` against a **rotating instance list** `ctx.piped_instances` (default constant `DEFAULT_PIPED_INSTANCES` in `registry.py`, e.g. `("https://pipedapi.kavin.rocks", "https://pipedapi.adminforge.de", ...)`). Health-select an instance via `GET {inst}/healthcheck`; search `GET {inst}/search?q=<query>&filter=videos`; items where `type=="stream"` → `AudioCandidate(provider=PIPED, provider_id=<id from url ?v=>, url=f"{inst}{item['url']}" or canonical youtube watch URL, name=title, artists=(uploaderName,), duration_ms=duration*1000, verified=uploaderVerified, popularity=views)`. If **all** instances fail health/search → `ProviderUnavailable(provider=PIPED)`.

**Testing:** pure mapper functions per provider tested from checked-in fixtures (`_map_soundcloud_hydration`, `_map_bandcamp_tralbum`, `_map_piped_search`). HTTP behavior via `respx` (SoundCloud search HTML, Bandcamp page, Piped healthcheck+search). Piped: `test_piped_falls_over_to_next_instance` (first instance 503, second 200) and `test_piped_all_instances_down_raises_provider_unavailable`. One `@pytest.mark.network` live search each (may be flaky → also `@pytest.mark.network`, never in CI).

**Contract vs freedom:** Duration-unit handling per provider (SoundCloud ms as-is, Bandcamp ×1000, Piped ×1000) and Piped instance-failover → `ProviderUnavailable` are contract. Scrape selectors/regexes are implementation (reference `targets/{soundcloud,bandcamp,piped}.py`) and expected to need maintenance.

- [ ] **Step 1: Record fixtures.** **Step 2: Write tests (mappers + respx + failover).** **Step 3: RED → Step 4: implement (lazy `bs4`) → Step 5: register** (caps: SoundCloud `{ProvidesAudio, Resolves}`, Bandcamp `{ProvidesAudio, Resolves}`, Piped `{ProvidesAudio}`).
- [ ] **Step 6: GREEN + gates.** `make check` green.
- [ ] **Step 7: Commit** `feat(core/providers): SoundCloud, Bandcamp, and Piped audio providers`

---

### Task 11: Lyrics — LRCLIB, Genius, Musixmatch, AZLyrics (each isolated)

**Files:**
- Create: `providers/lyrics/__init__.py`, `providers/lyrics/{lrclib,genius,musixmatch,azlyrics}.py`
- Create fixtures: `fixtures/lrclib/get.json`, `fixtures/genius/{search.json,song_page.html}`, `fixtures/musixmatch/{search.html,lyrics_page.html}`, `fixtures/azlyrics/{search.html,lyrics_page.html}`
- Create tests: `test_lrclib.py`, `test_genius.py`, `test_musixmatch.py`, `test_azlyrics.py`
- Modify: `registry.py` `build_default_registry`

**All implement `ProvidesLyrics` (`async def lyrics(self, track) -> Lyrics | None`). Returning `None` means "not found" (not an error). One provider's scraper breaking must never affect another (separate modules, lazy `bs4`, exceptions confined to that provider → `None` on parse failure, `ProviderUnavailable` on transport failure).**

- **LRCLIB (`id = LRCLIB`, SYNCED):** Direct `httpx` to the documented open API `GET https://lrclib.net/api/get?artist_name=&track_name=&album_name=&duration=` (duration in **seconds** = `track.duration_ms // 1000`); fallback `GET https://lrclib.net/api/search?q=`. Response has `syncedLyrics` (LRC with `[mm:ss.xx]`) and `plainLyrics`. Prefer `syncedLyrics` → `Lyrics(kind=LyricsKind.SYNCED, text=..., source=LRCLIB)`; else `plainLyrics` → `Lyrics(kind=PLAIN, ...)`. 404 → `None`. (Deliberate: direct lrclib.net API instead of the `syncedlyrics` bundle — better isolation, no heavy dep, and it is the only synced source in v1.)
- **Genius (`id = GENIUS`, PLAIN):** Requires `ctx.genius_token`. If token absent, the factory raises `ProviderUnavailable` (so `capable(ProvidesLyrics)` simply omits Genius and records it in `unavailable`). Search `GET https://api.genius.com/search?q=<name> <artist>` with `Authorization: Bearer <token>` → pick best `hits[].result` by title similarity; fetch the result `url` HTML page and scrape lyrics (`div[class^=Lyrics__Container]`, `<br/>`→`\n`). Returns `PLAIN`.
- **Musixmatch (`id = MUSIXMATCH`, PLAIN):** Pure scraping, no token. Search `GET https://www.musixmatch.com/search/<quoted>`; parse `a[href^='/lyrics/']`; fetch lyrics page and join `p.mxm-lyrics__content`. Returns `PLAIN`.
- **AZLyrics (`id = AZLYRICS`, PLAIN):** Pure scraping with the `geo.js` `x` token bootstrap: `GET https://www.azlyrics.com/geo.js` → regex-extract the hidden `x` value; search `GET https://www.azlyrics.com/search/?q=<name>+<artist>&x=<x>`; fetch the result page and pick the longest classless `<div>` as the lyrics body. Returns `PLAIN`.

**Testing:** each provider gets pure-parse tests from its checked-in fixture (`_parse_lrclib(payload)`, `_extract_genius_lyrics(html)`, `_extract_musixmatch(html)`, `_extract_azlyrics(html)`), respx behavior tests (`lyrics()` returns the right `Lyrics` / `None` on 404 / `None` on empty), and a Genius `test_genius_unavailable_without_token`. One `@pytest.mark.network` live lookup per provider (guarded; scrapers are flaky, so keep out of CI).

**Contract vs freedom:** `lyrics()` returning `Lyrics | None`, the LRCLIB SYNCED-vs-PLAIN preference, and Genius-without-token → unavailable are contract. All scrape selectors are implementation and expected to rot (reference `spotdl-v4-reference/spotdl/providers/lyrics/*`).

- [ ] **Step 1: Record fixtures** (one real response/page per provider). **Step 2: Write tests. Step 3: RED → Step 4: implement (separate modules, lazy `bs4`) → Step 5: register** (each cap `{ProvidesLyrics}`; Genius factory lazy + token-gated).
- [ ] **Step 6: GREEN + gates.** `make check` green.
- [ ] **Step 7: Commit** `feat(core/providers): LRCLIB, Genius, Musixmatch, AZLyrics lyrics providers`

---

### Task 12: Wire the default registry + integration smoke test

**Files:**
- Modify: `providers/registry.py` (`build_default_registry` finalized — all 13 providers registered with lazy factories), `providers/__init__.py` (final public API + `__all__`)
- Create: `packages/core/tests/providers/test_registry_integration.py`

**Interface produced:** `build_default_registry(context: ProviderContext) -> ProviderRegistry` returns a registry with every v1 provider registered (via **lazy** factories), ready for the server (Plan 5) to consume by capability.

**Contract vs freedom:** The set of registered providers and their declared capabilities are a contract (asserted by the smoke test). Factory internals were set in Tasks 6–11.

- [ ] **Step 1: Finalize `build_default_registry`.** Ensure all 13 `reg.register(ProviderSpec(...))` calls are present with lazy-import factories. Confirm every factory imports its provider module **inside** the function (grep: no provider submodule imported at `registry.py` top level).

- [ ] **Step 2: Write `test_registry_integration.py`** (all non-network):
  - `test_import_registry_has_no_provider_dep_imports`: `import spotdl_core.providers.registry` succeeds; assert none of `ytmusicapi`, `yt_dlp`, `bs4` are in `sys.modules` merely from importing the registry (guards lazy-import discipline).
  - `test_default_registry_registers_all_providers`: `set(build_default_registry(ProviderContext()).registered) == set(PROVIDER_ORDER)` (all 13).
  - `test_capable_metadata_order`: `[p.id for p in reg.capable(Resolves)]` begins `[SPOTIFY, DEEZER, ITUNES, MUSICBRAINZ, ...]` (order per `PROVIDER_ORDER`; YTMusic/SoundCloud/Bandcamp may also appear after — assert the metadata four lead and the relative order matches `PROVIDER_ORDER`).
  - `test_capable_audio_membership`: `{p.id for p in reg.capable(ProvidesAudio)}` == `{YTMUSIC, YOUTUBE, SOUNDCLOUD, BANDCAMP, PIPED}`.
  - `test_capable_lyrics_membership_without_genius_token`: with `ProviderContext(genius_token=None)`, `{p.id for p in reg.capable(ProvidesLyrics)}` == `{LRCLIB, MUSIXMATCH, AZLYRICS}` and `GENIUS in reg.unavailable`.
  - `test_isolation_broken_provider_does_not_break_others`: monkeypatch one factory (e.g. YTMusic's) to raise `ImportError`; `capable(ProvidesAudio)` still returns the other four and `YTMUSIC in reg.unavailable`.
  - `test_registry_aclose_is_safe_with_no_construction` and `async with build_default_registry(...) as reg: pass` (no network, nothing constructed → clean exit).
  - `@pytest.mark.network async def test_end_to_end_resolve_then_audio()`: `async with build_default_registry(ProviderContext()) as reg:` resolve `spotify:track:6rqhFgbbKwnb9MLmUQDhG6` via `reg.get(SPOTIFY)`, then `reg.get(YTMUSIC).audio_candidates(track)` returns ≥1 candidate. Excluded from CI.

- [ ] **Step 3: RED (integration assertions) → Step 4: adjust wiring to green.**

- [ ] **Step 5: Final gates.** `make check` green. Optionally run `uv run pytest -m network` locally to sanity-check live providers (not required to pass in CI; record which providers are currently healthy).

- [ ] **Step 6: Commit**
```bash
git commit -am "feat(core/providers): wire default registry with all v1 providers + integration smoke test"
```

---

## Self-review notes

- **Spec §5.2 coverage:** capability Protocols `Resolves/Searches/Enriches/ProvidesAudio/ProvidesLyrics` (Task 3); registry with capability lookup + deterministic ordering (Task 5, 12); URL/`provider:type:id`/shortlink/`intl-xx` parsing in one place with a full accepted-forms contract table (Task 2); metadata sources Spotify (anon-token primary + client-credentials fallback behind one `SpotifyAuth` interface), Deezer, iTunes, MusicBrainz (Tasks 6–8); YTMusic-as-metadata (Task 9); audio targets YTMusic/YouTube/SoundCloud/Bandcamp/Piped (Tasks 9–10); lyrics LRCLIB(synced)/Genius/Musixmatch/AZLyrics each isolated (Task 11). Error taxonomy from §10 (Task 1), including `degraded_sources` visibility hooks (`LayeredSpotifyAuth.live_path`, `registry.unavailable`) — no silent fallbacks. Spec §1's no-hardcoded-shared-secret requirement is honored structurally: the Spotify TOTP secret is overridable via `SpotifyConfig.totp_secret_override` / `SPOTDL_SPOTIFY_TOTP_SECRET` (pinned value is a default only), and `LayeredSpotifyAuth` falls back on auth errors, transport failures, and malformed token payloads alike — with payload-shape validation so a garbage 2xx never masquerades as success.
- **Type consistency with the existing model:** uses only the real names — `EntityType`, `ProviderId` (exact 13 members), `MatchStatus`, `LyricsKind`, `Track` (duration in **ms**, so Deezer/Bandcamp/Piped/YT ×1000 and MusicBrainz/iTunes as-is are explicitly specified), `AudioCandidate`, `AlbumRef`, `ArtistRef`, `Lyrics`. New provider-layer types (`ResolvedEntity`, `PlatformRef`, `ProviderSpec`, `ProviderContext`, `SpotifyConfig`) live in `core.providers`, not `core.model`, keeping the frozen model untouched.
- **CI stays green throughout:** every task ends at `make check` green; network tests are marked `network` and excluded by `addopts = -m 'not network'` set in Task 1; providers using heavy/fragile deps are lazily imported so `import spotdl_core.providers` and the registry never import-fail (asserted in Task 12).
- **Dependency direction:** everything is under `spotdl_core`; nothing imports `spotdl_server`/`spotdl_cli`; import-linter contracts from Plan 1 continue to pass.
- **No placeholders:** all endpoints, field paths, version floors (verified on PyPI), exception classes, Protocol signatures, and the URL table are concrete. Fixture recording is a first step in each provider task so parse tests are deterministic and reviewable.
- **Task ordering is dependency-correct:** errors → urls → base (imports urls) → http → registry (imports base/http/errors) → providers (import base/http/errors, register into registry) → integration. Each provider task is independently reviewable and appends exactly one block of registrations.
