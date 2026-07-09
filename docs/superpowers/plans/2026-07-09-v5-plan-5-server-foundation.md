# spotDL v5 `apps/server` Foundation Implementation Plan (Plan 5 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Plan 1's server skeleton into a working metadata backend implementing the read side of spec §6: the full §6.1 database schema (SQLAlchemy 2 async + Alembic, dual-dialect), the entity persistence layer (provider-snapshot cache, deterministic canonical merge, matches, lyrics, entity links), and the non-auth/non-download `/api/v1` surface from §6.2 (`POST /resolve`, `GET /search`, typed entity GETs, `GET /tracks/{id}/matches`, `GET /tracks/{id}/lyrics`, `GET /config`, `GET /health`). The stable error envelope (§10) and the OpenAPI build artifact (§3) ship here. Auth/votes/reports/admin are **Plan 6**; downloads and WebSocket progress are **Plan 7** — this plan implements **neither**, but the schema is designed complete so neither plan needs to ALTER a table created here.

**Architecture:** Strict layering per spec §6: `routers` (HTTP only, ≤200 lines each, no business logic) → `services` (orchestration; no FastAPI or SQLAlchemy types in public signatures) → `repositories` (DB only; the sole holders of ORM query code) → `core` provider registry + matcher (consumed only through the Plan 2 `ProviderRegistry` and the Plan 3 `match()` function). `apps/server` is the **only** consumer of `packages/core` (spec §3). No module-level mutable singletons: the async engine, session factory, and `ProviderRegistry` are built in the FastAPI lifespan, stored on `app.state`, injected into services via FastAPI dependencies, and closed on shutdown. Deployment-mode gating is startup-time (routers mounted or not, feature flags in `GET /config`), never per-request conditionals.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 (async ORM, `Mapped`/`mapped_column`), Alembic, Pydantic v2 + pydantic-settings, aiosqlite (default), asyncpg (optional Postgres), uvicorn. Tests: pytest + pytest-asyncio, httpx `ASGITransport` for API tests, SQLite (in-memory and tmp-file) for repository/migration tests, an optional Postgres service (skipped locally when absent, run in CI). All provider/matcher I/O is faked at the `ProviderRegistry` seam with in-memory fake providers implementing the Plan 2 Protocols — the default suite is fully offline.

## Global Constraints

- Python `>=3.13`; single uv lockfile at the workspace root.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Dependency direction (spec §3, machine-enforced by import-linter): `core ← server ← cli`. `spotdl_server` may import `spotdl_core`; it must **never** import `spotdl_cli`. New intra-server layering contracts are added in Task 12.
- New runtime dependencies go in `apps/server/pyproject.toml`; new test-only dependencies go in the root `pyproject.toml` `[dependency-groups].dev`. Exact version floors are given per task.
- No code is copied from the `xnetcat-rewrite` branch or v4. Those trees are **shape references only** (the anti-pattern schema is cited in the self-review, not ported).
- **No module-level mutable singletons.** The engine, `async_sessionmaker`, and `ProviderRegistry` live on `app.state`, are created in the lifespan, and are closed on shutdown. Services receive their collaborators by dependency injection.
- **Layering is a contract, not a convention** (enforced in Task 12): routers import only `fastapi`, Pydantic API schemas, and service classes — never `sqlalchemy` or ORM models. Services import repositories and core — never `fastapi`. Repositories are the only modules that import `sqlalchemy`/ORM. Routers stay ≤200 lines.
- TDD: every task writes failing tests first (RED), then implements to green. The default suite is **offline** — no real provider network, no real Postgres required.
- All test directories are packages (`__init__.py` present); pytest runs with `--import-mode=importlib` (already configured). `apps/server/tests/conftest.py` already strips `SPOTDL_`-prefixed env vars.
- `make check` (lint + typecheck + test + web-check) must pass at the end of **every** task. `make check` runs `pytest -m 'not network'`; Postgres-backed tests are gated by a `postgres` marker/skip (see Task 3) so a developer without a Postgres server still gets a green `make check`.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## What already exists (do not recreate)

- **Plan 1 (server skeleton):** `apps/server/src/spotdl_server/app.py` (`create_app(settings)` mounting `GET /api/v1/health` and `GET /api/v1/config`), `settings.py` (`DeploymentMode` StrEnum `HOSTED|SELFHOST|EMBEDDED`, `Settings(BaseSettings)` with `env_prefix="SPOTDL_"` and `mode`), `apps/server/tests/{conftest.py,test_app.py}`. `apps/server/pyproject.toml` depends on `spotdl-core, fastapi>=0.115, uvicorn>=0.34, pydantic-settings>=2.7`.
- **Plan 1/2 (`core.model`):** `spotdl_core.model` re-exports `EntityType`, `ProviderId`, `MatchStatus`, `LyricsKind` (real `StrEnum`s) and the frozen entities `ArtistRef`, `AlbumRef`, `Track`, `AudioCandidate`, `FeatureVector`, `Match`, `Lyrics`. Field shapes are fixed in `packages/core/src/spotdl_core/model/entities.py` (consumed verbatim; see the type-consistency table in the self-review).
- **Plan 2 (`core.providers`) — consumed via the registry seam.** CONTRACT surface this plan relies on:
  - Exception taxonomy `spotdl_core.providers`: `SpotdlError` (root); `ProviderError(message, *, provider)` with `.provider`; subclasses `ProviderUnavailable`, `ProviderAuthError`, `RateLimited(*, provider, retry_after)`, `EntityNotFound`; standalone `UnsupportedURL`, `NoMatchFound`; download subset `DownloadFailed(*, step)`, `ConversionFailed`, `MetadataEmbedFailed`.
  - `parse(value: str) -> PlatformRef` where `PlatformRef(provider: ProviderId, entity_type: EntityType, entity_id: str, url: str | None)`; raises `UnsupportedURL`.
  - Capability Protocols (runtime-checkable) `Resolves` (`async resolve(ref) -> ResolvedEntity`), `Searches` (`async search(query, *, limit=10) -> list[Track]`), `Enriches`, `ProvidesAudio` (`async audio_candidates(track, *, limit=10) -> list[AudioCandidate]`), `ProvidesLyrics` (`async lyrics(track) -> Lyrics | None`); base `Provider` (`id: ClassVar[ProviderId]`).
  - `ResolvedEntity(BaseModel, frozen)`: `provider, provider_id, entity_type, track: Track|None, album: AlbumRef|None, artist: ArtistRef|None, name: str|None, tracks: tuple[Track,...]`.
  - `ProviderRegistry(context: ProviderContext)` with `register(spec)`, `get(id) -> Provider`, `capable(capability: type[C]) -> list[C]` (PROVIDER_ORDER order, skips failed factories), `registered`, `unavailable -> dict[ProviderId, ProviderError]`, `aclose()`, async context manager; `ProviderSpec(id, capabilities: frozenset[type], factory)`; `ProviderContext(user_agent, spotify: SpotifyConfig, soundcloud_client_id, genius_token, piped_instances, ytmusic_language)`; `build_default_registry(context) -> ProviderRegistry`.
- **Plan 3 (`core.matching`) — consumed via one function.** CONTRACT: `from spotdl_core.matching import match, ScoringConfig, MATCHER_V5_DEFAULT`; `def match(track: Track, candidates: tuple[AudioCandidate, ...] | list[AudioCandidate], config: ScoringConfig = MATCHER_V5_DEFAULT) -> list[Match]` (ranked, viable-only). `ScoringConfig.matcher_version: str` (default `"v5.0"`) and `ScoringConfig` round-trips `model_dump_json()` / `model_validate_json()`.

> **Availability note:** Plans 2 and 3 are implemented before Plan 5 executes. If a `capable()` call finds no real audio/metadata providers yet, the services still function (they degrade to `degraded_sources` / empty results). All Plan 5 tests fake the registry, so Plan 5 does not depend on any real provider being finished.

## Plan series roadmap (for context — not part of this plan)

Plan 1 bootstrap (done) → Plan 2 `core.providers` → Plan 3 `core.matching` → Plan 4 `core.download` → **Plan 5 server foundation (this plan)** → Plan 6 auth + community (users/votes/reports/admin) → Plan 7 downloads + WS → Plan 8 clients + CLI → Plan 9 TUI → Plan 10 web → Plan 11 deploy.

## Package layout produced by this plan

```
apps/server/src/spotdl_server/
├─ __init__.py                    # __version__ (exists)
├─ app.py                         # create_app(settings, *, registry=None): lifespan, routers, handlers (Task 7,8,10)  [CONTRACT for signature]
├─ bootstrap.py                   # upgrade_to_head(settings): programmatic Alembic upgrade (Task 3)  [CONTRACT]
├─ settings.py                    # extended: database, data_dir, provider context (Task 1)
├─ db/
│  ├─ __init__.py
│  ├─ base.py                     # DeclarativeBase, naming convention, TimestampMixin, UUID/JSON type aliases (Task 1)
│  ├─ engine.py                   # build_engine / build_sessionmaker from Settings (Task 1)  [CONTRACT]
│  ├─ enums.py                    # server-only DB enums: LinkStatus, DownloadStatus, BatchKind (Task 2)  [CONTRACT]
│  └─ models.py                   # ALL §6.1 ORM models (Task 2)  [CONTRACT — THE schema]
├─ repositories/
│  ├─ __init__.py
│  ├─ snapshots.py                # SnapshotRepository (Task 4)  [CONTRACT]
│  ├─ entities.py                 # TrackRepository/AlbumRepository/ArtistRepository/PlaylistRepository (Task 4)  [CONTRACT]
│  ├─ merge.py                    # deterministic snapshot→canonical merge (Task 5)  [CONTRACT for rules]
│  ├─ links.py                    # EntityLinkRepository (Task 6)  [CONTRACT]
│  ├─ matches.py                  # MatchRepository (Task 6)  [CONTRACT]
│  └─ lyrics.py                   # LyricsRepository (Task 6)  [CONTRACT]
├─ services/
│  ├─ __init__.py
│  ├─ errors.py                   # NotFoundError (server-side rich 404) (Task 7)  [CONTRACT]
│  ├─ dto.py                      # service-layer DTOs (no HTTP/ORM types) (Task 8)
│  ├─ provider_search.py          # shared multi-provider search helper (Task 8)  [CONTRACT]
│  ├─ resolve.py                  # ResolveService (Task 8)  [CONTRACT for signature]
│  ├─ search.py                   # SearchService (Task 9, reuses provider_search)
│  └─ entities.py                 # EntityService (Task 9)
├─ api/
│  ├─ __init__.py
│  ├─ schemas.py                  # Pydantic request/response models (Task 10)  [CONTRACT]
│  ├─ errors.py                   # ErrorEnvelope + ErrorCode + exception handlers (Task 7)  [CONTRACT]
│  ├─ deps.py                     # FastAPI dependencies: session, services (Task 8-10)
│  └─ routers/
│     ├─ __init__.py
│     ├─ resolve.py               # POST /resolve (Task 10)
│     ├─ search.py                # GET /search (Task 10)
│     ├─ entities.py              # GET /tracks|albums|artists|playlists/{id} (+matches,+lyrics) (Task 10)
│     └─ meta.py                  # GET /health, GET /config (Task 10)
alembic/                          # at apps/server/ root
├─ alembic.ini
├─ env.py                         # async, dual-dialect (Task 3)
└─ versions/
   └─ 0001_initial_schema.py      # full §6.1 schema (Task 3)  [CONTRACT mirrors models.py]

apps/server/tests/
├─ __init__.py, conftest.py       # extended: db fixtures, fake-registry fixtures
├─ db/            test_models.py, test_engine.py, test_migrations.py, test_bootstrap.py
├─ repositories/  test_snapshots.py, test_entities.py, test_merge.py, test_links.py, test_matches.py, test_lyrics.py
├─ services/      test_provider_search.py, test_resolve.py, test_search.py, test_entities_service.py
├─ api/           test_resolve_api.py, test_search_api.py, test_entities_api.py, test_config.py, test_errors.py
├─ fakes.py                       # in-memory fake providers implementing the Plan 2 Protocols
└─ test_openapi.py                # OpenAPI in-sync test
scripts/export_openapi.py         # deterministic openapi.json dump (Task 11)
openapi.json                      # committed build artifact (Task 11)
```

