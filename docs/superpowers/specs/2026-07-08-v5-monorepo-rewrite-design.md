# spotDL v5 — Monorepo Rewrite Design

Date: 2026-07-08
Status: Approved design, pending implementation plan
Supersedes: the `xnetcat-rewrite` branch (kept only as an anti-pattern reference; the rewrite does not build on it)

## 1. Overview

spotDL v5 is a ground-up rewrite of spotify-downloader as a monorepo with three
deliverables:

- **server** — a FastAPI service providing metadata resolution, search,
  track→audio matching, lyrics, and community curation (voting/corrections).
  Self-hostable; also run by us as a **community-hosted instance** that the CLI
  uses by default.
- **cli** — the `spotdl` tool (Typer CLI + full Textual TUI). Uses the
  community server for resolve/search/match/lyrics by default; downloads always
  run locally. Works fully offline by embedding the server in-process.
- **web-ui** — a React SPA served by the server, feature-flagged per
  deployment mode.

### Goals

- Solve the Spotify API crisis structurally: metadata acquisition is
  centralized server-side (anonymous-token client + operator credentials +
  multi-source merging + permanent cache) instead of a hardcoded shared client
  secret in every install.
- Preserve spotDL's matching quality (redesigned matcher must meet or beat v4
  on a golden corpus before release).
- Self-hosting is first-class: one container, SQLite by default, same image as
  the community instance.
- Keep the `spotdl` identity: PyPI name, Docker Hub repo, docs site, user
  workflows (sync/save files, output templating, all formats).
- Avoid the failure modes of the `xnetcat-rewrite` branch (see §13).

### Non-goals (v1)

- DRM-circumvention audio sources (Tidal/Deezer downloads). These providers are
  metadata-only.
- Learned/ML matching weights (the schema records what is needed to do this
  later from vote data).
- Mobile apps, browser extensions.
- Full moderation suite — v1 admin is a minimal report-review queue, user list,
  and stats.

## 2. Decision record

| Topic | Decision |
|---|---|
| Identity | v5 of `spotdl` — takes over PyPI name, Docker Hub, docs site |
| Stack | Python 3.13 (server, CLI, core) + React 19/TypeScript (web) |
| Server scope v1 | Metadata + matching + lyrics + search + accounts + community voting |
| CLI connectivity | Community server by default; embedded server as offline fallback |
| Spotify strategy | Layered: anonymous-token client → operator credentials fallback → multi-source metadata (Deezer, iTunes, MusicBrainz) → permanent cache |
| Server downloads | Self-host/embedded only: server-side queue + browser delivery. Hard-disabled in hosted mode |
| Entity model | Two-layer: provider snapshots → typed canonical tables. No field-provenance table, no generic relation graph |
| Web UI | One app, feature-flagged via `GET /config` |
| CLI surface | New subcommand CLI + v4 compat shim (translation + deprecation notices) |
| TUI | Full parity with web UI, as a thin presentation layer over the shared client |
| Database | Hosted: Postgres. Self-host: SQLite default, Postgres optional. Embedded/CLI: SQLite |
| Repo | Orphan branch `v5` in this repo; v4 master tree copied to `~/Projects/xnetcat/spotdl-v4-reference/` |
| Auth | Anonymous read (IP rate-limited); accounts (email+password, GitHub/Discord OAuth) for voting/submissions; PATs for CLI |
| Voting scope | Matches (provider-agnostic), lyrics, metadata corrections, cross-provider entity links |
| Audio providers v1 | YouTube Music, YouTube (yt-dlp only), SoundCloud, Bandcamp, Piped; evaluate Audius/Internet Archive/Jamendo |
| Layout | `apps/` + `packages/` monorepo (uv workspace + pnpm) |
| Hosting | Railway (server + managed Postgres + Redis), Cloudflare in front |
| v1 features | All v4 downloader features (sync/save, full metadata suite, m3u, SponsorBlock, cookies, proxy, yt-dlp passthrough) |
| Matching | Redesigned provider-agnostic scorer, gated by golden corpus vs v4 |
| Architecture | CLI embeds the server (in-process ASGI) for offline/local; one core library, server is its only consumer |

## 3. Monorepo layout & tooling