---

## THE SCHEMA (spec §6.1) — authoritative table-by-table contract

This section is the single source of truth for Task 2 (ORM) and Task 3 (initial migration). It is designed **complete** so that Plan 6 (auth/votes/reports) and Plan 7 (downloads/WS) add only **new tables**, never ALTER a table defined here. Every column below has a stated type, nullability, default, and constraint.

**Cross-dialect rules (anti-churn, non-negotiable):**
- **Primary keys:** `sa.Uuid(as_uuid=True)` with Python-side `default=uuid.uuid4`. Portable: native `UUID` on Postgres, `CHAR(32)` on SQLite. Public entity ids in URLs are these UUIDs.
- **Enums:** `sa.Enum(PyEnum, native_enum=False, validate_strings=True, length=32)` → stored as `VARCHAR` + `CHECK` on **both** dialects. This deliberately avoids Postgres native `ENUM` types, whose `ADD VALUE` / `DROP TYPE` migrations were a churn source. Enum classes: `ProviderId`, `EntityType`, `MatchStatus`, `LyricsKind` (from `core.model`); `LinkStatus`, `DownloadStatus`, `BatchKind` (server-only, `db/enums.py`).
- **JSON:** `sa.JSON` (portable). Used **only** for `provider_snapshots.raw_payload` (the one JSON *domain* column, per spec) and for small normalized value lists (`genres`, denormalized `artist_names`, serialized `features`) — never for canonical domain state that belongs in typed columns.
- **Timestamps:** `sa.DateTime(timezone=True)`, Python-side `default=lambda: datetime.now(UTC)` (and `onupdate` for `updated_at`). No dialect-specific `server_default now()`. A `TimestampMixin` supplies `created_at` + `updated_at`.
- **Naming convention:** set `MetaData(naming_convention=...)` for `ix/uq/ck/fk/pk` so Alembic autogenerate and downgrades are deterministic across dialects (this alone prevents most "spurious diff" migration churn).
- **Vote tallies live now.** `matches`, `lyrics`, `entity_links` each carry `upvotes`, `downvotes`, `net_score` (all `INTEGER NOT NULL DEFAULT 0`). Plan 6's `votes` table inserts rows and updates these counters — **no ALTER** of the votable tables.
- **Deferred user references are plain nullable UUID columns with NO DB foreign key** (`submitted_by`, `requested_by`). Plan 6 creates `users` and adds `votes`/`reports` that FK *into* these tables (additive). We accept app-level integrity for the back-reference to avoid a SQLite batch-rebuild ALTER later. Document this at each column.

### Table: `provider_snapshots`
Permanent metadata cache + external-ID map. One row per `(provider, provider_entity_id)`.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `provider` | Enum(ProviderId) | no | | |
| `provider_entity_id` | String(256) | no | | the provider's native id (or SoundCloud/Bandcamp path) |
| `entity_type` | Enum(EntityType) | no | | |
| `raw_payload` | JSON | no | | verbatim provider response (the only JSON domain column) |
| `name` | String(1024) | yes | | normalized key field |
| `isrc` | String(32) | yes | | normalized key field |
| `duration_ms` | Integer | yes | | normalized key field |
| `artist_names` | JSON | yes | | normalized `list[str]` |
| `album_name` | String(1024) | yes | | normalized key field |
| `art_url` | String(2048) | yes | | normalized key field |
| `fetched_at` | DateTime(tz) | no | now | when the payload was fetched |
| `expires_at` | DateTime(tz) | yes | | cache TTL boundary; NULL = permanent |
| `created_at`/`updated_at` | DateTime(tz) | no | now | TimestampMixin |

Constraints/indexes: `UNIQUE (provider, provider_entity_id)` → `uq_provider_snapshots_provider_entity`; `INDEX (isrc)`; `INDEX (provider, entity_type)`.

### Table: `albums`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `name` | String(1024) | no | | |
| `album_artist` | String(1024) | yes | | mirrors `AlbumRef.album_artist` |
| `year` | Integer | yes | | |
| `track_count` | Integer | yes | | |
| `cover_url` | String(2048) | yes | | |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

### Table: `artists`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `name` | String(1024) | no | | display name (highest-priority source's casing) |
| `normalized_name` | String(1024) | no | | canonical dedup key — see artist-identity contract below |
| `genres` | JSON | no | `[]` | normalized `list[str]` |
| `image_url` | String(2048) | yes | | |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (normalized_name)` → `uq_artists_normalized_name`.

> **Artist canonical identity (CONTRACT).** Tracks carry artists only as name tuples (`Track.artists: tuple[str, ...]`); a track resolve produces no per-artist snapshots or entity_links, so artist identity cannot come from provider ids. Dedup is therefore by **normalized name**. Normalization rule (`normalize_artist_name`, Task 4): `unicodedata.normalize("NFKC", name).casefold()`, then collapse every internal whitespace run to a single space, then `strip()`. So `"  The  Beatles "` ≡ `"the beatles"`, `"BØRNS"` ≡ `"børns"`. The unique index on `normalized_name` enforces one canonical row per key and is also the **future duplicate-cleanup boundary**: later artist-merge tooling (or a Plan 6 correction flow) operates by re-pointing `track_artists.artist_id` rows across this key — no schema change needed. Artist rows created *directly* (an `ARTIST` resolve with real snapshots) still get `entity_links`; artist rows created as a side effect of a track merge get none (name-only provenance) — both paths converge on the same row via `normalized_name`.

### Table: `tracks`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `name` | String(1024) | no | | |
| `duration_ms` | Integer | no | `0` | |
| `isrc` | String(32) | yes | | indexed |
| `explicit` | Boolean | yes | | tri-state (unknown = NULL) |
| `track_number` | Integer | yes | | |
| `disc_number` | Integer | yes | | |
| `year` | Integer | yes | | |
| `genres` | JSON | no | `[]` | normalized `list[str]` |
| `popularity` | Integer | yes | | Spotify prior (feeds matcher/select later) |
| `album_id` | Uuid FK→albums.id | yes | | plain FK, `ondelete=SET NULL` |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Indexes: `INDEX (isrc)`; `INDEX (album_id)`.

### Table: `playlists`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `name` | String(1024) | no | | |
| `description` | Text | yes | | |
| `owner` | String(512) | yes | | |
| `cover_url` | String(2048) | yes | | |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

### Link table: `track_artists` (track ↔ artist M2M, ordered)
| Column | Type | Null | Notes |
|---|---|---|---|
| `track_id` | Uuid FK→tracks.id | no | `ondelete=CASCADE` |
| `artist_id` | Uuid FK→artists.id | no | `ondelete=CASCADE` |
| `position` | Integer | no | artist ordering (0 = main) |

PK: composite `(track_id, artist_id)`. Index `(artist_id)`.

### Link table: `playlist_tracks` (playlist ↔ track M2M, ordered)
| Column | Type | Null | Notes |
|---|---|---|---|
| `playlist_id` | Uuid FK→playlists.id | no | `ondelete=CASCADE` |
| `track_id` | Uuid FK→tracks.id | no | `ondelete=CASCADE` |
| `position` | Integer | no | playlist order |

PK: composite `(playlist_id, track_id)`. Index `(track_id)`. (Ordering via `position`; relationship uses `order_by=position`.)

> **Schema note (spec-faithful):** spec §6.1 lists exactly `track→album` FK, `track↔artist` M2M, `playlist↔track` ordered M2M. Album↔artist is intentionally **not** a link table — `albums.album_artist` (string) carries the album-artist display, matching `AlbumRef`. This is the deliberate "no generic relation graph" decision (spec §2 decision record) that avoids the anti-pattern branch's rework.

### Table: `entity_links`
Canonical entity ↔ snapshot linkage; votable.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `entity_type` | Enum(EntityType) | no | | which canonical table `entity_id` points at |
| `entity_id` | Uuid | no | | canonical id (polymorphic; no cross-table FK) |
| `snapshot_id` | Uuid FK→provider_snapshots.id | no | | `ondelete=CASCADE` |
| `status` | Enum(LinkStatus) | no | `auto` | `auto \| verified \| disputed` |
| `upvotes` | Integer | no | `0` | vote tally (Plan 6 populates) |
| `downvotes` | Integer | no | `0` | vote tally |
| `net_score` | Integer | no | `0` | upvotes − downvotes cache |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (entity_type, entity_id, snapshot_id)`; `INDEX (snapshot_id)`; `INDEX (entity_type, entity_id)`.

### Table: `matches`
Provider-agnostic track → audio target; votable.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `track_id` | Uuid FK→tracks.id | no | | `ondelete=CASCADE`, indexed |
| `target_provider` | Enum(ProviderId) | no | | audio provider |
| `target_id` | String(512) | no | | provider's audio id/ref |
| `target_url` | String(2048) | no | | playable URL |
| `score` | Float | no | | matcher base score |
| `matcher_version` | String(32) | no | | from `ScoringConfig.matcher_version` |
| `status` | Enum(MatchStatus) | no | `auto` | `auto \| community_verified \| rejected` |
| `features` | JSON | yes | | serialized `FeatureVector` (vote-data training later) |
| `candidate_name` | String(1024) | yes | | denormalized for display without refetch |
| `candidate_artists` | JSON | yes | | denormalized `list[str]` |
| `candidate_duration_ms` | Integer | yes | | denormalized |
| `submitted_by` | Uuid | yes | | user id; **no FK** (Plan 6 adds `users`); NULL = auto |
| `upvotes` | Integer | no | `0` | vote tally |
| `downvotes` | Integer | no | `0` | vote tally |
| `net_score` | Integer | no | `0` | vote tally cache |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (track_id, target_provider, target_id)` → dedupe re-matches; `INDEX (track_id, status)`.

### Table: `lyrics`
Per track, per source, per kind; votable.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `track_id` | Uuid FK→tracks.id | no | | `ondelete=CASCADE`, indexed |
| `source` | Enum(ProviderId) | no | | lyrics provider |
| `kind` | Enum(LyricsKind) | no | | `plain \| synced` |
| `text` | Text | no | | plain text or LRC body |
| `submitted_by` | Uuid | yes | | user id; **no FK** (Plan 6); NULL = auto |
| `upvotes` | Integer | no | `0` | vote tally |
| `downvotes` | Integer | no | `0` | vote tally |
| `net_score` | Integer | no | `0` | vote tally cache |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (track_id, source, kind)`; `INDEX (track_id)`.

### Table: `download_batches` (schema only — created here, **unused until Plan 7**)
Groups the N jobs produced by one `POST /downloads` (single-track submissions are a batch of one) and holds the batch-level post-processing config Plan 7's finalizer needs (m3u, `.spotdl` save file, archive). Defined now — per Plan 7's required amendment — so Plan 7 ships **zero** migrations.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `kind` | Enum(BatchKind) | no | | `single \| album \| playlist` |
| `source` | String(2048) | yes | | submitted url/query (for save-file provenance) |
| `name` | String(1024) | yes | | album/playlist display name → `{list-name}`, m3u, save-file title |
| `output_format` | String(16) | yes | | resolved per submit |
| `bitrate` | String(16) | yes | | |
| `output_template` | String(2048) | yes | | |
| `generate_m3u` | Boolean | no | `False` | |
| `m3u_template` | String(2048) | yes | | m3u file-name template (`{list}`/`{list[0]}`) |
| `generate_save_file` | Boolean | no | `False` | |
| `save_file_path` | String(2048) | yes | | on-disk `.spotdl` target if auto-written |
| `update_archive` | Boolean | no | `False` | |
| `embed_lyrics` | Boolean | no | `True` | |
| `generate_lrc` | Boolean | no | `False` | |
| `sponsor_block` | Boolean | no | `False` | |
| `total_jobs` | Integer | no | `0` | = `{list-length}` |
| `finalized_at` | DateTime(tz) | yes | | set once post-processing has run (idempotency guard) |
| `requested_by` | Uuid | yes | | user id; **no FK** (Plan 6 pattern) |
| `created_at`/`updated_at` | DateTime(tz) | no | now | TimestampMixin |

Indexes: `INDEX (requested_by)`.

### Table: `download_jobs` (schema only — created here, **unused until Plan 7**)
Selfhost/embedded queue state; survives restarts. Defined now so Plan 7 mounts the router and worker without a migration. `progress` + `updated_at` (which has `onupdate`) double as Plan 7's progress column and de-facto heartbeat; crash recovery keys on `status='running'` under single-process queue ownership — no lease column needed.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `batch_id` | Uuid FK→download_batches.id | yes | | `ondelete=CASCADE`, indexed; groups a submission (single-track = batch of one) |
| `track_id` | Uuid FK→tracks.id | yes | | `ondelete=SET NULL` |
| `match_id` | Uuid FK→matches.id | yes | | `ondelete=SET NULL` (chosen audio target) |
| `status` | Enum(DownloadStatus) | no | `queued` | `queued \| running \| completed \| failed \| cancelled` |
| `list_position` | Integer | yes | | 1-based index within the batch → `{list-position}` |
| `output_format` | String(16) | yes | | mp3/m4a/flac/… |
| `bitrate` | String(16) | yes | | |
| `output_template` | String(2048) | yes | | |
| `output_path` | String(2048) | yes | | final file path |
| `progress` | Float | no | `0.0` | 0..1 |
| `error_message` | Text | yes | | |
| `error_step` | String(32) | yes | | maps to `DownloadFailed.step` |
| `skip_reason` | String(32) | yes | | set when a `completed` job was actually a skip (`already_exists`/`in_archive`/`skip_file`/`explicit_filtered`); NULL = a real download. Keeps `DownloadStatus` stable (no `skipped` enum value → no enum ALTER) |
| `attempts` | Integer | no | `0` | incremented by Plan 7's `requeue()`/`recover_orphaned()`; `attempts > 0` ⇒ the worker forces `overwrite=FORCE` on re-run (Plan 7 recovery-integrity rule — the re-run decision rides on the row, not the filesystem) |
| `requested_by` | Uuid | yes | | user id; **no FK** (Plan 6) |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |
| `started_at` | DateTime(tz) | yes | | |
| `finished_at` | DateTime(tz) | yes | | |

Indexes: `INDEX (status)`; `INDEX (track_id)`; `INDEX (batch_id)`.