```
spotify-downloader/            (orphan branch `v5`)
├─ apps/
│  ├─ server/                  # FastAPI app          → PyPI: spotdl-server
│  ├─ cli/                     # Typer CLI + Textual TUI → PyPI: spotdl
│  └─ web/                     # React 19 + Vite SPA (unpublished; embedded into server package)
├─ packages/
│  └─ core/                    # providers, matching, download engine, domain types
│                              #                       → PyPI: spotdl-core
├─ deploy/                     # Dockerfile, compose files, railway config, Caddy example
├─ docs/                       # mkdocs-material site (incl. v4→v5 migration guide)
├─ scripts/                    # build tooling, golden-corpus tooling, PyInstaller
└─ Makefile                    # `make check` = lint + typecheck + test, all components
```

**Dependency direction (hard rule):** `core` ← `server` ← `cli`.

- `packages/core` has no knowledge of HTTP, databases, or UI.
- `apps/server` is the **only** consumer of core.
- `apps/cli` never imports core directly; it talks to the server API —
  over HTTPS (remote) or in-process ASGI (embedded).
- `apps/web` and the TUI consume only generated API clients.
- Nothing is ever copied between components. Code review enforces this;
  import-linter contracts enforce it in CI.

**Tooling:**

- Python: uv workspace (single lockfile at root), ruff (lint + format),
  mypy strict, pytest. Python ≥3.13.
- Web: pnpm, TypeScript strict, vitest, Playwright, ESLint. Node ≥22.
- Generated clients: OpenAPI schema exported at build time →
  TypeScript client (apps/web) and Python client (apps/cli) generated in CI.
  Handwritten API clients are forbidden.
- CI: per-component jobs (core, server, cli, web) + one full-stack smoke job +
  golden-corpus matcher gate.

## 4. Deployment modes

One server codebase, one Docker image, mode selected by `SPOTDL_MODE`:

| Mode | Operator | Downloads | Auth & voting | Database | Web UI |
|---|---|---|---|---|---|
| `hosted` | spotDL team (Railway) | **disabled** (403 `downloads_disabled`; router not mounted) | full | Postgres | community features only |
| `selfhost` | users (NAS/VPS) | server-side queue + browser file delivery | optional local accounts | SQLite default, Postgres optional | full incl. downloads/library |
| `embedded` | inside the CLI process | via CLI (local download engine) | none (loopback only) | SQLite in spotdl data dir | served by `spotdl web` |