**Deferred to Plan 6 (created there, NOT here):** `users`, `oauth_identities`, `refresh_tokens`, `api_tokens`, `votes` (`user_id`, `votable_type`, `votable_id`, `value`; unique per user per object), `reports`. **Deferred to Plan 7 wiring:** the download router/worker/finalizer (the `download_batches` + `download_jobs` tables exist now, per Plan 7's required amendments — Plan 7 ships zero migrations). The self-review confirms none of these require ALTERing a Plan 5 table.

---

## Tasks

### Task 1: DB foundation — settings extension, declarative base, engine/session factory

**Files:**
- Modify: `apps/server/pyproject.toml` (deps), `apps/server/src/spotdl_server/settings.py`
- Create: `apps/server/src/spotdl_server/db/__init__.py`, `db/base.py`, `db/engine.py`
- Create: `apps/server/tests/db/__init__.py`, `apps/server/tests/db/test_engine.py`

**Step 1 — dependencies.** Add to `apps/server/pyproject.toml` `dependencies` (floors verified on PyPI 2026-07): `"sqlalchemy[asyncio]>=2.0.36"`, `"alembic>=1.14"`, `"aiosqlite>=0.20"`, `"asyncpg>=0.30"`. Run `uv sync --all-packages`.

**Step 2 — extend `Settings` (RED first: write `test_engine.py`).** Add to `Settings`:
```python
data_dir: Path = Path("~/.local/share/spotdl").expanduser()   # SQLite file location for selfhost/embedded
database_url: str | None = None                               # explicit override (e.g. postgresql+asyncpg://...)
db_echo: bool = False
```
Add a computed helper (a method, not a field) `def effective_database_url(self) -> str`: if `database_url` set, return it (assert it names an async driver: contains `+aiosqlite` or `+asyncpg`); else return `f"sqlite+aiosqlite:///{self.data_dir / 'spotdl.db'}"`. Keep `mode` unchanged. (Provider-context settings — Spotify creds etc. — are read by `build_default_registry`'s `ProviderContext.from_env`; add a `provider_context()` helper in Task 8, not here.)

**Step 3 — `db/base.py` (CONTRACT: naming convention + mixin).**
```python
from datetime import UTC, datetime
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
```

**Step 4 — `db/engine.py` (CONTRACT — no singletons).**
```python
def build_engine(settings: Settings) -> AsyncEngine        # create_async_engine(settings.effective_database_url(), echo=settings.db_echo, future=True)
def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]   # expire_on_commit=False
```
No module-level engine. `data_dir` is `mkdir(parents=True, exist_ok=True)`-ed inside `build_engine` for the SQLite case.

**Tests (`test_engine.py`, offline):**
- `test_default_url_is_sqlite_aiosqlite` — `Settings(data_dir=tmp).effective_database_url()` starts with `sqlite+aiosqlite:///` and points inside tmp.
- `test_explicit_postgres_url_passthrough` — `Settings(database_url="postgresql+asyncpg://u@h/db").effective_database_url()` returns it unchanged.
- `test_build_engine_and_sessionmaker_roundtrip` — build engine on a tmp SQLite file, open a session, `await session.execute(text("select 1"))` returns 1; `await engine.dispose()`.

**Gates:** `make check` green. **Commit:** `feat(server): async SQLAlchemy engine/session factory and settings`.

---

### Task 2: SQLAlchemy models — the full §6.1 schema (THE contract)

**Files:**
- Create: `apps/server/src/spotdl_server/db/enums.py`, `db/models.py`
- Create: `apps/server/tests/db/test_models.py`

**Step 1 — `db/enums.py` (CONTRACT).** Server-only DB enums (core enums are imported from `spotdl_core.model`):
```python
from enum import StrEnum
class LinkStatus(StrEnum):
    AUTO = "auto"; VERIFIED = "verified"; DISPUTED = "disputed"
class DownloadStatus(StrEnum):
    QUEUED = "queued"; RUNNING = "running"; COMPLETED = "completed"
    FAILED = "failed"; CANCELLED = "cancelled"
class BatchKind(StrEnum):
    SINGLE = "single"      # one submitted track/url
    ALBUM = "album"        # album url expanded to N tracks
    PLAYLIST = "playlist"  # playlist url expanded to N tracks
```

**Step 2 — write `test_models.py` (RED).** Tests build all tables into a fresh in-memory SQLite engine (`create_all`) and assert the schema **exactly matches the contract table above**. This is the guard against churn — the test is the schema spec, mechanically:
- `test_all_tables_present` — `Base.metadata.tables.keys()` == the exact set `{provider_snapshots, albums, artists, tracks, playlists, track_artists, playlist_tracks, entity_links, matches, lyrics, download_batches, download_jobs}`.
- `test_provider_snapshots_columns_and_unique` — column names/nullability/types match the contract; the `(provider, provider_entity_id)` unique constraint exists by name `uq_provider_snapshots_provider_entity`.
- One `test_<table>_columns` per table asserting the full column list, nullability, and defaults from the contract (use `Base.metadata.tables[...]`; iterate columns; assert against a literal expected dict).
- `test_vote_tally_columns_present` — `matches`, `lyrics`, `entity_links` each have `upvotes/downvotes/net_score` NOT NULL default 0.
- `test_artists_normalized_name_unique` — `artists.normalized_name` is NOT NULL and carries the unique constraint `uq_artists_normalized_name`; inserting two rows with the same `normalized_name` raises `IntegrityError`.
- `test_enum_columns_are_non_native_varchar` — inspect the `Enum` type: `native_enum is False`; insert-and-read round-trips `ProviderId.SPOTIFY`, `MatchStatus.COMMUNITY_VERIFIED`, `LinkStatus.DISPUTED`, `DownloadStatus.QUEUED`, `BatchKind.PLAYLIST`, `LyricsKind.SYNCED`.
- `test_ordered_m2m_positions` — insert a track with three artists at positions 0/1/2 and a playlist with ordered tracks; read back ordered by `position`.
- `test_track_album_fk_set_null` — deleting an album nulls `tracks.album_id`.
- `test_cascade_deletes` — deleting a track cascades `track_artists`, `matches`, `lyrics`, `playlist_tracks` rows.
- `test_no_user_fk_on_votable_tables` — `matches.submitted_by`/`lyrics.submitted_by`/`download_jobs.requested_by`/`download_batches.requested_by` columns exist and carry **no** ForeignKey (asserts deferral design so Plan 6 adds only tables).
- `test_download_job_batch_fk_cascade` — `download_jobs.batch_id` FKs `download_batches.id` with `ondelete=CASCADE` and is indexed; deleting a batch deletes its jobs; `batch_id`/`list_position`/`skip_reason` are all nullable (a job may exist without a batch until Plan 7 wires submission); `attempts` is Integer NOT NULL default 0 (matches Plan 7's `test_download_schema_guard`).

**Step 3 — implement `db/models.py`.** One `class` per table using `Mapped[...]`/`mapped_column`, inheriting `Base` (+ `TimestampMixin` where timestamps apply). Encode every column, type, default, constraint, and index exactly as the schema contract. Relationships use `lazy="selectin"` (matches the existing repo decision "Set relationships to use selectin loading"): `Track.album`, `Track.artists` (via `track_artists`, `order_by=track_artists.c.position`), `Album.tracks`, `Artist.tracks`, `Playlist.tracks` (ordered), `Track.matches`, `Track.lyrics`. Association tables `track_artists` and `playlist_tracks` are `Table` objects (or association-object classes only if a payload beyond `position` is needed — it is not, so plain `Table`). Enum columns: `mapped_column(sa.Enum(ProviderId, native_enum=False, validate_strings=True, length=32))`. UUID PKs: `mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)`.

**Gates:** `make check` green (mypy strict: annotate all `Mapped[...]`). **Commit:** `feat(server): full v5 schema ORM models (spec §6.1)`.

---

### Task 3: Alembic — dual-dialect env, initial migration, up/down round-trip, CI Postgres service

**Files:**
- Create: `apps/server/alembic.ini`, `apps/server/alembic/env.py`, `apps/server/alembic/script.py.mako`, `apps/server/alembic/versions/0001_initial_schema.py`
- Create: `apps/server/src/spotdl_server/bootstrap.py`
- Create: `apps/server/tests/db/test_migrations.py`, `apps/server/tests/db/test_bootstrap.py`
- Modify: `.github/workflows/ci.yml`

**Step 1 — Alembic scaffold.** `alembic.ini` with `script_location = alembic`, no hardcoded `sqlalchemy.url` (env resolves it). `env.py`: import `Base.metadata` as `target_metadata`; resolve the URL from `Settings().effective_database_url()` (overridable by `-x db_url=...` and by env var so tests point at tmp files / Postgres); run migrations through an **async** engine (`run_async_migrations` using `connection.run_sync(context.run_migrations)`); `context.configure(..., render_as_batch=connection.dialect.name == "sqlite", compare_type=True)`. `render_as_batch` on SQLite makes any *future* ALTER migration (Plan 6/7 add tables only, but batch keeps SQLite safe) work.

**Step 2 — write `test_migrations.py` (RED).** Parametrized over dialects:
- SQLite: always runs. Create a tmp-file DB, run `alembic upgrade head`, assert the reflected table set equals `Base.metadata.tables` keys; run `alembic downgrade base`, assert no application tables remain (only `alembic_version`).
- **`upgrade == models` parity:** after `upgrade head` on a fresh SQLite DB, assert Alembic autogenerate detects **no** diff (`alembic revision --autogenerate` produces an empty upgrade, or use `alembic.autogenerate.compare_metadata` and assert `== []`). This mechanically proves the migration mirrors `models.py` — the primary anti-churn guarantee.
- Postgres: gated by a `postgres` fixture that reads `SPOTDL_TEST_POSTGRES_URL` (async DSN); if unset, `pytest.skip("no postgres")`. When set, same up/down + parity assertions against Postgres.
Add a `postgres` pytest marker and a `postgres_url` fixture in `tests/conftest.py`.

**Step 3 — implement `0001_initial_schema.py`.** Generate via `alembic revision --autogenerate`, then hand-verify it renders every table/column/constraint/index from the schema contract, with the naming convention applied — **including the Plan-7-reserved pieces**: the full `download_batches` table, the `BatchKind` enum column, and `download_jobs.batch_id` (FK→`download_batches.id`, CASCADE, indexed) / `list_position` / `skip_reason` / `attempts` (Integer NOT NULL default 0). `down_revision = None`. `downgrade()` drops all tables in FK-safe order (`download_jobs` before `download_batches`). The autogenerate-parity test from Step 2 mechanically enforces that these amendments are in the migration (they are in `Base.metadata`, so any omission shows up as a non-empty diff).

**Step 3b — `spotdl_server/bootstrap.py` (CONTRACT — Plan 8's required programmatic-migration seam; name and signature must match exactly).** Plan 8's embedded CLI transport runs migrations at startup by importing `spotdl_server` — never by shelling out to alembic or importing it directly (keeps `cli → server` clean):
```python
def upgrade_to_head(settings: Settings) -> None:
    """Run Alembic `upgrade head` programmatically against
    settings.effective_database_url(). Idempotent: a no-op when already at head.
    Locates alembic.ini/scripts relative to the installed spotdl_server package
    (importlib.resources / package-relative path), NOT the CWD, so it works from
    any working directory and from a wheel install."""
```
Implementation: build an `alembic.config.Config` pointing at the packaged `alembic.ini`/script dir, set `sqlalchemy.url` (or the `-x db_url` attribute the env.py already honors) from `settings.effective_database_url()`, call `alembic.command.upgrade(cfg, "head")`. Synchronous by design (called once at process startup, before the event loop or via `run_sync`); ensure the alembic scripts ship in the wheel (add the directory to `[tool.hatch.build.targets.wheel]` includes).

**Tests (`test_bootstrap.py`, offline):**
- `test_upgrade_to_head_creates_schema` — `upgrade_to_head(Settings(data_dir=tmp))` then reflect the SQLite file: table set == `Base.metadata.tables` keys and `alembic_version` is at head.
- `test_upgrade_to_head_is_idempotent` — calling it twice succeeds; schema unchanged.
- `test_upgrade_to_head_runs_from_any_cwd` — run with `monkeypatch.chdir(other_tmp)`; still succeeds (proves package-relative config resolution, the wheel/embedded case).

**Step 4 — CI (`.github/workflows/ci.yml`).** Add a Postgres service to the `python` job and expose the DSN so the Postgres-gated migration tests run in CI (they skip locally):
```yaml
  python:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: spotdl
          POSTGRES_PASSWORD: spotdl
          POSTGRES_DB: spotdl_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    env:
      SPOTDL_TEST_POSTGRES_URL: postgresql+asyncpg://spotdl:spotdl@localhost:5432/spotdl_test
    steps:
      # ... existing steps unchanged ...
```
(Keep every existing step; only add `services`, `env`.)

**Gates:** `make check` green (SQLite path). **Commit:** `feat(server): alembic dual-dialect env + initial schema migration; CI postgres service`.

---

### Task 4: Repositories — snapshots (upsert) + canonical entity CRUD

**Files:**
- Create: `apps/server/src/spotdl_server/repositories/__init__.py`, `repositories/snapshots.py`, `repositories/entities.py`
- Create: `apps/server/tests/repositories/__init__.py`, `tests/repositories/test_snapshots.py`, `tests/repositories/test_entities.py`
- Modify: `tests/conftest.py` (add a `session` fixture: builds an in-memory SQLite engine, `create_all`, yields an `AsyncSession`, rolls back)

**Contract vs freedom:** Repository **class names + public method signatures are CONTRACT** (services depend on them). All accept an `AsyncSession` in `__init__` (unit of work owned by the caller) and take/return **ORM models or plain values** — never Pydantic API schemas, never `ResolvedEntity`. Repositories never commit; the service/UoW commits.

**`SnapshotRepository` (CONTRACT):**
```python
class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None: ...
    async def upsert(self, *, provider, provider_entity_id, entity_type,
                     raw_payload, name=None, isrc=None, duration_ms=None,
                     artist_names=None, album_name=None, art_url=None,
                     expires_at=None) -> ProviderSnapshot: ...   # by (provider, provider_entity_id); refreshes payload+fetched_at
    async def get(self, provider, provider_entity_id) -> ProviderSnapshot | None: ...
    async def get_by_isrc(self, isrc: str) -> list[ProviderSnapshot]: ...
    async def get_fresh(self, provider, provider_entity_id, now) -> ProviderSnapshot | None: ...  # None if expired
```
Upsert uses a select-then-insert/update keyed on the unique constraint (portable across SQLite/Postgres; avoid dialect-specific `ON CONFLICT` to keep one code path).

**Entity repositories (CONTRACT — one per canonical type):** `TrackRepository`, `AlbumRepository`, `ArtistRepository`, `PlaylistRepository`, each `__init__(session)` with:
- `async def get(id) -> Model | None` (relations eager via selectin).
- `async def create(**fields) -> Model` / `async def update(model, **fields) -> Model`.
- `TrackRepository.get_or_create_by_isrc(isrc) -> tuple[Track, bool]` (canonical dedupe hook used by merge).
- `TrackRepository.set_artists(track, artist_ids_in_order)` and `PlaylistRepository.set_tracks(playlist, track_ids_in_order)` (manage ordered M2M `position`; `set_artists` replaces the full ordered set — re-runnable).
- `ArtistRepository.get_or_create_by_normalized_name(name: str) -> tuple[Artist, bool]` — computes `normalize_artist_name(name)`, returns the existing row for that key or creates one with `name=name` (original casing), `normalized_name=<key>`. The artist-dedup hook used by merge (Task 5).

**`normalize_artist_name` (CONTRACT — module-level pure function in `repositories/entities.py`):**
```python
def normalize_artist_name(name: str) -> str:
    """NFKC-normalize, casefold, collapse internal whitespace runs to one space, strip."""
```
Exactly the rule stated in the schema's artist-identity contract; this function is the single implementation (merge and any future correction flow import it — never re-derive the key inline).

**Tests (offline, in-memory SQLite):** upsert creates then updates the same row (count stays 1, payload refreshed); `get_by_isrc` returns all providers with that ISRC; `get_fresh` returns None past `expires_at`; entity create/get with relations; ordered M2M round-trips positions; `get_or_create_by_isrc` idempotent; `test_normalize_artist_name` (table-driven: `"  The  Beatles "` → `"the beatles"`, `"BØRNS"` → `"børns"`, NFKC full-width → ascii); `test_get_or_create_by_normalized_name_dedupes_case_and_whitespace` (`"The Beatles"` then `"the  beatles"` → same row, created flags `(True, False)`, display `name` keeps the first casing); `test_set_artists_is_replace_and_rerunnable`.

**Gates:** `make check` green. **Commit:** `feat(server): snapshot + canonical entity repositories`.

---

### Task 5: Deterministic snapshot → canonical merge (source-priority per field class)

**Files:**
- Create: `apps/server/src/spotdl_server/repositories/merge.py`
- Create: `apps/server/tests/repositories/test_merge.py`

**Contract vs freedom:** The **merge rules table below is CONTRACT.** Merge is **deterministic and re-runnable**: given the same set of snapshots for a canonical entity, it always yields the same canonical field values regardless of snapshot insertion order, and running it twice is a no-op. Implementation (how fields are pulled from `raw_payload` vs the normalized columns) is free, but the source-priority order and per-field-class selection rule are fixed.

**Source priority (spec §6.1): `SPOTIFY > DEEZER > ITUNES > MUSICBRAINZ`.** For any audio-provider snapshots that also carry metadata (YTMusic), they rank after MUSICBRAINZ. Define `SOURCE_PRIORITY: tuple[ProviderId, ...]` and a stable sort key.

**Merge rules table (CONTRACT) — for a canonical `tracks` row built from N snapshots:**

| Field class | Fields | Rule |
|---|---|---|
| Identity | `name`, `duration_ms`, `track_number`, `disc_number`, `explicit`, `year` | first non-null following SOURCE_PRIORITY |
| ISRC | `isrc` | first non-null following SOURCE_PRIORITY (Spotify → Deezer → MusicBrainz; iTunes has none) |
| Descriptive set | `genres` | first **non-empty** following SOURCE_PRIORITY (not unioned — deterministic single-source pick) |
| Media | `album` (→`AlbumRef`/`albums` row), `cover_url` | album identity from the highest-priority snapshot that has an album; `cover_url` = first non-null by priority |
| Prior | `popularity` | Spotify only (else NULL) |
| Artist set | `artists` (→`track_artists` rows) | the **full ordered name tuple from the single highest-priority snapshot that has a non-empty `artist_names`** (not a cross-source union — deterministic single-source pick, order preserved, index 0 = main artist) |

Albums merge with the same rule set (`name`, `album_artist`, `year`, `track_count`, `cover_url`). Artists merge `name`, `genres`, `image_url` (and `normalized_name` is always recomputed from the winning `name`). Playlists merge `name`, `description`, `owner`, `cover_url`.

**Artist-resolution step (CONTRACT — part of `merge_track`, runs after field merge):**
1. Take the winning ordered artist-name tuple per the "Artist set" rule above.
2. For each name, in order, call `ArtistRepository.get_or_create_by_normalized_name(name)` (Task 4) to resolve/create the canonical `artists` row. Names in the tuple that normalize to the same key resolve to the same row (deduped, first occurrence keeps its position).
3. `CanonicalMerger` (not the caller) then calls `TrackRepository.set_artists(track, resolved_artist_ids_in_order)` — a full replace, so re-running merge after a higher-priority source appears converges to that source's artist set without orphaned link rows.

The same mechanism applies in `merge_artist` for a direct ARTIST resolve: canonical identity there is *also* the normalized name (`get_or_create_by_normalized_name`), with `entity_links` rows added for its snapshots.

**Public API (CONTRACT):**
```python
class CanonicalMerger:
    def __init__(self, session: AsyncSession) -> None: ...
    async def merge_track(self, snapshots: Sequence[ProviderSnapshot]) -> Track: ...      # upsert canonical track + entity_links
    async def merge_album(self, snapshots, track_snapshots_by_pos) -> Album: ...
    async def merge_artist(self, snapshots) -> Artist: ...
    async def merge_playlist(self, snapshots, track_snapshots_ordered) -> Playlist: ...
```
Merge also creates/updates `entity_links` rows (`status=auto`) linking the canonical entity to each contributing snapshot. `merge.py` lives in the repositories layer, so it upserts `EntityLink` ORM rows directly (idempotent on the unique triple) — it does **not** depend on Task 6's `EntityLinkRepository` (which is the read/status API built afterwards), keeping this task green standalone. Canonical identity resolution: prefer an existing canonical entity found via ISRC (tracks) or via an existing `entity_links` row for any input snapshot; otherwise create. This makes re-resolution converge on one canonical row.

**Tests (offline, pure-ish with in-memory DB):**
- `test_priority_prefers_spotify_name` — Spotify + Deezer snapshots with different names → canonical takes Spotify's.
- `test_isrc_falls_through_to_deezer_when_spotify_missing`.
- `test_genres_first_nonempty` — Spotify empty genres, MusicBrainz has genres → MusicBrainz wins.
- `test_merge_is_order_independent` — merging `[deezer, spotify]` == merging `[spotify, deezer]`.
- `test_merge_is_rerunnable` — merging twice yields one canonical row and identical field values (no duplicate `entity_links`).
- `test_merge_dedupes_by_isrc` — two snapshots same ISRC → one canonical track, two entity_links.
- `test_duration_unit_trust` — Deezer snapshot stored in ms already (providers normalize per Plan 2); merge does not re-scale.
- `test_merge_resolves_artists_by_normalized_name` — Spotify snapshot `artist_names=["Daft Punk", "Pharrell Williams"]` → two `artists` rows created, `track_artists` positions 0/1; re-merging with a Deezer snapshot whose names differ only in case/whitespace creates **no** new artist rows.
- `test_merge_artist_set_single_source_ordered` — Spotify has 2 artists, MusicBrainz has 3 → track gets exactly Spotify's 2, in Spotify's order; re-merge is a full replace (no stale link rows).

**Gates:** `make check` green. **Commit:** `feat(server): deterministic source-priority canonical merge`.

---

### Task 6: Repositories — entity_links, matches, lyrics

**Files:**
- Create: `repositories/links.py`, `repositories/matches.py`, `repositories/lyrics.py`
- Create: `tests/repositories/test_links.py`, `test_matches.py`, `test_lyrics.py`

**`EntityLinkRepository` (CONTRACT):** `__init__(session)`; `async def upsert(entity_type, entity_id, snapshot_id, status=LinkStatus.AUTO) -> EntityLink` (by unique triple); `async def for_entity(entity_type, entity_id) -> list[EntityLink]`; `async def set_status(link, status)`.

**`MatchRepository` (CONTRACT):**
```python
class MatchRepository:
    def __init__(self, session: AsyncSession) -> None: ...
    async def replace_for_track(self, track_id, matches: Sequence[Match], matcher_version: str) -> list[MatchModel]: ...
    # upsert by (track_id, target_provider, target_id); preserves vote tallies + community_verified/rejected status on re-match
    async def list_for_track(self, track_id) -> list[MatchModel]: ...  # ordered: community_verified first, then score desc; rejected excluded by default
    async def get(self, match_id) -> MatchModel | None: ...
```
`replace_for_track` maps each `core.model.Match` → row (`target_provider=candidate.provider`, `target_id=candidate.provider_id`, `target_url=candidate.url`, `score`, `matcher_version`, `status`, `features=match.features.model_dump()`, denormalized candidate fields). **Preserve existing community state:** if a row already exists with `status in {community_verified, rejected}` or with nonzero vote tallies, keep its `status`/tallies rather than overwriting from a fresh AUTO match (this is what lets Plan 6 votes survive re-resolution — no schema change needed).

**`LyricsRepository` (CONTRACT):** `__init__(session)`; `async def upsert(track_id, source, kind, text) -> LyricsModel` (by `(track_id, source, kind)`, preserves tallies); `async def list_for_track(track_id) -> list[LyricsModel]` (synced before plain, then by `net_score` desc); `async def get(id)`.

**Tests (offline):** link upsert idempotent by triple + status change; `replace_for_track` dedupes by target and preserves `community_verified` status/tallies across a re-run; `list_for_track` ordering (community first, rejected excluded); lyrics upsert by triple, ordering synced-first.

**Gates:** `make check` green. **Commit:** `feat(server): entity-link, match, and lyrics repositories`.

---

### Task 7: Error envelope + exception handlers (spec §10 code table)

**Files:**
- Create: `apps/server/src/spotdl_server/api/__init__.py`, `api/errors.py`
- Create: `apps/server/src/spotdl_server/services/__init__.py`, `services/errors.py`
- Create: `apps/server/tests/api/__init__.py`, `tests/api/test_errors.py`
- Modify: `app.py` (register handlers — routers come in Task 10)

**Contract vs freedom:** The **`ErrorEnvelope` shape and the error-code table are CONTRACT** (generated clients in Plan 8 surface these codes as typed errors). Handler internals are free.

**`ErrorEnvelope` (CONTRACT):**
```python
class ErrorEnvelope(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] | None = None

class ErrorCode(StrEnum):   # the stable code vocabulary
    UNSUPPORTED_URL = "unsupported_url"
    NOT_FOUND = "not_found"
    NO_MATCH_FOUND = "no_match_found"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_AUTH_ERROR = "provider_auth_error"
    RATE_LIMITED = "rate_limited"
    VALIDATION_ERROR = "validation_error"
    DOWNLOADS_DISABLED = "downloads_disabled"   # defined now; raised in Plan 7
    DOWNLOAD_FAILED = "download_failed"         # defined now; raised in Plan 7
    INTERNAL_ERROR = "internal_error"
```

**Server-side not-found (CONTRACT — new file `services/errors.py`):** Plan 2's core exceptions carry only what they carry — `ProviderError` family has `.provider` (and `RateLimited` additionally `.retry_after`); `UnsupportedURL` and `NoMatchFound` carry only a message. The `detail` contract below uses **only attributes that actually exist**. For server-originated 404s (entity GETs on unknown ids) core's `EntityNotFound` is too thin, so the server defines its own richer exception at the raise site:
```python
# spotdl_server/services/errors.py  (importable by services AND api without layering violation)
from uuid import UUID
from spotdl_core.model import EntityType
from spotdl_core.providers import SpotdlError

class NotFoundError(SpotdlError):
    """A canonical entity was not found in the server DB."""
    def __init__(self, *, entity_type: EntityType, entity_id: UUID | str) -> None:
        super().__init__(f"{entity_type.value} {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id
```
Services (Tasks 8/9) raise `NotFoundError` — not core `EntityNotFound` — for DB lookups. Core `EntityNotFound` still maps to 404 (it surfaces when a provider reports the upstream entity gone) with its `.provider` as detail.

**Error-code mapping table (CONTRACT — every `detail` key is backed by a real attribute, noted per row):**

| Raised / condition | HTTP | `code` | `detail` (source attribute) |
|---|---|---|---|
| `UnsupportedURL` | 400 | `unsupported_url` | `{"value": str(exc)}` — Plan 2's `parse` raises `UnsupportedURL(value)`, so the message **is** the offending input |
| `NotFoundError` (server, `services/errors.py`) | 404 | `not_found` | `{"entity_type": exc.entity_type.value, "id": str(exc.entity_id)}` |
| `EntityNotFound` (core — provider reported the upstream entity missing) | 404 | `not_found` | `{"provider": exc.provider.value if exc.provider else None}` |
| `NoMatchFound` | 404 | `no_match_found` | `null` (carries only a message; the message string is the human context) |
| `ProviderUnavailable` | 502 | `provider_unavailable` | `{"provider": exc.provider.value if exc.provider else None}` |
| `ProviderAuthError` | 502 | `provider_auth_error` | `{"provider": exc.provider.value if exc.provider else None}` |
| `RateLimited` | 429 | `rate_limited` | `{"provider": ..., "retry_after": exc.retry_after}` + `Retry-After` header when `retry_after` is not None |
| FastAPI/Pydantic `RequestValidationError` | 422 | `validation_error` | `{"errors": exc.errors()}` |
| `DownloadFailed`/`ConversionFailed`/`MetadataEmbedFailed` | 500 | `download_failed` | `{"step": exc.step}` (Plan 7 raises; mapping defined now) |
| downloads-disabled guard | 403 | `downloads_disabled` | `null` (Plan 7) |
| any other `Exception` | 500 | `internal_error` | `null` (message generic; real error logged) |

**`register_exception_handlers(app: FastAPI) -> None` (CONTRACT):** installs handlers for `SpotdlError` (dispatch on subclass → row above; **`NotFoundError` is checked before `EntityNotFound`**, and subclass rows generally before their parents), `RequestValidationError`, and `Exception`. Each returns `JSONResponse(status_code, ErrorEnvelope(...).model_dump())`. A single `_status_and_code(exc) -> tuple[int, ErrorCode, dict|None]` mapper keeps it table-driven and testable in isolation.

**Tests (offline):** unit-test `_status_and_code` for each row **constructing each exception exactly as Plan 2/`services/errors.py` define it** (no invented kwargs); integration-test via a throwaway app with routes that raise each exception, asserting status, `code`, `detail`, and (for `RateLimited`) the `Retry-After` header. `test_not_found_error_beats_entity_not_found_dispatch`; `test_unhandled_exception_is_internal_error_and_hides_message` (message not leaked).

**Gates:** `make check` green. **Commit:** `feat(server): stable error envelope and exception handlers (spec §10)`.

---

### Task 8: ResolveService — cache-first resolve → snapshot → merge → canonical → kick matching

**Files:**
- Create: `services/dto.py`, `services/provider_search.py`, `services/resolve.py` (`services/__init__.py` exists from Task 7)
- Create: `apps/server/src/spotdl_server/api/deps.py` (partial: registry + session + service providers)
- Create: `apps/server/tests/fakes.py`, `tests/services/__init__.py`, `tests/services/test_resolve.py`, `tests/services/test_provider_search.py`
- Modify: `settings.py` or `deps.py` — `provider_context(settings) -> ProviderContext`; `app.py` — `create_app(settings, *, registry=None)` + lifespan (build engine, sessionmaker, `ProviderRegistry`; store on `app.state`; `aclose` on shutdown only what the app built)

**Contract vs freedom:** `ResolveService.__init__` collaborators and the `resolve()` return DTO are **CONTRACT** (routers + tests depend on them). No FastAPI/ORM types cross the service boundary — inputs are plain values, output is a `services/dto.py` dataclass.

**`services/dto.py` (service-layer DTOs — no HTTP, no ORM):** `ResolveResult`, `TrackView`, `AlbumView`, `ArtistView`, `PlaylistView`, `MatchView`, `LyricsView`, `SearchResult`. Each is a frozen dataclass/pydantic carrying only primitives + nested DTOs + `degraded_sources: tuple[str, ...]`. The API schema layer (Task 10) maps DTO → response model; this keeps ORM rows out of routers.

**`services/provider_search.py` (CONTRACT — the shared search helper; created HERE so this task is self-contained, and reused by Task 9's `SearchService`):**
```python
async def provider_search(
    registry: ProviderRegistry, query: str, *, limit: int = 20,
) -> tuple[list[Track], set[ProviderId]]:
    """Run every registry.capable(Searches) provider (PROVIDER_ORDER), concatenate
    results, de-duplicate by ISRC then by (name, main_artist) casefolded key,
    truncate to `limit`. Returns (tracks, failed_provider_ids); a ProviderError
    from one searcher never aborts the others."""
```
Pure orchestration over the registry — no DB session, no persistence (callers persist snapshots themselves).

**`ResolveService` (CONTRACT):**
```python
class ResolveService:
    def __init__(self, *, session: AsyncSession, registry: ProviderRegistry,
                 matcher_config: ScoringConfig = MATCHER_V5_DEFAULT) -> None: ...
    async def resolve(self, query: str) -> ResolveResult: ...
```
Algorithm:
1. **Parse.** Try `parse(query)` (URL / `provider:type:id`). On `UnsupportedURL`, treat `query` as free text → call `provider_search(registry, query)` (this task's helper), take the top track, and continue as if resolving that track's provider ref; if the search yields nothing, re-raise the original `UnsupportedURL`. (Free-text resolve returns the best-matching track entity.)
2. **Cache-first.** `SnapshotRepository.get_fresh(ref.provider, ref.entity_id, now)`. On hit, skip the network fetch for that provider.
3. **Fetch + snapshot.** For each `Resolves` provider that can serve `ref.provider` (primary = the ref's provider; enrichers optional), call `provider.resolve(ref)`. The primary is obtained via `registry.get(ref.provider)` — **wrap the documented `KeyError`** (id parses to a `ProviderId` the registry never registered): map it to `ProviderUnavailable(provider=ref.provider)` so it reaches the client as a 502 `provider_unavailable` envelope, never a 500 `internal_error`. Wrap each provider call: on `ProviderError` (unavailable/auth/rate-limited), **do not abort** — record the provider id in `degraded_sources` and continue with the remaining sources (spec §10 "no silent fallbacks"). Persist each success via `SnapshotRepository.upsert(...)` with normalized key fields extracted from the `ResolvedEntity`/`Track`.
4. **Merge.** Collect all snapshots for this entity (fresh cache + new) and run `CanonicalMerger.merge_*` → canonical row + `entity_links`.
5. **Kick matching (tracks only).** Gather `AudioCandidate`s from every `registry.capable(ProvidesAudio)` provider via `audio_candidates(track)` (each wrapped: failures → `degraded_sources`, never fatal), concatenate, run `match(track, candidates, matcher_config)`, persist via `MatchRepository.replace_for_track(...)`. For album/playlist, matching is **not** kicked per-track in Plan 5 (documented deferral — bulk matching belongs to Plan 7's queue; per-track resolve covers the primary flow). Commit the unit of work once.
6. Include `registry.unavailable` provider ids in `degraded_sources` too (constructor-level provider breakage is visible). Return the `ResolveResult` DTO with the typed entity view and `degraded_sources`.

**Degraded-sources contract:** `degraded_sources` is the sorted, de-duplicated set of `ProviderId` values that failed during this resolve (construction failure, resolve failure, or audio-candidate failure). Empty tuple when everything succeeded.

**`create_app` signature + lifespan wiring (CONTRACT — the `registry=` keyword is Plan 8's required injection seam, consumed by the embedded CLI transport and by every fake-registry test in this plan; name and semantics must match exactly):**
```python
def create_app(
    settings: Settings | None = None,
    *,
    registry: ProviderRegistry | None = None,   # fake/test + embedded-CLI injection seam (Plan 8)
) -> FastAPI: ...

@asynccontextmanager
async def lifespan(app):
    settings = app.state.settings
    engine = build_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)
    injected: ProviderRegistry | None = app.state.injected_registry  # set by create_app from the kwarg
    app.state.registry = injected or build_default_registry(provider_context(settings))
    try:
        yield
    finally:
        if injected is None:            # caller-owned registries are NOT closed by the app
            await app.state.registry.aclose()
        await engine.dispose()
```
Ownership rule (CONTRACT, per Plan 8's amendment): when `registry` is passed, the lifespan uses it instead of `build_default_registry(...)` and does **not** `aclose()` it — the caller owns its lifetime. When omitted, the app builds the default registry and closes it on shutdown. This keyword is the **single** fake-injection seam: Plan 5 tests build apps as `create_app(settings, registry=build_fake_registry(...))` (no `app.state` poking, no dependency-override gymnastics), and Plan 8's `EmbeddedTransport` passes its own registry the same way.

`deps.py`: `get_sessionmaker`/`get_registry` read `request.app.state`; `get_session` yields a session and commits/rolls-back; `get_resolve_service(session, registry)` composes the service.

**`tests/fakes.py` (the offline seam):** `FakeResolver`, `FakeSearcher`, `FakeAudioProvider`, `FakeLyricsProvider` implementing the Plan 2 Protocols with canned data; a `build_fake_registry(*providers, failing=...) -> ProviderRegistry` helper registering `ProviderSpec`s whose factories return the fakes (and one whose factory raises, to exercise `degraded_sources`).

**Tests (offline, in-memory DB + fake registry):**
- `test_resolve_url_miss_fetches_snapshots_merges_and_returns_track`.
- `test_resolve_cache_hit_skips_provider_call` (fresh snapshot; fake resolver asserts it was not called).
- `test_resolve_records_degraded_source_on_provider_failure` (one failing resolver → `degraded_sources` contains it, resolve still succeeds from another).
- `test_resolve_kicks_matching_and_persists_matches` (fake audio provider → matches stored; `list_for_track` non-empty).
- `test_resolve_free_text_falls_back_to_search`.
- `test_resolve_unsupported_and_no_result_raises` (free text with no search hit → the original `UnsupportedURL`).
- `test_resolve_unregistered_provider_maps_keyerror_to_provider_unavailable` (ref parses to a `ProviderId` absent from the fake registry → `ProviderUnavailable` with `.provider` set, not `KeyError`).
- `test_resolve_is_rerunnable` (resolving the same URL twice → one canonical track, matches replaced not duplicated).
- `test_create_app_uses_injected_registry` (in `tests/test_app.py`) — `create_app(settings, registry=fake)` serves requests from the fake providers; after app shutdown the fake registry is **still open** (its `aclose` was not called — assert via a recording `aclose` on the fake); `create_app(settings)` without the kwarg builds and closes its own registry on shutdown.

In `test_provider_search.py` (helper tested directly, no DB): merges two fake searchers in PROVIDER_ORDER; de-dupes by ISRC then `(name, main_artist)`; truncates to `limit`; one failing searcher → its id in the returned failed set, other results intact.

**Gates:** `make check` green. **Commit:** `feat(server): ResolveService with cache-first merge and match kick`.

---

### Task 9: SearchService + EntityService

**Files:**
- Create: `services/search.py`, `services/entities.py`
- Create: `tests/services/test_search.py`, `tests/services/test_entities_service.py`

**`SearchService` (CONTRACT):**
```python
class SearchService:
    def __init__(self, *, session: AsyncSession, registry: ProviderRegistry) -> None: ...
    async def search(self, query: str, *, limit: int = 20) -> SearchResult: ...
```
Delegates the fan-out/merge/de-dupe to `provider_search(registry, query, limit=limit)` (Task 8's helper — do **not** re-implement it), then snapshots each result track via `SnapshotRepository.upsert` (so a subsequent resolve is a cache hit) and returns a `SearchResult` DTO (`tracks: tuple[TrackView, ...]`, `degraded_sources` = the helper's failed set ∪ `registry.unavailable`, sorted). Provider failures are non-fatal → `degraded_sources`. **Cached:** results are persisted as snapshots; an optional lightweight query→results cache is out of scope (permanent snapshot cache is the durable layer). Empty results return an empty tuple (not an error).

**`EntityService` (CONTRACT):**
```python
class EntityService:
    def __init__(self, *, session: AsyncSession) -> None: ...
    async def get_track(self, id) -> TrackView: ...       # raises NotFoundError (services/errors.py) if absent
    async def get_album(self, id) -> AlbumView: ...
    async def get_artist(self, id) -> ArtistView: ...
    async def get_playlist(self, id) -> PlaylistView: ...
    async def get_matches(self, track_id) -> tuple[MatchView, ...]: ...   # from MatchRepository, raises if track absent
    async def get_lyrics(self, track_id) -> tuple[LyricsView, ...]: ...
```
Reads only — canonical rows already persisted by resolve. Maps ORM → DTO with relations (album, artists, playlist tracks). All getters raise the **server-side `NotFoundError(entity_type=..., entity_id=...)`** (Task 7, `services/errors.py`) when the entity does not exist — never core `EntityNotFound`, which is reserved for provider-reported misses; `get_matches`/`get_lyrics` return an empty tuple when the track exists but has no matches/lyrics yet.

**Tests (offline):** search delegates to `provider_search` (fake searchers) and snapshots results; failing searcher → degraded; entity getters return DTOs with relations; `get_track` missing → `NotFoundError` carrying `entity_type=TRACK` and the requested id; `get_matches` on existing-but-unmatched track → empty tuple; on missing track → `NotFoundError`.

**Gates:** `make check` green. **Commit:** `feat(server): SearchService and EntityService`.

---

### Task 10: API schemas + routers (`/api/v1`) + config extension + mode gating

**Files:**
- Create: `api/schemas.py`, `api/routers/__init__.py`, `api/routers/{resolve,search,entities,meta}.py`
- Modify: `app.py` (mount routers, keep the `create_app(settings, *, registry=None)` signature from Task 8), `api/deps.py` (finish service deps)
- Create: `tests/api/{test_resolve_api,test_search_api,test_entities_api,test_config}.py`
- Modify: `tests/test_app.py` (existing health/config tests stay green — extend config assertions)

**Contract vs freedom:** The **request/response Pydantic schemas are CONTRACT** (they define the OpenAPI the Plan 8 clients generate against). Router internals are free but each router file stays **≤200 lines** and contains **no business logic** (delegates to a service) and **no ORM import**.

**`api/schemas.py` (CONTRACT — response models):**
- `ResolveRequest{query: str}`.
- `TrackOut{id, name, artists: list[str], duration_ms, isrc, explicit, track_number, disc_number, year, genres: list[str], popularity, album: AlbumRef-like | None}`.
- `AlbumOut{id, name, album_artist, year, track_count, cover_url, tracks: list[TrackOut]}`.
- `ArtistOut{id, name, genres, image_url, tracks: list[TrackOut]}`.
- `PlaylistOut{id, name, description, owner, cover_url, tracks: list[TrackOut]}`.
- `EntityEnvelope{type: EntityType, track|album|artist|playlist: <Out> | None}` (discriminated on `type`; only one populated) OR a tagged union — implementer picks one and documents it; it must be stable for client generation.
- `ResolveResponse{ entity: EntityEnvelope, degraded_sources: list[str] }`.
- `SearchResponse{ results: list[TrackOut], degraded_sources: list[str] }`.
- `MatchOut{id, target_provider: ProviderId, target_id, target_url, score, matcher_version, status: MatchStatus, upvotes, downvotes, net_score, candidate_name, candidate_artists: list[str], candidate_duration_ms}`.
- `MatchesResponse{ track_id, matches: list[MatchOut] }`.
- `LyricsOut{id, source: ProviderId, kind: LyricsKind, text, upvotes, downvotes, net_score}`.
- `LyricsResponse{ track_id, lyrics: list[LyricsOut] }`.
- `ConfigResponse{ mode: DeploymentMode, features: FeatureFlags, matcher_version: str }`.
- `FeatureFlags{ downloads: bool, auth: bool, voting: bool, library: bool }`.
- `HealthResponse{ status: str }`.
- `ErrorEnvelope` (imported from `api/errors.py`) is declared as the documented error response for the routers via `responses=`.

**Routers (all under `/api/v1`):**
- `resolve.py`: `POST /resolve` (body `ResolveRequest`) → `ResolveResponse`; delegates to `ResolveService`.
- `search.py`: `GET /search?q=&limit=` → `SearchResponse`; delegates to `SearchService`.
- `entities.py`: `GET /tracks/{id}` → `ResolveResponse`-style `TrackOut` wrapper (or `EntityEnvelope`); `GET /albums/{id}`, `GET /artists/{id}`, `GET /playlists/{id}`; `GET /tracks/{id}/matches` → `MatchesResponse`; `GET /tracks/{id}/lyrics` → `LyricsResponse`. `{id}` is `UUID`. Delegates to `EntityService`.
- `meta.py`: `GET /health` → `HealthResponse` (unchanged behavior); `GET /config` → `ConfigResponse`.

**`GET /config` extension (spec §4).** `features` computed from `settings.mode` at request time from a startup-fixed value (mode does not change at runtime):
- `downloads = settings.mode is not DeploymentMode.HOSTED` (unchanged).
- `library = settings.mode is not DeploymentMode.HOSTED`.
- `auth = False` (hardcoded until Plan 6 flips it per mode).
- `voting = False` (until Plan 6).
- `matcher_version = MATCHER_V5_DEFAULT.matcher_version`.

**Deployment-mode gating (startup-time, spec §4).** In `create_app`, mount routers unconditionally for the Plan 5 surface (all read-only, available in every mode). The **download router is NOT created in this plan**; leave a single commented seam in `app.py`: `# if settings.mode is not DeploymentMode.HOSTED: app.include_router(downloads_router)  # Plan 7`. This proves the gating is a mount-time decision, not a per-request `if`. Add a test asserting no `/api/v1/downloads*` route exists in any mode (guards against Plan 7 accidentally always-mounting).

**Tests (offline, `httpx.ASGITransport`, fake registry injected via the `create_app(settings, registry=build_fake_registry(...))` seam — the same seam Plan 8's embedded transport uses):**
- resolve API: happy path returns `ResolveResponse` with `entity.type == "track"` and `degraded_sources`; unsupported URL → 400 `unsupported_url` envelope; provider failure surfaces in `degraded_sources` (200, not 502, because another source succeeded); total provider unavailability → 502 `provider_unavailable`.
- search API: returns results; `q` missing → 422 `validation_error`.
- entities API: `GET /tracks/{id}` 200; unknown id → 404 `not_found`; `/matches` and `/lyrics` shapes; `/matches` on unknown track → 404.
- config: `test_config_selfhost` (downloads/library true, auth/voting false, matcher_version present); `test_config_hosted` (downloads/library false); `test_config_embedded`. Keep/extend the existing `tests/test_app.py` assertions.
- `test_no_download_routes_mounted_in_any_mode`.

**Router-size gate:** add `test_routers_under_200_lines` (asserts each file in `api/routers/` is ≤200 lines) — a cheap mechanical guard for the layering rule.

**Gates:** `make check` green. **Commit:** `feat(server): /api/v1 resolve/search/entity/config routers + schemas`.

---

### Task 11: OpenAPI export as a deterministic build artifact + in-sync test

**Files:**
- Create: `apps/server/scripts/export_openapi.py`, `apps/server/openapi.json`
- Create: `apps/server/tests/test_openapi.py`
- Modify: root `Makefile` (add `openapi` target)

**Step 1 — `scripts/export_openapi.py` (CONTRACT — deterministic output).** Build the app in a fixed mode (`Settings(mode=DeploymentMode.SELFHOST)` so the full read surface is present), call `app.openapi()`, and write `openapi.json` with `json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`. `sort_keys=True` guarantees byte-stable output across runs/machines (the Plan 8 client generation diffs against this file). Pin `app.version` to `__version__` (already stable). Accept an optional `--check` flag that compares without writing (exit 1 on drift).

**Step 2 — `Makefile` target.**
```make
openapi:
	uv run python apps/server/scripts/export_openapi.py
```
Add `openapi` to `.PHONY`.

**Step 3 — `tests/test_openapi.py`.** `test_openapi_in_sync`: regenerate the schema in-memory, compare to the committed `openapi.json` byte-for-byte; on mismatch fail with the message "run `make openapi`". This makes the artifact self-checking in CI. Also `test_error_envelope_documented`: assert `ErrorEnvelope` is a component schema and appears in at least the resolve route's `responses`.

**Step 4 — generate + commit `openapi.json`.** Run `make openapi`; commit the file.

**Gates:** `make check` green (the in-sync test passes because the file was just generated). **Commit:** `feat(server): deterministic OpenAPI export artifact + in-sync test`.

---

### Task 12: Layering enforcement + integration smoke + docs

**Files:**
- Modify: `.importlinter` (add intra-server contracts)
- Create: `apps/server/tests/test_layering.py`, `apps/server/tests/test_integration_resolve_flow.py`
- Modify: `apps/server/README.md` or `docs/` note (layering rules; optional)

**Step 1 — import-linter intra-server contracts (CONTRACT enforcement of §6 layering).** Extend `.importlinter` (keep existing `layers` and `no_cli_core` contracts):
```ini
[importlinter:contract:server_layers]
name = Server layering: routers -> services -> repositories -> db
type = layers
containers = spotdl_server
layers =
    api.routers
    services
    repositories
    db

[importlinter:contract:routers_no_orm]
name = Routers must not import SQLAlchemy/ORM
type = forbidden
source_modules = spotdl_server.api.routers
forbidden_modules = sqlalchemy | spotdl_server.db.models

[importlinter:contract:services_no_fastapi]
name = Services must not import FastAPI
type = forbidden
source_modules = spotdl_server.services
forbidden_modules = fastapi
```
(`api.deps` and `api.errors` are HTTP glue and intentionally sit outside the `services` layer; they may import both FastAPI and services. If import-linter flags `deps.py`↔`services` layering, place `deps.py` at the `api.routers` layer level via a `containers`/module-tag adjustment documented in the task.)

**Step 2 — `test_layering.py`.** Belt-and-suspenders beyond import-linter: assert (via `ast`/module inspection) that no file under `api/routers/` imports `sqlalchemy` or `spotdl_server.db.models`, and no file under `services/` imports `fastapi`. Re-assert the ≤200-line router rule here (single home for the layering guards).

**Step 3 — `test_integration_resolve_flow.py` (offline end-to-end).** With a real tmp-file DB migrated via `bootstrap.upgrade_to_head(settings)` (exercising the Plan 8 boot path and proving the migration is the real schema), a fake registry passed through `create_app(settings, registry=...)` (resolver + audio + lyrics fakes, plus one failing provider), and `httpx.ASGITransport`:
`POST /resolve {url}` → assert `TrackOut` + `degraded_sources` includes the failing provider → `GET /tracks/{id}` matches → `GET /tracks/{id}/matches` non-empty and ordered → `GET /tracks/{id}/lyrics` present → re-`POST /resolve` same URL → still one canonical track, matches replaced not duplicated. This is the Plan 5 acceptance test.

**Step 4 — verify `lint-imports` passes** (`uv run lint-imports`) with the new contracts.

**Gates:** `make check` green. **Commit:** `test(server): layering contracts + offline resolve integration flow`.

---

## Self-review

**Every §6.1 table/column accounted for.** The authoritative schema section defines all twelve Plan-5 tables — `provider_snapshots`, `albums`, `artists`, `tracks`, `playlists`, `track_artists`, `playlist_tracks`, `entity_links`, `matches`, `lyrics`, `download_batches`, `download_jobs` — with full column lists, types, nullability, defaults, constraints, and indexes. `download_batches` + `download_jobs` are schema-only (Plan 7), and fold in Plan 7's required amendments verbatim (the `download_batches` table, the `BatchKind` enum, and `download_jobs.batch_id`/`list_position`/`skip_reason`/`attempts`) so Plan 7 ships zero migrations and Plan 7's Task-1 guard test passes against this schema as drafted. `users`, `oauth_identities`, `refresh_tokens`, `api_tokens`, `votes`, `reports` are explicitly deferred to Plan 6 and, by design (vote-tally columns on votable tables now; user references as FK-less nullable UUIDs), require **no ALTER** of any Plan-5 table — only new-table migrations. Task 2's `test_models.py` mechanically pins every column; Task 3's autogenerate-parity test proves migration == models on both dialects. This is the anti-churn guarantee against the reference branch's 18 migrations / 4 entity reworks.

**§6.2 Plan-5 subset fully routed.** `POST /resolve` (Task 8/10), `GET /search` (Task 9/10), `GET /tracks|albums|artists|playlists/{id}` (Task 9/10), `GET /tracks/{id}/matches` (Task 6/9/10), `GET /tracks/{id}/lyrics` (Task 6/9/10), `GET /config` (extended, Task 10), `GET /health` (kept, Task 10). Explicitly **out of scope** and NOT routed here: `POST /tracks/{id}/matches`, all `*/vote`, `POST /reports`, `auth/*`, `GET /metrics`, downloads, `WS /ws/progress`, admin.

**Layering rules stated as enforceable constraints.** Routers ≤200 lines + HTTP-only + no ORM import (Task 10/12, import-linter `routers_no_orm` + `test_layering.py`); services take/return DTOs, no FastAPI import (`services_no_fastapi`); repositories are the sole SQLAlchemy holders (`server_layers` layers contract); core is reached only via `ProviderRegistry` and `match()`.

**Error envelope + degraded sources.** §10 envelope `{code, message, detail}` with the full code table (Task 7); every `detail` key in the mapping table is backed by an attribute that actually exists on the Plan 2 exceptions (`.provider`, `.retry_after`, `.step`, message-as-value for `UnsupportedURL`) or on the server-side `NotFoundError` defined at the raise site — no invented attributes. `degraded_sources[]` threaded through `ResolveResult`/`SearchResult` DTOs and both response schemas, populated from per-call provider failures + `registry.unavailable` (Task 8/9); `ProviderRegistry.get()`'s documented `KeyError` is mapped to `provider_unavailable`, never a 500. Asserted end-to-end in Task 12.

**Artist canonical identity is closed, not implied.** Tracks arrive with artists as name tuples only, so the schema carries `artists.normalized_name` (unique, NFKC+casefold+whitespace-collapse rule spelled out once as `normalize_artist_name`), `ArtistRepository.get_or_create_by_normalized_name` is the single dedup hook, and Task 5's merge contract states exactly who resolves names and calls `TrackRepository.set_artists` (the `CanonicalMerger`, full-replace, order-preserving). The unique key doubles as the future duplicate-cleanup boundary.

**Task ordering is strictly green-per-task.** The multi-provider search fan-out (`services/provider_search.py`) is created in Task 8 (with its own tests) because ResolveService's free-text path needs it; Task 9's SearchService reuses it rather than defining it. `services/errors.py` (`NotFoundError`) lands in Task 7 with the handlers that consume it, before any service raises it.

**Downstream-plan seams folded in (Plan 8 required amendments).** `create_app(settings, *, registry: ProviderRegistry | None = None)` is the CONTRACT injection seam (Task 8): an injected registry is used instead of `build_default_registry` and is never closed by the app (caller-owned — pinned by `test_create_app_uses_injected_registry`); it is the one mechanism this plan's own API/integration tests use, so the seam Plan 8's `EmbeddedTransport` depends on is exercised on every CI run. `spotdl_server.bootstrap.upgrade_to_head(settings)` (Task 3, CONTRACT) runs Alembic programmatically against `settings.effective_database_url()` with package-relative config resolution (works from any CWD and from a wheel), is idempotent, and is the only migration entry point the CLI may touch — tested by `test_bootstrap.py` and exercised end-to-end in Task 12's integration flow.

**Type consistency with core contracts.** Services consume `ResolvedEntity`, `Track`, `AudioCandidate`, `Lyrics`, `Match`, `FeatureVector` from `core.model` verbatim; `duration_ms` stays milliseconds end-to-end (providers normalize per Plan 2; merge never re-scales); ORM enum columns reuse the exact `ProviderId`/`EntityType`/`MatchStatus`/`LyricsKind` classes (no parallel definitions); `matcher_version` flows `ScoringConfig.matcher_version` → `matches.matcher_version` column → `MatchOut`; `Match.features` (`FeatureVector | None`) serializes to the `matches.features` JSON column. Registry/matcher are consumed exactly at the CONTRACT signatures quoted in "What already exists".

**No TBDs.** Every task has exact files, signatures, test names, and gates. The two implementer choices left open (tagged-union vs discriminated `EntityEnvelope`; `deps.py` layer placement) are bounded with a "pick one and document; must be stable for client generation" instruction, not open questions.

**Deployment-mode gating stays startup-time.** No per-request mode conditionals; the download router seam is a mount-time comment (Task 10) with a test asserting no download routes exist in any mode — trivial now, load-bearing in Plan 7.

### Anti-pattern cross-check (xnetcat-rewrite backend: 18 migrations, 4 entity reworks)

The reference branch's schema failure was inspected directly. Its trajectory: **003** typed tables (`artists`/`albums`/`playlists` + typed `*_platform_links` + `playlist_tracks.position`) → **015/016** pivot to a generic `entities` + `entity_snapshots` + `entity_relations` model with a `canonical` **JSON blob** holding merged domain state, tearing down 11 typed tables → **017** re-key entities (`entity_key` from name/artist/duration to ISRC-first) via painful `canonical->>'isrc'` data surgery → **018** delete all entity data, drop `entity_key` entirely, split canonical into a new table. Each Plan-5 decision is a direct antidote:

| Reference failure | Concrete evidence | Plan 5 antidote |
|---|---|---|
| Merged domain state in a JSON blob (`entity_canonicals.canonical`), forcing `json_extract`/`->>` queries and re-key surgery | migrations 015, 017 | Typed canonical columns on `tracks`/`albums`/`artists`/`playlists`; JSON used only for `raw_payload` + small normalized value lists |
| Generic `entity_relations` dropped first-class ordering (`position` lost when playlist links went generic) | migrations 003 vs 015 | Typed ordered M2M `playlist_tracks`/`track_artists` with a real `position` column and `order_by` |
| Synthetic `entity_key` string churned twice (rekeyed in 017, deleted in 018) | migrations 017, 018 | UUID PKs + ISRC/entity_links-based canonical dedupe; no synthetic natural-key string to churn |
| Field-provenance table (`entity_field_provenance`) added complexity | migration 015 | Spec §2's "no field-provenance table" honored — merge is deterministic + re-runnable instead (Task 5) |
| Dangling polymorphic `entity_id` GUIDs with no FK (`metadata_reports`, `refresh_cooldowns`) | models | The one polymorphic ref here (`entity_links.entity_type+entity_id`) is bounded — created only by merge, disambiguated by `entity_type`; every other reference is a real typed FK |
| Dual vote sources of truth (rows + denormalized counters, inconsistent) | `entity_relations`/`lyrics` | Denormalized tallies (`upvotes/downvotes/net_score`) are the display cache; Plan 6's `votes` rows are the ledger that updates them — one write path, designed now so no ALTER |
| Inconsistent JSON typing (`JSONType` JSONB-aware vs plain `sa.JSON`) | `base.py` | One portable `sa.JSON` everywhere; enums non-native VARCHAR+CHECK — identical DDL on SQLite and Postgres |

The `test_models.py` column pin + the `test_migrations.py` autogenerate-parity assertion together make a silent schema drift impossible, which is the mechanism that would have caught the reference branch's reworks before they shipped as migrations.