The hosted instance never touches audio — it serves metadata, matches (URLs +
scores), and lyrics only. This preserves the project's legal posture: audio is
always fetched client-side (or on the user's own self-hosted server) from the
target provider.

Mode gating happens at startup (routers not mounted, feature flags in
`GET /config`), not per-request conditionals.

## 5. packages/core

Four sub-packages, each independently testable.

### 5.1 core.model

Typed domain objects (pydantic, frozen): `Track`, `Album`, `Artist`,
`Playlist`, `AudioCandidate`, `Match`, `Lyrics`, `FeatureVector`. Real enums:
`EntityType`, `ProviderId`, `MatchStatus`, `LyricsKind`. No JSON-blob domain
state outside raw provider payloads.

### 5.2 core.providers

Capability-based plugins. A provider implements any subset of Protocols:

- `Resolves` — URL / `provider:type:id` → metadata
- `Searches` — free-text search
- `Enriches` — fill missing fields (genres, ISRC, art)
- `ProvidesAudio` — returns downloadable `AudioCandidate`s
- `ProvidesLyrics` — plain and synced lyrics

A registry wires providers; URL/platform-ID parsing (`spotify:track:x`,
share links, `/intl-xx/` stripping) lives here, in exactly one place.

**Metadata sources (v1):** Spotify (anonymous-token client primary,
operator-credentials spotipy-style fallback — both behind one interface),
Deezer, iTunes/Apple Music, MusicBrainz, YouTube Music.

**Audio targets (v1):** YouTube Music (default), YouTube (yt-dlp only; pytube
dropped), SoundCloud, Bandcamp, Piped. Candidates to evaluate during
implementation, same Protocol: Audius, Internet Archive, Jamendo. No provider
requiring DRM circumvention.

**Lyrics:** synced (LRCLIB via syncedlyrics), Genius, Musixmatch, AZLyrics.
Each isolated; scraper breakage in one provider cannot affect others.

### 5.3 core.matching (redesigned)

Provider-agnostic scorer, replacing v4's heuristic accretion:

1. **Feature extraction** — per `(track, candidate)`: title similarity, artist
   set similarity, album similarity (slug + rapidfuzz helpers ported from v4 —
   the one piece kept verbatim, including pykakasi handling), duration delta,
   ISRC equality, verified-source flag, forbidden-word penalty set
   (remix/live/cover/…), explicit mismatch, popularity prior.
2. **Scoring** — declarative weighted combination with hard-reject gates
   (e.g. duration delta beyond threshold, zero title-word overlap). Weights and
   gates live in a versioned config (`matcher_version`), so the server can
   recalibrate from vote data and A/B matcher versions without code changes.
3. **Selection** — ISRC-verified short-circuit; near-tie resolution by
   popularity prior.

**Release gate:** a golden corpus (several hundred `(track, candidates,
expected pick)` cases — recorded v4 decisions + hand-verified pairs, stored in
the repo) runs in CI. The new matcher must meet or beat v4 accuracy on it
before v5.0 ships. The corpus tooling lives in `scripts/`.

Community votes are a server-side overlay: a `community_verified` match pins
the returned result regardless of score; heavily downvoted matches are
re-matched.

### 5.4 core.download

v4's ~860-line god-method decomposed into a pipeline of small steps, each a
function taking/returning a typed context:

plan file path (templating, restrict, length limits, overwrite/skip/archive
logic) → fetch audio (yt-dlp) → convert (ffmpeg, bitrate handling, passthrough
args) → embed metadata (mutagen; mp3/m4a/flac/ogg/opus/wav presets, cover art,
lyrics, ISRC, source URL) → post-process (.lrc generation, m3u, archive update,
SponsorBlock via yt-dlp postprocessors).

Feature parity with v4: all output formats, full template variable set,
archive files, m3u + playlist numbering + retain-track-cover, cookie files,
proxy, yt-dlp passthrough args, SponsorBlock, ffmpeg auto-download.

Consumers: the server's download workers (selfhost/embedded). The CLI reaches
it through the embedded server, not by importing core.

## 6. apps/server

FastAPI + SQLAlchemy 2 async + Alembic + Pydantic v2 + uvicorn. Single
versioned API at `/api/v1`. OpenAPI schema is a build artifact consumed by
client generation.

**Layering:** `routers` (HTTP only) → `services` (orchestration) →
`repositories` (DB only) → core provider registry. Routers stay ≤ ~200 lines;
no business logic in routers, no HTTP or ORM types in services' public
signatures.

### 6.1 Schema

- `provider_snapshots` — unique `(provider, provider_entity_id)`;
  `entity_type`, raw payload JSON (the only JSON domain column), normalized
  key fields (name, isrc, duration_ms, artist names, album name, art URL),
  `fetched_at`, `expires_at`. Permanent metadata cache + external-ID map.
- Canonical typed tables: `tracks`, `albums`, `artists`, `playlists`; plain
  FKs (track→album, track↔artist M2M, playlist↔track ordered M2M). Merge from
  snapshots is deterministic source-priority per field class
  (Spotify > Deezer > iTunes > MusicBrainz), re-runnable.
- `entity_links` — canonical entity ↔ snapshot linkage,
  `status: auto | verified | disputed`; votable.
- `matches` — `(track_id, target_provider, target_id, score, matcher_version,
  status: auto | community_verified | rejected)`; votable. Provider-agnostic:
  any track → any audio target.
- `lyrics` — per track per source, plain + synced; votable.
- `votes` — `(user_id, votable_type, votable_id, value)`; unique per user per
  object.
- `reports` — metadata-correction reports + minimal review state.
- `users`, `oauth_identities`, `refresh_tokens`, `api_tokens`.
- `download_jobs` — selfhost/embedded queue state (survives restarts).

All enums are real DB enums / typed columns. Alembic migrations tested
up/down against SQLite and Postgres.

### 6.2 API surface (v1)

- `POST /resolve` — URL, `provider:type:id`, or free text → canonical entity
  (cache-first; on miss: fetch, snapshot, merge, kick matching).
- `GET /search?q=`, `GET /tracks/{id}`, `/albums/{id}`, `/artists/{id}`,
  `/playlists/{id}`.
- `GET /tracks/{id}/matches`, `POST /tracks/{id}/matches` (submit URL),
  `POST /matches/{id}/vote`.
- `GET /tracks/{id}/lyrics`, `POST /lyrics/{id}/vote`.
- `POST /links/{id}/vote`, `POST /reports`.
- `auth/register|login|logout|refresh|me`, OAuth callbacks, PAT management.
- `GET /config` — deployment mode + feature flags (drives web UI and TUI).
- `GET /health`, `GET /metrics`.
- Selfhost/embedded only: `POST /downloads`, `GET /downloads`,
  `DELETE /downloads/{id}`, `GET /downloads/{id}/file` (browser delivery),
  `WS /ws/progress`.
- Admin (minimal): reports queue, user list, stats.

Stable machine-readable error envelope `{code, message, detail}`; error codes
are part of the API contract and surface as typed errors in generated clients.

### 6.3 Download queue

DB-backed `download_jobs` + asyncio worker pool in-process. No Redis/celery
dependency for self-hosters — one container, one volume. Progress via
WebSocket; jobs survive restarts. Server settings: concurrency, library path,
default format/bitrate/template.

### 6.4 Rate limiting & abuse (hosted)

Redis-backed counters: per-IP anonymous tiers (generous reads), per-token
authed tiers, tight write tiers (votes/submissions/reports). Expensive
uncached resolves enter a bounded queue with backpressure instead of
immediate 429s. Cloudflare in front for CDN/DDoS.

## 7. apps/cli (CLI + TUI)

**One client, two transports.** All functionality goes through
`SpotdlClient` (generated Python client) constructed with either an HTTPS base
URL or an in-process ASGI transport to an embedded server (SQLite). Defaults:
community server for resolve/search/match/lyrics; downloads always local via
the embedded server's engine. `--offline`, config, or unreachable-server
fallback (with a warning) switch resolution to embedded too.

```
spotdl <url|query>                     # sugar for `spotdl download`
spotdl download <urls...> [options]
spotdl search <query>
spotdl sync <file|url> [--out-file]    # .spotdl v2 (versioned JSON; v4 auto-migrated)
spotdl save <url> [--save-file]
spotdl meta <files...>
spotdl url <urls...>
spotdl web                             # embedded server + bundled web UI, localhost
spotdl tui                             # Textual TUI (also bare `spotdl` in a TTY)
spotdl auth login|logout|status        # community account; stores PAT
spotdl config get|set|edit
spotdl server [--mode selfhost ...]    # run a real server from the CLI install
```

**Compat shim:** v4 invocations are detected and translated (one-line
deprecation notice showing the new form). `.spotdl` v4 files load
transparently. Removed long-tail v4 flags fail with a pointer to their
replacement. The translation table doubles as the migration-guide content and
is test-covered.

**TUI:** full parity with the web UI (search, entity pages, match voting,
lyrics, queue, settings, admin-lite) as a pure presentation layer: Textual
screens + a shared view-model module. Hard rule: no provider/matching/download
logic in TUI code — new data needs grow the server API, benefiting web too.

**Downloader UX:** Rich progress (parallel bars), per-track failures never
abort a batch; collected error summary; `--save-errors` retained.

## 8. apps/web

React 19 + TypeScript + Vite + TanStack Router/Query + Tailwind. Server state
exclusively via TanStack Query over the generated TS client; Zustand only for
UI/session state (auth token, runtime-configurable API base URL so one build
can point at any self-hosted server).

Pages: home/search; track/album/artist/playlist (metadata, match list with
scores + voting + submit-URL, lyrics incl. synced display); downloads queue +
library (selfhost/embedded; live WebSocket progress); settings; auth; minimal
admin (reports, users, stats). All feature-gated by `GET /config`.

The built SPA is embedded as static assets in the `spotdl-server` package —
`spotdl web` works offline; v4's runtime GitHub fetch of the web UI is gone.

## 9. Community hosting & ops

- Railway: server (hosted mode) + managed Postgres + Redis. Cloudflare in
  front. The GHCR image self-hosters pull is byte-identical to what Railway
  runs.
- `deploy/`: `docker-compose.selfhost.yml` (single service + volume; optional
  Postgres override file), Caddy TLS example, Railway config.
- Observability: structured JSON logs, Prometheus `/metrics`
  (request rates, cache hit ratio, provider error rates, resolve queue depth,
  matcher version distribution), optional Sentry via env.
- Nightly Postgres backups to object storage.
- Matcher A/B: hosted server can run a candidate `matcher_version` on a
  traffic slice and compare vote outcomes before promoting.

## 10. Error handling

- Core raises typed exceptions (`ProviderUnavailable`, `NoMatchFound`,
  `DownloadFailed(step=…)`, `ConversionFailed`, `MetadataEmbedFailed`, …).
- Server maps them to the stable error envelope; codes documented in OpenAPI.
- Provider degradation is graceful and visible: if the Spotify anonymous-token
  client breaks, resolution proceeds from other sources and responses carry
  `degraded_sources`; clients display why metadata may be thinner. No silent
  fallbacks.
- CLI: batch downloads report per-track failures at the end; non-zero exit if
  any failed; `--save-errors` writes details.

## 11. Testing

- **core:** unit tests; VCR cassettes per provider; golden matching corpus as
  a CI gate with accuracy report per matcher version.
- **server:** pytest against SQLite and Postgres (service container); API
  contract tests; Alembic up/down tests; rate-limit behavior tests.
- **cli:** integration tests (command → embedded server → mocked providers);
  compat-shim translation table tests; TUI snapshot tests (Textual pilot).
- **web:** vitest component tests; Playwright e2e against a seeded
  selfhost-mode server.
- **cross-cutting:** CI job boots the compose stack and smoke-tests
  resolve → match → queue → stubbed download → file exists with correct tags.

## 12. Migration & release

1. Copy master's tree (plain files, no `.git`) to
   `~/Projects/xnetcat/spotdl-v4-reference/`.
2. Create orphan branch `v5` in this repo from an empty tree; all v5 work
   happens there. No legacy code is checked into `v5` (no `old/` tree).
3. v4 master continues receiving fixes until v5.0 GA.
4. PyPI: pre-releases as `5.0.0aN` (pip keeps serving 4.x by default);
   `spotdl` 5.0 at GA, depending on `spotdl-server` → `spotdl-core`.
5. Docker Hub `spotdl/spotify-downloader` switches to the server image at GA;
   v4 image stays tagged `legacy-v4`.
6. Docs site rewritten; prominent v4→v5 migration guide generated from the
   compat-shim translation table.
7. PyInstaller binaries continue: default action launches the TUI;
   `spotdl web` for the browser UI. ffmpeg auto-download retained.
8. Community server goes live on Railway before GA; the CLI default
   `api_url` points at it (overridable in config; must not ship as a
   localhost stub).

## 13. Risks & mitigations (lessons from xnetcat-rewrite)

| Risk | Mitigation |
|---|---|
| Shared core forks and diverges (killed the last attempt) | Server is core's only consumer; CLI/web/TUI use generated clients only; import-linter CI contracts |
| God-files (800–1700 lines last time) | Layering rules + size expectations in review; routers/services/screens stay small and single-purpose |
| Entity schema churn (4 migration reworks last time) | Simplified two-layer model specified up front; typed columns and enums; migrations reviewed against this spec |
| Matching redesign regresses quality | Golden corpus CI gate vs v4; versioned weights; hosted A/B before promoting |
| Spotify anonymous-token client breaks | Provider interface with credential fallback + multi-source merge + permanent snapshot cache; `degraded_sources` visibility |
| TUI parity balloons | TUI is presentation-only over shared client/view-models; logic additions must land in the server API |
| Community server cost/abuse | Cache-first design, Redis rate limiting, resolve backpressure, Cloudflare; hosted mode serves no audio |
| Dead layers accumulate | v1 scope is fixed here; features not in this spec require a spec update first |
