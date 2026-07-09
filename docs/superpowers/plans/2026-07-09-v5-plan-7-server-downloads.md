# spotDL v5 `apps/server` Download Queue & Delivery Implementation Plan (Plan 7 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement spec §6.3's server-side download system on top of Plans 4–6: a **DB-backed `download_jobs` queue** driven by an **in-process asyncio worker pool** (no Redis/celery — one container, one volume), **WebSocket progress** fan-out, **browser file delivery**, and **batch orchestration** (album/playlist expansion, m3u generation, archive maintenance, `.spotdl` v2 save-file emission). The §6.2 download surface (`POST/GET/DELETE /downloads`, `GET /downloads/{id}/file`, `WS /ws/progress`, plus batch/save-file endpoints) is mounted **only** in `selfhost` and `embedded` modes — **hosted never mounts any of it** (startup gating). Jobs **survive restarts**: on boot, orphaned `running` jobs are recovered per the state-machine contract. The download **engine** itself (Plan 4 `DownloadEngine`) is consumed unchanged; this plan owns everything *around* it — queueing, concurrency, progress, delivery, and batch post-processing.

**Architecture:** Same strict layering as Plans 5/6: `api.routers` (HTTP/WS only, ≤200 lines each, no business logic, no ORM import) → `services` (orchestration; no FastAPI/SQLAlchemy types in public signatures) → `repositories` (DB only) → `db`. The worker pool, progress hub, and download engine are **leaf runtime collaborators** built once in the FastAPI **lifespan**, stored on `app.state`, injected via dependencies, and **drained/closed on shutdown** — no module-level mutable singletons (mirrors Plan 5's engine/registry and Plan 6's clock/limiter wiring). The download engine (`spotdl_core.download.DownloadEngine`) is reached only through `packages/core` (spec §3); the server never re-implements pipeline logic. **Cross-process claiming is a non-goal**: the queue is owned by exactly **one** process's pool (the single container / the embedded CLI process), so claim safety comes from single-process ownership, not distributed locks — this boundary is documented and tested.

**Tech Stack:** Python 3.13, FastAPI (incl. `WebSocket`), Starlette `FileResponse`, SQLAlchemy 2 async ORM, Pydantic v2 + pydantic-settings, `asyncio` (worker pool, `asyncio.Queue`, `asyncio.Lock`, task cancellation). Reuses Plan 4 `spotdl_core.download` (engine + `post`/`paths` batch utilities), Plan 5 repositories/services (resolve/entity), Plan 6 auth (`AuthContext`, `require_user`, `Clock`). Tests: pytest + pytest-asyncio, httpx `ASGITransport` for HTTP, Starlette `TestClient`/`httpx-ws`-style WS testing via the ASGI app, in-memory + tmp-file SQLite. The default suite is **fully offline**: a **`FakeDownloadEngine`** is injected at the worker-pool construction seam; no yt-dlp/ffmpeg/network is touched.

## Global Constraints

- Python `>=3.13`; single uv lockfile at the workspace root.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Dependency direction (import-linter): `core ← server ← cli`. `spotdl_server` may import `spotdl_core`; never `spotdl_cli`. Server intra-layering contracts from Plan 5 Task 12 (`server_layers`, `routers_no_orm`, `services_no_fastapi`) stay green — this plan adds `services/downloads.py`, `services/worker.py`, `services/batch.py`, repositories, and routers that must obey them (the worker pool sits at/below the service layer; the progress hub and WS glue sit in `api/` because they touch `WebSocket`).
- New runtime dependencies: **none** (asyncio/Starlette/FastAPI already present; the download engine is `spotdl-core`). New test-only deps: none beyond Plan 5/6's dev group.
- **No module-level mutable singletons.** The engine, worker pool, and progress hub live on `app.state`, built in the lifespan, drained/closed on shutdown.
- **Layering is a contract.** Routers import only `fastapi`, Pydantic API schemas, service classes, `spotdl_server.auth` value types (`AuthContext`), and the progress-hub type; never `sqlalchemy`/ORM. Services import repositories, core, auth/clock — never `fastapi`. Repositories are the only SQLAlchemy holders. Routers stay ≤200 lines.
- TDD: every task writes failing tests first (RED), then implements to green. The default suite is **offline** — no real download engine, no network, no ffmpeg, no Postgres, no Redis.
- All test directories are packages (`__init__.py`); pytest runs with `--import-mode=importlib`. `apps/server/tests/conftest.py` already strips `SPOTDL_`-prefixed env vars.
- `make check` (lint + typecheck + test + web-check) must pass at the end of **every** task. `make check` runs `pytest -m 'not network'`; Postgres tests stay gated by the `postgres` marker/skip from Plan 5.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

---

## ⚠️ REQUIRED Plan-5 amendments (schema — must land in Plan 5, NOT ALTERed here)

Plan 5 states its schema is designed complete so "Plan 7 mounts the router and worker **without a migration**" (plan-5-draft.md line 273). Three queue needs — batch grouping, skip disambiguation, and recovery-integrity marking — are **not** met by Plan 5's `download_jobs` as drafted. To honour the anti-churn rule ("never `ALTER` a table defined in a prior plan") these **must be added to Plan 5's `db/models.py`, `db/enums.py`, and migration `0001_initial_schema.py` as *defined-now / used-in-Plan-7*** — exactly the pattern Plan 5 already uses for `download_jobs` itself. **If Plan 5 has already been executed, these ship as a small Plan-5 follow-up migration `0001x`, not as ad-hoc `op.add_column` inside a Plan 7 migration.** Plan 7 itself adds **no** migration; Task 1 includes a guard test that fails loudly if these are absent.

**Amendment A — new server-only enum in `db/enums.py`:**
```python
class BatchKind(StrEnum):
    SINGLE = "single"      # one submitted track/url
    ALBUM = "album"        # album url expanded to N tracks
    PLAYLIST = "playlist"  # playlist url expanded to N tracks
```

**Amendment B — new table `download_batches`** (groups the N jobs produced by one `POST /downloads`; holds the batch-level post-processing config the finalizer needs). Cross-dialect rules identical to Plan 5 (UUID PK `default=uuid.uuid4`; enum `native_enum=False, length=32`; `TimestampMixin`):

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `kind` | Enum(BatchKind) | no | | single/album/playlist |
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

Index: `INDEX (requested_by)`.

**Amendment C — four columns added to `download_jobs`** (Plan 5 table):

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `batch_id` | Uuid FK→download_batches.id | yes | | `ondelete=CASCADE`, indexed; groups a submission (single-track = batch of one) |
| `list_position` | Integer | yes | | 1-based index within the batch → `{list-position}` |
| `skip_reason` | String(32) | yes | | set when a `completed` job was actually a skip (`already_exists`/`in_archive`/`skip_file`/`explicit_filtered`); NULL = a real download |
| `attempts` | Integer | no | `0` | incremented by `requeue()`/`recover_orphaned()`; `attempts > 0` ⇒ the worker forces `overwrite=FORCE` on re-run (recovery-integrity rule, CONTRACT 1) |

Rationale for `skip_reason`: `DownloadStatus` (Plan 5) has no `skipped` value; mapping `DownloadOutcome.SKIPPED` → `completed` + `skip_reason` keeps the enum stable (no ALTER of the enum) while preserving the skip fact across restarts. Rationale for `attempts`: a crash or drain-cancellation mid-Convert/Embed can leave a converted-but-untagged (or partial) file at the planned output path, and the job row does not learn its `output_path` until completion — so the re-run integrity decision (CONTRACT 1) must ride on the row, not be inferred from the filesystem. `download_jobs.progress` (`Float 0..1`) and `updated_at` (has `onupdate`) already exist and serve as the progress column + de-facto heartbeat.

**Why no lease/heartbeat column is required (honest single-process design):** crash recovery keys on the **single-process ownership invariant**, not a lease clock. At boot, *before* the pool starts, any row in status `running` is necessarily orphaned by a crashed prior process (no other process ever claims these rows). So recovery is unconditional on `status='running'`, needing no `lease_expires_at`. `updated_at` already advances on every throttled progress write, so if a future multi-process design is ever adopted it can treat `updated_at` as the heartbeat with a lease window — but v1 deliberately does not, and this is documented and tested (Task 6). **Net: Plan 7 introduces zero new lease columns.**

**These amendments touch Plan 5's `test_models.py`/`test_migrations.py` expected-column dicts.** Plan 6's `test_no_plan5_table_altered` compares `matches`/`lyrics`/`entity_links` only (not `download_jobs`), so it is unaffected.

---

## What already exists (consumed, not recreated)

- **Plan 4 `spotdl_core.download` (the engine + batch utilities):**
  - `DownloadEngine(config, *, fetcher, cover=None, lyrics_search=None, sponsor_block=None)`; `async download(request: DownloadRequest, on_progress: ProgressCallback | None = None) -> DownloadOutcome` — **never raises for per-track failures**; returns a `FAILED` outcome tagged with `failed_step`. `build_default_engine(config) -> DownloadEngine` (lazy — importable without network/ffmpeg).
  - `DownloadConfig(output_dir, temp_dir, ffmpeg_path="ffmpeg", cookie_file=None, proxy=None, ytdlp_args=(), ffmpeg_args=())` (frozen dataclass).
  - `DownloadRequest(track, candidate, output_template, output_format=OutputFormat.MP3, bitrate=BITRATE_AUTO, overwrite=OverwriteMode.SKIP, restrict=RestrictMode.NONE, max_filename_length=None, lyrics=None, embed_lyrics=True, skip_album_art=False, retain_track_cover=False, id3_separator="/", track_url=None, generate_lrc=False, sponsor_block=False, respect_skip_file=False, create_skip_file=False, skip_explicit=False, archive=frozenset(), known_paths=(), detect_formats=(), list_name=None, list_position=None, list_length=None)` (frozen).
  - `DownloadOutcome{status: OutcomeStatus, track, path, skip_reason: SkipReason|None, failed_step: str|None, error: str|None}`; `OutcomeStatus(DOWNLOADED|SKIPPED|FAILED)`; `SkipReason(ALREADY_EXISTS|SKIP_FILE|IN_ARCHIVE|EXPLICIT_FILTERED)`.
  - `ProgressEvent{phase: ProgressPhase, percent: int|None, message: str|None}` (frozen); `ProgressPhase(PLAN|FETCH|CONVERT|EMBED|POST|DONE|SKIPPED|ERROR)`; `ProgressCallback = Callable[[ProgressEvent], None]` — **synchronous, best-effort, must never raise into the pipeline**.
  - `OutputFormat(MP3|M4A|FLAC|OGG|OPUS|WAV)`, `OverwriteMode(SKIP|FORCE|METADATA)`, `RestrictMode(NONE|ASCII|STRICT)`, `Bitrate = str`, `BITRATE_AUTO="auto"`, `BITRATE_DISABLE="disable"`.
  - **Batch utilities** (`spotdl_core.download.post` / `.paths` — Plan 4 Tasks 4 & 8, deliberately deferred to *this* plan's orchestration): `post.M3uEntry{track: Track, path: Path, list_name: str|None}`; `post.create_m3u_content(entries, template, output_format, *, restrict=RestrictMode.NONE, detect_formats=()) -> str`; `post.gen_m3u_files(entries, file_name, template, output_format, *, restrict, detect_formats) -> list[Path]`; `post.archive_update(current: frozenset[str], results: Iterable[tuple[str, bool]], *, add_unavailable: bool) -> frozenset[str]`; `paths.load_archive(path) -> frozenset[str]`; `paths.save_archive(path, urls) -> None`.
- **Plan 5:** `db/models.py` (`DownloadJob`, `Track`, `Match`, `Album`, etc.); `db/enums.py` `DownloadStatus(QUEUED|RUNNING|COMPLETED|FAILED|CANCELLED)`; `db/engine.py` `build_engine`/`build_sessionmaker`; `api/errors.py` `ErrorEnvelope{code,message,detail}` + `ErrorCode` (includes `DOWNLOADS_DISABLED="downloads_disabled"`, `DOWNLOAD_FAILED="download_failed"`, `NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`) + `register_exception_handlers`; the `DownloadFailed/ConversionFailed/MetadataEmbedFailed → 500 download_failed {"step": exc.step}` and `downloads-disabled → 403 downloads_disabled` rows are **already in Plan 5's mapping table** (defined-now, raised-here). `services/errors.py` `NotFoundError(entity_type, entity_id)`. `api/deps.py` `get_sessionmaker`/`get_registry`/`get_session`. `services/resolve.py` `ResolveService`, `services/entities.py` `EntityService` (used to expand album/playlist → tracks + matches). `api/schemas.py` `ConfigResponse{mode, features, matcher_version}`, `FeatureFlags{downloads, auth, voting, library}` (downloads/library already `mode is not HOSTED`). `scripts/export_openapi.py` + committed `openapi.json` + `test_openapi.py` + `make openapi`.
- **Plan 6:** `auth/context.py` `AuthContext{kind: "anonymous"|"user"|"pat", user_id, is_admin, token_id}` + `ANONYMOUS` + `.authenticated`; `api/deps.py` `get_auth_context(request, session, clock) -> AuthContext` (never raises → `ANONYMOUS`), `require_user`, `require_admin`; `auth/clock.py` `Clock`/`SystemClock` (+ `FakeClock` in conftest); `auth/tokens.py` `TokenService.verify_access`, `is_pat`, `sha256_hex`; settings `auth_enabled: bool | None` + the **derived `auth_active()`** gate (`None` → active except in `EMBEDDED`) and `require_auth_secret()` (startup fail-fast pattern this plan mirrors). **Sequencing note:** Plan 7 executes after Plan 6 and hard-imports `AuthContext`/`get_auth_context`/`TokenService` — "downloads work with auth disabled" means *auth deactivated via config* (`auth_active()` False, e.g. embedded default or `SPOTDL_AUTH_ENABLED=false`), not that this plan runs without Plan 6's code being present.

## Plan series roadmap (context — not part of this plan)

Plan 1 bootstrap → Plan 2 providers → Plan 3 matching → Plan 4 download → Plan 5 server foundation → Plan 6 auth + community → **Plan 7 downloads + WS (this plan)** → Plan 8 clients + CLI (consumes the `.spotdl` v2 contract defined here) → Plan 9 TUI → Plan 10 web → Plan 11 deploy.

## Package layout produced by this plan

```
apps/server/src/spotdl_server/
├─ settings.py                     # + download settings + download_config()/effective_library_path() (Task 1)
├─ downloads/                      # leaf domain package (pure-ish; no fastapi, no ORM) below services
│  ├─ __init__.py
│  ├─ progress.py                  # overall_progress(), phase weights, ProgressThrottle (Task 5)   [CONTRACT]
│  ├─ savefile.py                  # SaveFileV2 pydantic model + build_save_file()/dump (Task 7)     [CONTRACT: .spotdl v2]
│  └─ worker.py                    # DownloadWorkerPool + state machine + crash recovery (Task 6)    [CONTRACT]
├─ repositories/
│  ├─ downloads.py                 # DownloadJobRepository (claim/list/filter/update/recover) (Task 3) [CONTRACT]
│  └─ batches.py                   # DownloadBatchRepository (create/get/aggregate/finalize) (Task 3)  [CONTRACT]
├─ services/
│  ├─ downloads.py                 # DownloadQueueService: submit(expand)/list/get/cancel (Task 4)     [CONTRACT]
│  └─ batch.py                     # BatchFinalizer: archive + m3u + save-file emission (Task 7)        [CONTRACT]
├─ api/
│  ├─ progress_hub.py              # ProgressHub (WS fan-out) — imports fastapi.WebSocket (Task 5)     [CONTRACT]
│  ├─ schemas.py                   # + download request/response + WS message models (Task 2)          [CONTRACT]
│  ├─ deps.py                      # + get_download_queue_service, require_download_access, get_hub/pool (Task 8)
│  └─ routers/
│     ├─ downloads.py              # POST/GET/DELETE /downloads (+ /{id}/file, /batches/...) (Task 9)   [CONTRACT surface]
│     └─ progress_ws.py            # WS /ws/progress (Task 10)                                          [CONTRACT protocol]
└─ app.py                          # lifespan: build engine/pool/hub, recover, drain; mode gating (Task 8)

apps/server/scripts/export_ws_schema.py   # WS JSON Schema export (Task 2)  [CONTRACT artifact]
apps/server/ws-protocol.json              # committed WS protocol artifact for Plan 8 codegen (Task 2)

apps/server/tests/
├─ conftest.py                     # + FakeDownloadEngine, download settings fixture, pool/hub fixtures
├─ downloads/    test_progress.py, test_worker.py, test_savefile.py
├─ repositories/ test_downloads_repo.py, test_batches_repo.py
├─ services/     test_download_queue_service.py, test_batch_finalizer.py
└─ api/          test_downloads_api.py, test_download_file_api.py, test_progress_ws.py,
                 test_download_mode_gating.py, test_download_config.py, test_download_schemas.py,
                 test_ws_schema_artifact.py, test_downloads_integration.py
```

---

## THE CONTRACTS (authoritative — verbatim; implementers copy, only internals are free)

### CONTRACT 1 — Job & batch lifecycle state machine + crash recovery

`DownloadStatus` (Plan 5, unchanged): `queued | running | completed | failed | cancelled`. `completed` covers both a real download and a skip (disambiguated by `skip_reason`).

```
                         claim (pool)              outcome DOWNLOADED/SKIPPED
   POST /downloads ─▶ [queued] ───────────▶ [running] ─────────────────────────▶ [completed]
                         │                     │  outcome FAILED / unexpected exc
                         │                     ├────────────────────────────────▶ [failed]   (error_step set)
                         │  DELETE (pre-claim) │  DELETE while running → task.cancel()
                         ├───────────────▶ [cancelled] ◀──────────────────────────┤
                         │                     │  graceful shutdown drain-timeout / crash
                         └◀────────────────────┘  (running → queued : "recovered")
   terminal: completed | failed | cancelled  (no outgoing edge except row delete)
```

Transition rules (each is a single committed DB transaction):
- **create** → `queued` (`progress=0.0`, `started_at=NULL`, `batch_id`, `list_position` set).
- **claim** (`queued → running`): set `started_at=now`, `progress=0.0`. Guarded by the pool's `asyncio.Lock` (CONTRACT 2). A job whose status is no longer `queued` when popped (e.g. cancelled meanwhile) is **skipped** by the worker (no transition).
- **success** (`running → completed`): `finished_at=now`, `progress=1.0`, `output_path` from the outcome; `skip_reason=NULL` for `DOWNLOADED`, `skip_reason=<reason>.value` for `SKIPPED`.
- **failure** (`running → failed`): `finished_at=now`, `error_step = outcome.failed_step` (or `"unknown"`), `error_message = outcome.error` (truncated to the `Text` column). `progress` left at last value.
- **user cancel**:
  - `queued → cancelled` if not yet claimed (repository conditional `UPDATE ... WHERE status='queued'`); `finished_at=now`.
  - `running → cancelled`: pool calls `task.cancel()`; the `asyncio.CancelledError` propagates out of `engine.download` (it derives from `BaseException`, so the engine's `except Exception` does **not** swallow it — CONTRACT 2); the worker's handler sets `cancelled`, `finished_at=now`, best-effort deletes any partial output file.
- **graceful-shutdown re-queue** (`running → queued`): during `pool.shutdown()`, in-flight tasks that exceed the drain timeout are cancelled with the pool's `_shutting_down` flag set; the CancelledError handler distinguishes shutdown (→ `queued`, `started_at=NULL`, `progress=0.0`, `attempts += 1`, "recovered") from user cancel (→ `cancelled`). This is how jobs "survive restarts."
- **crash recovery** (`running → queued`, at startup, *before* workers spawn): `DownloadJobRepository.recover_orphaned() ⇒ UPDATE download_jobs SET status='queued', started_at=NULL, progress=0.0, attempts=attempts+1 WHERE status='running'` (single statement, single transaction). Returns the recovered ids; the pool then enqueues all `queued` ids. Justified by single-process ownership (see amendment note). **No stuck states:** every `running` row at boot is deterministically returned to `queued`; a cancelled-while-queued job never runs; a WS-client-gone never blocks a job (CONTRACT 3).
- **recovery integrity (pinned choice — MUST):** a job recovered/re-queued after a crash or drain-cancellation may have died mid-Convert/Embed, leaving a **converted-but-untagged or partial file at its planned output path**. File existence is therefore **never** trusted as a completion signal: with the batch's default `overwrite=SKIP`, a naive re-run would have the engine's `plan_skip` mark the suspect file `SKIPPED/ALREADY_EXISTS` — completed without embed or integrity. The rule: the worker builds the `DownloadRequest` for any job with `attempts > 0` using `overwrite=OverwriteMode.FORCE` (overriding the batch's overwrite), so the engine re-fetches, re-converts, and re-embeds over the suspect file. The alternative (delete `output_path` + temp artifacts before re-enqueue) was rejected because the job row does not know its planned output path until completion. Only recovered/re-queued jobs are forced; first attempts honour the batch's overwrite mode, so legitimate skips still work.
- **temp-dir sweep (companion to recovery integrity):** `pool.start()` step 1 also best-effort clears `settings.effective_temp_dir()` (the engine's exclusive scratch space in this single-process design) so crash-orphaned mid-fetch partial files don't accumulate. Failures to delete are logged and ignored — never fatal to startup.

**Batch finalization** is idempotent and derived, never a stuck state: a job reaching a terminal state triggers `DownloadBatchRepository.pending_count(batch_id)`; when it reaches 0 **and** `batches.finalized_at IS NULL`, the finalizer runs under the pool lock and sets `finalized_at=now` (so a concurrent last-two-jobs race finalizes exactly once).

### CONTRACT 2 — Worker pool

```python
# spotdl_server/downloads/worker.py
class DownloadWorkerPool:
    def __init__(
        self,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        engine: DownloadEngine,             # Plan 4; a FakeDownloadEngine in tests (the offline seam)
        hub: ProgressHub,
        settings: Settings,
        finalizer: BatchFinalizer,
        clock: Clock,
    ) -> None: ...

    async def start(self) -> None:
        """1) recover_orphaned() (running→queued, attempts+=1) + best-effort sweep of
        settings.effective_temp_dir() (crash-orphaned partial fetches; CONTRACT 1);
        2) re-enqueue every queued id (recovered + pre-existing);  3) spawn
        settings.download_concurrency worker tasks;  4) finalize any batch already
        fully-terminal but not finalized."""

    async def enqueue(self, job_ids: Sequence[UUID]) -> None:
        """Push ids onto the in-process asyncio.Queue so idle workers wake. Called by
        DownloadQueueService.submit after the job rows are committed."""

    async def request_cancel(self, job_id: UUID) -> bool:
        """Running: cancel the live asyncio.Task -> True. Queued: repo conditional
        cancel (queued→cancelled) -> True. Already terminal / unknown -> False."""

    async def shutdown(self, *, drain_timeout_s: float | None = None) -> None:
        """Set _shutting_down; stop accepting; wait up to drain_timeout for in-flight
        jobs to finish naturally; cancel any still running (their handler re-queues
        them). Await all worker tasks. Idempotent."""
```

- **Concurrency** = `settings.download_concurrency` (default 2). Workers consume job ids from a single `asyncio.Queue[UUID]`; the hand-off is FIFO. Backpressure is bounded only by DB rows (the queue holds ids, not payloads).
- **Claim safety (single-process boundary — documented):** claiming (`queued → running`) happens under one shared `asyncio.Lock` held only for the DB status transition, so two workers never claim the same row. This is correct **because exactly one process owns the queue**. Cross-process claiming (multiple containers sharing one Postgres) is a **non-goal** for v1; the honest multi-process path would be `SELECT ... FOR UPDATE SKIP LOCKED` — noted in a code comment, not implemented. A test asserts two concurrent workers never double-run one job.
- **Cancellation seam (honest):** the pool holds `self._running: dict[UUID, asyncio.Task]`. Cancel = `task.cancel()`. Because Plan 4's engine offloads each blocking step via `asyncio.to_thread` and `await`s it, cancellation is delivered **at the `await` boundary between steps** — the currently-executing blocking step (yt-dlp fetch or ffmpeg convert) **runs to completion in its worker thread first** (a thread cannot be force-killed), then `CancelledError` raises when the engine tries to await the next step. `CancelledError` is a `BaseException`, so the engine's `except Exception` does not convert it to a `FAILED` outcome — it propagates cleanly to the worker. This bounds cancellation latency to at most one step's duration; documented as the deliberate v1 granularity. (No Plan 4 change: the engine needs no cancel token — asyncio cancellation *is* the "check between steps" mechanism.)
- **Graceful shutdown draining:** `shutdown()` waits for in-flight jobs up to `settings.download_drain_timeout_s` (default 30); jobs finishing within the window reach their natural terminal state; jobs exceeding it are cancelled with `_shutting_down=True` and re-queued (`running → queued`) so the next boot resumes them.
- **Progress plumbing + throttle (CONTRACT 5):** each `_run_job` builds an `on_progress` callback that stores the latest `ProgressEvent` in a per-job holder (assignment is GIL-safe; `on_progress` runs in the engine's worker thread). A per-job **pump** coroutine flushes at most every `settings.progress_throttle_ms` (default 500 ms): it persists `progress` (overall 0..1 via CONTRACT 5) to the job row **and** broadcasts a `progress` WS message — but only when the held event differs from the last flush (phase change or overall Δ ≥ 0.01). Phase-transition and terminal events are always flushed. The pump is cancelled and a final flush performed when the job ends.

### CONTRACT 3 — WebSocket protocol (`WS /ws/progress`, single fan-out)

One endpoint fans out **all** job events to every connected client (no per-client `Downloader` like v4; clients filter by `batch_id`/`job_id` themselves). Messages are Pydantic models serialized with `model_dump_json()`, discriminated on `type`:

```python
# spotdl_server/api/schemas.py  (all frozen; type is a Literal)
WS_PROTOCOL_VERSION = 1

class WsHello(BaseModel):
    """First frame sent to every client immediately after accept — the protocol
    version envelope. Clients reject a version they don't support."""
    type: Literal["hello"] = "hello"
    protocol_version: int = WS_PROTOCOL_VERSION

class WsJobQueued(BaseModel):
    type: Literal["job_queued"] = "job_queued"
    job_id: UUID; batch_id: UUID | None
    track_name: str | None; list_position: int | None; list_length: int | None

class WsJobStarted(BaseModel):
    type: Literal["job_started"] = "job_started"
    job_id: UUID; batch_id: UUID | None

class WsProgress(BaseModel):
    type: Literal["progress"] = "progress"
    job_id: UUID; batch_id: UUID | None
    phase: str          # ProgressPhase value ("fetch"|"convert"|"embed"|"post"|...)
    percent: int | None # 0-100 within the phase, when known
    overall: float      # 0.0-1.0 whole-job progress (CONTRACT 5)

class WsJobFinished(BaseModel):
    type: Literal["job_finished"] = "job_finished"
    job_id: UUID; batch_id: UUID | None
    status: Literal["completed"]
    skipped: bool; skip_reason: str | None
    output_path: str | None

class WsJobFailed(BaseModel):
    type: Literal["job_failed"] = "job_failed"
    job_id: UUID; batch_id: UUID | None
    step: str | None; error: str | None

class WsJobCancelled(BaseModel):
    type: Literal["job_cancelled"] = "job_cancelled"
    job_id: UUID; batch_id: UUID | None

class WsBatchFinished(BaseModel):
    type: Literal["batch_finished"] = "batch_finished"
    batch_id: UUID
    completed: int; failed: int; skipped: int; cancelled: int
    m3u_paths: list[str]; save_file_path: str | None

WsMessage = Annotated[
    WsHello | WsJobQueued | WsJobStarted | WsProgress | WsJobFinished
    | WsJobFailed | WsJobCancelled | WsBatchFinished,
    Field(discriminator="type"),
]
```

- **Server→client only** (progress). The server ignores inbound frames except responding to WS ping/close. On connect the server sends `WsHello` first (the version envelope), then a `job_queued`/`progress` snapshot of currently non-terminal jobs (best-effort; pinned in v1 → send snapshot).
- **Client-gone safety:** `ProgressHub.broadcast` iterates a copy of the client set; any send that raises (`WebSocketDisconnect`/`RuntimeError`) removes that client and continues — a dead client never blocks a broadcast or a job.
- **Emission points:** `hello` once per connection at accept; `job_queued` at submit/enqueue; `job_started` on claim; `progress` from the throttle pump; `job_finished`/`job_failed`/`job_cancelled` on terminal transition; `batch_finished` after the finalizer runs.
- **Machine-readable artifact (CONTRACT — Plan 8 codegen input):** because FastAPI's OpenAPI export does not describe WS routes, the `WsMessage` union is exported as a committed JSON Schema build artifact, mirroring the `openapi.json` pattern: `apps/server/scripts/export_ws_schema.py` dumps `TypeAdapter(WsMessage).json_schema()` (wrapped as `{"ws_protocol_version": WS_PROTOCOL_VERSION, "message": <schema>}`) with `json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False) + "\n"` to `apps/server/ws-protocol.json`; a `make ws-schema` target regenerates it and an in-sync test (Task 2) fails on drift. Plan 8's TS/Python clients generate their WS message types from this file.

### CONTRACT 4 — Download API request/response schemas

```python
# spotdl_server/api/schemas.py
class DownloadSubmitRequest(BaseModel):
    query: str                              # URL, provider:type:id, or free text (single track);
                                            #   album/playlist URL is expanded server-side to N jobs
    output_format: OutputFormat | None = None   # None -> settings.default_output_format
    bitrate: str | None = None                   # None -> settings.default_bitrate
    output_template: str | None = None           # None -> settings.default_output_template
    overwrite: OverwriteMode | None = None        # None -> OverwriteMode.SKIP
    embed_lyrics: bool = True
    generate_lrc: bool = False
    sponsor_block: bool = False
    generate_m3u: bool = False
    m3u_template: str | None = None               # {list}/{list[0]} supported (Plan 4 post)
    generate_save_file: bool = False
    update_archive: bool = False

class DownloadJobOut(BaseModel):
    id: UUID; batch_id: UUID | None
    status: DownloadStatus
    track_id: UUID | None; track_name: str | None; artists: list[str]
    output_format: str | None; bitrate: str | None; output_template: str | None
    output_path: str | None
    progress: float                          # 0.0-1.0
    skip_reason: str | None
    error_step: str | None; error_message: str | None
    list_position: int | None
    created_at: datetime; started_at: datetime | None; finished_at: datetime | None

class DownloadBatchOut(BaseModel):
    batch_id: UUID; kind: BatchKind; name: str | None
    total_jobs: int
    counts: dict[str, int]                   # {"queued":n,"running":n,"completed":n,"failed":n,"cancelled":n}
    finalized: bool
    jobs: list[DownloadJobOut]

class DownloadSubmitResponse(BaseModel):     # returned by POST /downloads
    batch: DownloadBatchOut

class DownloadListResponse(BaseModel):       # returned by GET /downloads
    jobs: list[DownloadJobOut]
    total: int; limit: int; offset: int
```

**Endpoints (all under `/api/v1`, mounted only in selfhost/embedded):**

| Method & path | Body / query | Response | Notes |
|---|---|---|---|
| `POST /downloads` | `DownloadSubmitRequest` | `DownloadSubmitResponse` (201) | resolve+expand → batch of N jobs; enqueue; broadcast `job_queued` |
| `GET /downloads` | `?status=&batch_id=&limit=50&offset=0` | `DownloadListResponse` | filter by status/batch; newest-first; pagination |
| `GET /downloads/{job_id}` † | — | `DownloadJobOut` | 404 `not_found` if unknown |
| `DELETE /downloads/{job_id}` | — | `DownloadJobOut` (200) | cancel queued or running; 409 `download_failed`(detail `{"reason":"already_terminal"}`) if terminal |
| `GET /downloads/{job_id}/file` | — | file stream | CONTRACT 6; only `completed` non-skip jobs |
| `GET /downloads/batches/{batch_id}` † | — | `DownloadBatchOut` | 404 if unknown |
| `GET /downloads/batches/{batch_id}/save-file` † | — | `.spotdl` v2 JSON | CONTRACT 7; `application/json` + `Content-Disposition` attachment |

> **† Deliberate additions beyond spec §6.2's literal list** (which names only `POST/GET /downloads`, `DELETE /downloads/{id}`, `GET /downloads/{id}/file`, `WS /ws/progress`). Scope-note justification, pinned here so reviewers don't read them as scope creep: `GET /downloads/{job_id}` is the polling fallback for clients without a WS connection (CLI one-shots, curl) and the refresh target after `DELETE`; `GET /downloads/batches/{batch_id}` is the batch-status read the web/TUI queue page needs (spec §8 "downloads queue" is batch-oriented); `GET /downloads/batches/{batch_id}/save-file` is the pinned emission endpoint for the `.spotdl` v2 artifact that Plan 8's `spotdl sync`/`spotdl save` consume (the spec's `spotdl save <url> [--save-file]` requires the server to hand this file to the client). All three are read-only, mode-gated identically to the rest of the surface, and covered by the OpenAPI artifact.

**Error-code addition (extends Plan 5's `ErrorCode` — additive, API-level only, not a DB enum):** append `UNSUPPORTED_ENTITY = "unsupported_entity"` to `api/errors.py`'s `ErrorCode`, raised via a new `services/errors.py` exception `UnsupportedBatchEntity(entity_type)` → **400** with detail `{"entity_type": "<value>"}`. Used when a resolvable entity kind cannot be batch-downloaded (v1: `artist`). This is deliberately distinct from `unsupported_url` (which means "the input could not be parsed at all") — the URL here parses fine; the *entity kind* is unsupported.

### CONTRACT 5 — Whole-job progress mapping

```python
# spotdl_server/downloads/progress.py
PHASE_WEIGHTS: dict[ProgressPhase, tuple[float, float]] = {
    ProgressPhase.PLAN:    (0.00, 0.05),
    ProgressPhase.FETCH:   (0.05, 0.60),
    ProgressPhase.CONVERT: (0.60, 0.85),
    ProgressPhase.EMBED:   (0.85, 0.95),
    ProgressPhase.POST:    (0.95, 1.00),
    ProgressPhase.DONE:    (1.00, 1.00),
    ProgressPhase.SKIPPED: (1.00, 1.00),
    ProgressPhase.ERROR:   (0.00, 0.00),   # progress left as-is on error
}

def overall_progress(phase: ProgressPhase, percent: int | None) -> float:
    """Map a phase + in-phase percent to a monotonic 0.0-1.0 whole-job value.
    lo + (hi-lo) * (percent or 0)/100 ; clamped to [0,1]; DONE/SKIPPED -> 1.0."""
```

### CONTRACT 6 — File delivery semantics

`GET /downloads/{job_id}/file`:
1. Load the job; **404 `not_found`** if unknown.
2. **409 `download_failed`** (detail `{"reason": "not_ready"}`) unless `status == completed` and `skip_reason is None` and `output_path` is set. (A skipped job has no freshly-produced file to claim ownership of via this endpoint → treated as not-ready in v1.)
3. **Path-traversal safety (mandatory):** `resolved = Path(output_path).resolve()`; the configured library root `root = settings.effective_library_path().resolve()`; **403 `downloads_disabled`**-family is wrong here — return **404 `not_found`** if `not resolved.is_relative_to(root)` or `not resolved.is_file()` (never leak whether an out-of-root path exists). The stored `output_path` is always produced under `config.output_dir == root`, so a mismatch means tampering or a moved file.
4. Delivery: default = Starlette `FileResponse(resolved, filename=resolved.name, media_type=<by suffix>)` with `Content-Disposition: attachment; filename*=UTF-8''<url-encoded name>`. If `settings.download_x_accel_prefix` is set (nginx/Caddy internal redirect), instead return an empty `Response` with header `X-Accel-Redirect: <prefix>/<path-relative-to-root>` + the same `Content-Disposition` (streaming delegated to the reverse proxy; the file is never read by Python). Media type resolved from a small suffix map (`.mp3→audio/mpeg`, `.m4a→audio/mp4`, `.flac→audio/flac`, `.ogg→audio/ogg`, `.opus→audio/opus`, `.wav→audio/wav`, else `application/octet-stream`).

### CONTRACT 7 — `.spotdl` v2 save-file (consumed by Plan 8 `spotdl sync`)

A **versioned JSON object** (v4's `.spotdl` was a bare array of `Song.asdict`; v5 wraps it so the format is self-describing and Plan 8 can auto-migrate v4). One entry per job in the batch (all jobs, including failed — mirrors v4 which serialized every result). Emitted both as the `GET .../save-file` response and, when `generate_save_file`, written to `save_file_path`.

```python
# spotdl_server/downloads/savefile.py
SAVE_FILE_VERSION = 2

class SaveFileMatch(BaseModel):        # the chosen audio target (from matches row / DownloadRequest.candidate)
    provider: str                     # ProviderId value
    provider_id: str
    url: str                          # playable target url (candidate.url / matches.target_url)
    name: str | None = None
    artists: list[str] = []
    duration_ms: int | None = None
    isrc: str | None = None
    verified: bool = False
    score: float | None = None
    matcher_version: str | None = None

class SaveFileDownload(BaseModel):     # what the queue decided/produced
    output_format: str
    bitrate: str
    output_template: str
    output_path: str | None = None
    status: str                        # DownloadStatus value: completed|failed|cancelled|queued|running
    skip_reason: str | None = None
    error_step: str | None = None

class SaveFileSong(BaseModel):         # full track metadata (v5 Track + list context)
    name: str
    artists: list[str]
    artist: str | None = None          # main artist
    album_name: str | None = None
    album_artist: str | None = None
    duration_ms: int
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    disc_count: int | None = None
    track_count: int | None = None
    year: int | None = None
    date: str | None = None
    genres: list[str] = []
    publisher: str | None = None
    copyright_text: str | None = None
    popularity: int | None = None
    cover_url: str | None = None
    track_url: str | None = None       # canonical entity url (WOAS)
    provider: str | None = None        # source metadata provider
    provider_id: str | None = None
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None
    match: SaveFileMatch | None = None
    download: SaveFileDownload

class SaveFileV2(BaseModel):
    version: int = SAVE_FILE_VERSION   # == 2
    kind: str                          # BatchKind value
    name: str | None = None            # playlist/album name
    source: str | None = None          # submitted url/query
    created_at: str                    # ISO 8601 (batch.created_at)
    matcher_version: str | None = None
    songs: list[SaveFileSong]

def build_save_file(batch, jobs, tracks_by_id, matches_by_id) -> SaveFileV2: ...
def dump_save_file(model: SaveFileV2) -> str:   # json.dumps(model.model_dump(), indent=2, ensure_ascii=False) + "\n"
```

Completeness for Plan 8 sync: each song carries the full track metadata + the chosen `match` (audio target) + the `download` settings/result. `spotdl sync <file>` can re-resolve/re-match (or reuse `match`) and re-download missing tracks, prune removed ones, and regenerate m3u — exactly v4 sync semantics, now versioned. **Known limitation (documented):** Plan 5's canonical `tracks` table does not persist every optional tag field (`date`, `publisher`, `copyright_text`, `cover_url` are on the Plan 4 `Track` model but not columns), so those serialize as `null` when the song is reconstructed from the DB. This is additive-safe (all optional) and out of scope to widen here.

---

## Tasks

### Task 1: Settings, `DownloadConfig` builder, `/config` download surface, schema-amendment guard

**Files:**
- Modify: `apps/server/src/spotdl_server/settings.py`
- Modify: `apps/server/src/spotdl_server/api/schemas.py` (extend `ConfigResponse`), `api/routers/meta.py` (already serves `/config`)
- Create: `apps/server/tests/api/test_download_config.py`, `apps/server/tests/db/test_download_schema_guard.py`
- Modify: `apps/server/tests/conftest.py` (add a `download_settings` fixture)

**Contract vs freedom:** the settings **names/defaults** and the `/config` `download_defaults` shape are CONTRACT (web/TUI read them, Plan 8 clients generate against them). Helper internals are free.

- [ ] **Step 1 — RED: `test_download_schema_guard.py`.** Build all tables into in-memory SQLite (`create_all`) and assert the Plan-5 amendments landed (fails loudly if not): `download_batches` in `Base.metadata.tables`; `download_jobs` has columns `batch_id` (FK→`download_batches.id`, nullable, ondelete CASCADE), `list_position` (Integer, nullable), `skip_reason` (String, nullable), `attempts` (Integer, NOT NULL, default 0); `BatchKind` importable from `db.enums` and its column is non-native VARCHAR. This is the machine-check that the amendment note was honoured before any queue code is written.

- [ ] **Step 2 — RED: `test_download_config.py`.** `Settings(mode=SELFHOST)` exposes download defaults; `effective_library_path()` under a tmp `data_dir` resolves inside it; `download_config()` returns a `spotdl_core.download.DownloadConfig` with `output_dir==effective_library_path()`, `temp_dir==download_temp_dir`, `ffmpeg_path`, tokenized `ytdlp_args`/`ffmpeg_args` (via `shlex.split`). **Engine-knob guard (the Plan-8 amendment check — fails loudly if any is missing):** `test_engine_knob_settings_present` asserts all eleven `download_*` engine/session fields exist with the exact v4-parity defaults (`download_restrict is RestrictMode.NONE`, `download_max_filename_length is None`, `download_id3_separator == "/"`, `download_detect_formats == ()`, and the seven booleans `False`). `/config` in SELFHOST includes `download_defaults{output_format, bitrate, output_template, concurrency, restrict, max_filename_length, id3_separator, detect_formats, skip_explicit, respect_skip_file, create_skip_file, playlist_numbering, retain_track_cover, add_unavailable, scan_existing}` and `features.downloads is True`; in HOSTED `features.downloads is False` and `download_defaults is None`.

- [ ] **Step 3 — Implement settings.** Add (env-prefixed `SPOTDL_`):
```python
download_concurrency: int = 2
library_path: Path | None = None                 # None -> data_dir / "music"
download_temp_dir: Path | None = None             # None -> data_dir / "temp"
default_output_format: OutputFormat = OutputFormat.MP3
default_bitrate: str = "auto"
default_output_template: str = "{artists} - {title}.{output-ext}"
ffmpeg_path: str = "ffmpeg"
download_cookie_file: Path | None = None
download_proxy: str | None = None
ytdlp_args: str = ""                              # shlex-tokenized into DownloadConfig.ytdlp_args
ffmpeg_args: str = ""
downloads_require_auth: bool = False              # selfhost: gate downloads behind require_user;
                                                  #   only meaningful when settings.auth_active() (Plan 6)
progress_throttle_ms: int = 500
download_drain_timeout_s: float = 30.0
download_x_accel_prefix: str | None = None
ws_progress_require_auth: bool | None = None      # None -> derive: same as downloads_require_auth

# --- engine/session knobs (Plan-8 required amendment, folded in here): the
# remaining Plan 4 DownloadRequest options that are server-wide configuration,
# not per-request API fields. The CLI's embedded server (Plan 8) sets these per
# invocation; a persistent selfhost server treats them as operator defaults —
# consistent with ffmpeg_path/cookie_file/proxy already living in Settings.
# Names/types/defaults match Plan 4's DownloadRequest fields (v4 parity).
download_restrict: RestrictMode = RestrictMode.NONE   # -> DownloadRequest.restrict
download_max_filename_length: int | None = None       # -> DownloadRequest.max_filename_length
download_id3_separator: str = "/"                     # -> DownloadRequest.id3_separator
download_detect_formats: tuple[str, ...] = ()         # -> DownloadRequest.detect_formats (OutputFormat values)
download_skip_explicit: bool = False                  # -> DownloadRequest.skip_explicit
download_respect_skip_file: bool = False              # -> DownloadRequest.respect_skip_file
download_create_skip_file: bool = False               # -> DownloadRequest.create_skip_file
download_playlist_numbering: bool = False             # playlist batches: track_number := list_position,
                                                      #   album name := playlist name (v4 parity; applied
                                                      #   at worker request-build, Task 6)
download_retain_track_cover: bool = False             # -> DownloadRequest.retain_track_cover
download_add_unavailable: bool = False                # -> BatchFinalizer archive_update(add_unavailable=...)
download_scan_existing: bool = False                  # scan effective_library_path() -> DownloadRequest.known_paths
```
Helpers (methods): `effective_library_path() -> Path`, `effective_temp_dir() -> Path`, `downloads_enabled() -> bool` (`mode is not HOSTED`), `download_config() -> DownloadConfig` (imports `spotdl_core.download`; `mkdir(parents=True, exist_ok=True)` both dirs), and `require_download_auth_consistency() -> None` — **startup fail-fast, mirrors Plan 6's `require_auth_secret()`**: raise `RuntimeError("downloads_require_auth=True but auth is inactive (set SPOTDL_AUTH_ENABLED=true and an auth secret)")` when `downloads_enabled() and downloads_require_auth and not self.auth_active()`. **The auth gate keys on Plan 6's derived `settings.auth_active()`** (`auth_enabled: bool | None`, `None` → derived from mode, `False` in embedded) — never on raw `auth_enabled`, whose `None` default would make `downloads_require_auth` silently no-op in selfhost. Called from `create_app` (Task 8). Extend `ConfigResponse` with `download_defaults: DownloadDefaults | None` (new schema, CONTRACT — clients read the server's effective download configuration):
```python
class DownloadDefaults(BaseModel):
    output_format: str; bitrate: str; output_template: str; concurrency: int
    # engine/session knobs (Plan-8 amendment) — read-only visibility for clients
    restrict: str                       # RestrictMode value
    max_filename_length: int | None
    id3_separator: str
    detect_formats: list[str]
    skip_explicit: bool
    respect_skip_file: bool
    create_skip_file: bool
    playlist_numbering: bool
    retain_track_cover: bool
    add_unavailable: bool
    scan_existing: bool
```
populated when `downloads_enabled()` else `None`. `meta.py` maps it. Add a test: `Settings(mode=SELFHOST, downloads_require_auth=True, auth_enabled=False).require_download_auth_consistency()` raises; with `auth_enabled=True` (+ secret) it passes.

- [ ] **Step 4 — GREEN + gates.** `make check` green.
- [ ] **Step 5 — Commit:** `feat(server): download settings, DownloadConfig builder, /config download defaults + schema guard`.

---

### Task 2: API schemas (download request/response + WS messages) + `.spotdl` v2 model

**Files:**
- Modify: `apps/server/src/spotdl_server/api/schemas.py`
- Create: `apps/server/src/spotdl_server/downloads/__init__.py`, `downloads/savefile.py`
- Create: `apps/server/scripts/export_ws_schema.py`, `apps/server/ws-protocol.json` (committed artifact)
- Modify: root `Makefile` (add `ws-schema` target, add to `.PHONY`)
- Create: `apps/server/tests/api/test_download_schemas.py`, `apps/server/tests/api/test_ws_schema_artifact.py`, `apps/server/tests/downloads/__init__.py`, `apps/server/tests/downloads/test_savefile.py`

**Contract vs freedom:** every field in CONTRACT 3, 4, and 7 is fixed (OpenAPI + Plan 8 depend on it). This task defines models + the committed WS-schema artifact — no routers, no runtime I/O.

- [ ] **Step 1 — RED.** `test_download_schemas.py`: `DownloadSubmitRequest` defaults (`overwrite=None`, `embed_lyrics=True`, …) round-trip; the `WsMessage` discriminated union parses each `type` (including `"hello"`) to the right class and rejects an unknown `type`; `WsHello().protocol_version == WS_PROTOCOL_VERSION == 1`; `DownloadJobOut`/`DownloadBatchOut` serialize `status` as the `DownloadStatus` value. `test_savefile.py`: `SaveFileV2(version=2, ...)` round-trips `model_dump_json`; `dump_save_file` output is deterministic (sorted-free but stable indent, trailing newline) and re-parses to an equal model; a `SaveFileSong` with only required fields validates (all optional default sensibly). `test_ws_schema_artifact.py`: `test_ws_schema_in_sync` — regenerate the schema in-memory and byte-compare to the committed `ws-protocol.json` (fail message: "run `make ws-schema`"); `test_ws_schema_contains_all_message_types` — every `type` literal (`hello`, `job_queued`, `job_started`, `progress`, `job_finished`, `job_failed`, `job_cancelled`, `batch_finished`) appears in the artifact, and the top-level `ws_protocol_version` equals `WS_PROTOCOL_VERSION`.

- [ ] **Step 2 — Implement.** Add CONTRACT 3 WS models (incl. `WsHello` + `WS_PROTOCOL_VERSION`) + `WsMessage`, CONTRACT 4 request/response models, `DownloadDefaults` (Task 1), and CONTRACT 7 `savefile.py` models + `build_save_file` (pure mapper — signature only here; body may stay minimal, exercised fully in Task 7) + `dump_save_file`. Reuse `OutputFormat`/`OverwriteMode` from `spotdl_core.download` and `DownloadStatus`/`BatchKind` from `db.enums` (schemas may import enums — they are value types, not ORM). Implement `scripts/export_ws_schema.py` per CONTRACT 3's artifact rule (`TypeAdapter(WsMessage).json_schema()`, deterministic dump, optional `--check` flag mirroring `export_openapi.py`); add the Makefile target:
```make
ws-schema:
	uv run python apps/server/scripts/export_ws_schema.py
```
Run `make ws-schema` and commit `ws-protocol.json`.

- [ ] **Step 3 — GREEN + gates.** `make check` green (mypy strict; discriminated union typed with `Annotated[... , Field(discriminator="type")]`; the in-sync test passes because the artifact was just generated).
- [ ] **Step 4 — Commit:** `feat(server): download API + WS message schemas, .spotdl v2 model, ws-protocol.json artifact`.

---

### Task 3: Repositories — `DownloadJobRepository` + `DownloadBatchRepository`

**Files:**
- Create: `apps/server/src/spotdl_server/repositories/downloads.py`, `repositories/batches.py`
- Create: `apps/server/tests/repositories/test_downloads_repo.py`, `tests/repositories/test_batches_repo.py`

**Contract vs freedom:** class names + public signatures are CONTRACT (services + pool depend on them). All take `AsyncSession` in `__init__`, take/return ORM models or plain values, never Pydantic/HTTP types, never commit (caller owns the unit of work) — **except** the claim/cancel/recover methods, which are atomic status transitions the caller commits immediately.

**`DownloadJobRepository` (CONTRACT):**
```python
class DownloadJobRepository:
    def __init__(self, session: AsyncSession) -> None: ...
    async def create(self, *, batch_id, track_id, match_id, output_format, bitrate,
                     output_template, list_position, requested_by) -> DownloadJob: ...   # status=queued
    async def get(self, job_id: UUID) -> DownloadJob | None: ...
    async def list(self, *, status: DownloadStatus | None = None, batch_id: UUID | None = None,
                   limit: int = 50, offset: int = 0) -> tuple[list[DownloadJob], int]: ...  # (page, total), created_at desc
    async def claim(self, job_id: UUID, *, now: datetime) -> DownloadJob | None: ...
        # conditional UPDATE ... SET status='running', started_at=now WHERE id=:id AND status='queued';
        # returns the row iff it transitioned (None if it was cancelled/gone) — the caller holds the pool lock.
    async def mark_completed(self, job_id, *, output_path, skip_reason, now) -> None: ...
    async def mark_failed(self, job_id, *, error_step, error_message, now) -> None: ...
    async def mark_cancelled(self, job_id, *, now) -> None: ...
    async def requeue(self, job_id, *, now) -> None: ...            # running->queued, started_at=NULL, progress=0.0, attempts+=1
    async def cancel_if_queued(self, job_id, *, now) -> bool: ...   # conditional UPDATE WHERE status='queued'
    async def update_progress(self, job_id, *, progress: float) -> None: ...  # throttled writes (CONTRACT 5)
    async def recover_orphaned(self, *, now) -> list[UUID]: ...     # UPDATE ... status='queued', attempts=attempts+1 WHERE status='running'
    async def ids_by_status(self, status: DownloadStatus) -> list[UUID]: ...   # for start() re-enqueue
```

**`DownloadBatchRepository` (CONTRACT):**
```python
class DownloadBatchRepository:
    def __init__(self, session: AsyncSession) -> None: ...
    async def create(self, *, kind, source, name, output_format, bitrate, output_template,
                     generate_m3u, m3u_template, generate_save_file, save_file_path,
                     update_archive, embed_lyrics, generate_lrc, sponsor_block,
                     total_jobs, requested_by) -> DownloadBatch: ...
    async def get(self, batch_id: UUID) -> DownloadBatch | None: ...
    async def jobs(self, batch_id: UUID) -> list[DownloadJob]: ...
    async def counts(self, batch_id: UUID) -> dict[str, int]: ...        # per-status tally
    async def pending_count(self, batch_id: UUID) -> int: ...            # queued+running
    async def mark_finalized(self, batch_id: UUID, *, now) -> bool: ...  # conditional WHERE finalized_at IS NULL -> True once
```

**Tests (offline, in-memory SQLite):** create/list/filter/paginate (total independent of limit; status+batch filters); `claim` transitions once and returns `None` on a second claim or when the row was cancelled first (the no-double-run guard); `cancel_if_queued` False on a running row; `recover_orphaned` flips only `running` rows, increments `attempts`, and returns their ids; `requeue` increments `attempts`; `mark_completed` sets `skip_reason` for a skip and `output_path`; `mark_failed` truncates a very long `error_message`; batch `counts`/`pending_count` correct across mixed statuses; `mark_finalized` returns `True` exactly once (idempotent race guard).

- [ ] **Step 4 — GREEN + gates.** `make check` green. **Commit:** `feat(server): download job + batch repositories (claim/recover/finalize semantics)`.

---

### Task 4: `DownloadQueueService` — submit (resolve + expand), list, get, cancel

**Files:**
- Create: `apps/server/src/spotdl_server/services/downloads.py`
- Create: `apps/server/tests/services/test_download_queue_service.py`

**Contract vs freedom:** `DownloadQueueService.__init__` collaborators and method signatures are CONTRACT (routers + pool depend on them). No FastAPI/ORM types cross the boundary — inputs are plain values / the `DownloadSubmitRequest` schema is acceptable as a value object; outputs are `DownloadBatchOut`/`DownloadJobOut` DTOs (the same Pydantic models the router returns — they carry no ORM/HTTP coupling).

**`DownloadQueueService` (CONTRACT):**
```python
class DownloadQueueService:
    def __init__(self, *, session: AsyncSession, resolve_service: ResolveService,
                 entity_service: EntityService, match_repo: MatchRepository,
                 track_repo: TrackRepository, job_repo: DownloadJobRepository,
                 batch_repo: DownloadBatchRepository, settings: Settings,
                 requested_by: UUID | None, clock: Clock) -> None: ...

    async def submit(self, req: DownloadSubmitRequest) -> tuple[DownloadBatchOut, list[UUID]]: ...
        # returns (batch DTO, ordered job ids) — the router hands the ids to the pool.enqueue.
    async def list_jobs(self, *, status=None, batch_id=None, limit=50, offset=0) -> DownloadListResponse: ...
    async def get_job(self, job_id: UUID) -> DownloadJobOut: ...           # NotFoundError if absent
    async def get_batch(self, batch_id: UUID) -> DownloadBatchOut: ...     # NotFoundError if absent
```

**`submit` algorithm:**
1. **Resolve** `req.query` via `ResolveService.resolve(query)` (Plan 5 — cache-first; handles URL / `provider:type:id` / free text). The `ResolveResult` carries the entity type.
2. **Expand** by entity kind → an ordered list of `(track, match)` pairs and a `BatchKind`:
   - **track** → `BatchKind.SINGLE`, one pair; the chosen match = the top row from `MatchRepository.list_for_track(track_id)` (community-verified first, else best score); **no viable match → 404-style `NoMatchFound`** surfaced by the router. `name = None`.
   - **album** → `BatchKind.ALBUM`; tracks from the resolved album (already persisted by resolve); each track's top match; `name = album.name`. Tracks lacking any match are still created as jobs that will fail fast with `no_match` (visible, not silently dropped — spec §10).
   - **playlist** → `BatchKind.PLAYLIST`; ordered playlist tracks; `name = playlist.name`.
   - **artist** → artist bulk-download is out of scope for v1 → raise `UnsupportedBatchEntity(EntityType.ARTIST)` → **400 `unsupported_entity`** detail `{"entity_type": "artist"}` (the new error code pinned under CONTRACT 4 — deliberately not `unsupported_url`, since the URL parsed fine).
3. **Create the batch** (`DownloadBatchRepository.create`) with resolved defaults (`output_format = req.output_format or settings.default_output_format`, etc.), `total_jobs = len(pairs)`, `requested_by`.
4. **Create N jobs** (`DownloadJobRepository.create`) with `list_position = i+1`, `track_id`, `match_id`.
5. **Commit** the unit of work once. Return the `DownloadBatchOut` + the job-id list (creation order). The router (Task 9) calls `pool.enqueue(ids)` and broadcasts `job_queued` **after** the commit succeeds.

Matching is **not** re-kicked here — resolve already persisted matches (Plan 5 kicks matching for tracks; album/playlist matching is this queue's concern only insofar as it reads existing match rows; if an album track has no match row, the job carries `match_id=None` and the worker fails it with `error_step="fetch"`/`no_match`). Document this: bulk per-track matching for albums/playlists piggybacks on whatever resolve persisted; a follow-up could pre-match, but v1 relies on resolve + per-job fail-visible.

**Tests (offline, in-memory DB + a fake `ResolveService`/`EntityService` seam or a real one over fakes):** submit a track url → 1 job, batch `SINGLE`, defaults applied; submit an album → N ordered jobs with `list_position` 1..N, `name` set; a track with no match → job created with `match_id=None` (not dropped); `list_jobs` filters/paginates; `get_job`/`get_batch` raise `NotFoundError` when absent; overrides (`output_format`, `bitrate`, `output_template`) flow to the batch/jobs.

- [ ] **Step 4 — GREEN + gates.** `make check` green. **Commit:** `feat(server): DownloadQueueService — submit/expand/list/cancel orchestration`.

---

### Task 5: Progress hub (WS fan-out) + `overall_progress` + throttle

**Files:**
- Create: `apps/server/src/spotdl_server/api/progress_hub.py`, `apps/server/src/spotdl_server/downloads/progress.py`
- Create: `apps/server/tests/downloads/test_progress.py`, `apps/server/tests/api/test_progress_hub.py`

**Contract vs freedom:** `ProgressHub` public methods, `overall_progress`, and `PHASE_WEIGHTS` are CONTRACT (worker + WS router depend on them). `ProgressThrottle` internals are free.

**`downloads/progress.py` (CONTRACT):** `PHASE_WEIGHTS` + `overall_progress` exactly per CONTRACT 5, plus:
```python
class ProgressThrottle:
    def __init__(self, *, min_interval_ms: int, min_delta: float = 0.01) -> None: ...
    def should_flush(self, *, now: float, phase: ProgressPhase, overall: float,
                     is_terminal: bool) -> bool: ...
        # True if terminal, or phase changed since last flush, or (now - last >= interval
        # and overall - last_overall >= min_delta). Records the decision on True.
```

**`api/progress_hub.py` (CONTRACT):**
```python
class ProgressHub:
    def __init__(self) -> None: ...                     # self._clients: set[WebSocket]
    async def register(self, ws: WebSocket) -> None: ...   # accept + add
    def unregister(self, ws: WebSocket) -> None: ...
    async def broadcast(self, message: WsMessage) -> None: ...
        # payload = message.model_dump_json(); iterate a *copy* of clients; on send
        # error remove that client and continue (client-gone safety, CONTRACT 3).
    async def snapshot_to(self, ws: WebSocket, messages: Iterable[WsMessage]) -> None: ...
```
`ProgressHub` imports `fastapi.WebSocket`, so it lives in `api/` (it is HTTP-glue, not a service) — the worker receives it as an injected collaborator typed by this class (no layering violation: the worker is in `downloads/`, importing a concrete hub class from `api/` — to keep the layering contract clean, the worker depends on a tiny `Broadcaster` Protocol defined in `downloads/worker.py` that `ProgressHub` structurally satisfies, so `downloads/` never imports `api/`). **Document this Protocol seam.**

**Tests (offline):** `overall_progress` table (fetch@50→0.325; convert@0→0.60; done→1.0; error keeps 0.0/clamp); `ProgressThrottle` flushes on terminal + phase change + interval-with-delta, suppresses rapid sub-delta ticks. `ProgressHub`: register two fake `WebSocket`s (async stubs recording `send_text`), broadcast → both receive the JSON; one stub raising on send → it is removed and the other still receives; `snapshot_to` sends the given messages to one client only.

- [ ] **Step 4 — GREEN + gates.** `make check` green. **Commit:** `feat(server): progress hub fan-out + whole-job progress mapping + throttle`.

---

### Task 6: `DownloadWorkerPool` — asyncio pool, state machine, cancellation, drain, crash recovery

**Files:**
- Create: `apps/server/src/spotdl_server/downloads/worker.py`
- Modify: `apps/server/tests/conftest.py` (add `FakeDownloadEngine` + pool fixture)
- Create: `apps/server/tests/downloads/test_worker.py`

**Contract vs freedom:** the class in CONTRACT 2 + the state transitions in CONTRACT 1 are fixed. The `FakeDownloadEngine` is the **offline seam** for the whole plan.

**`FakeDownloadEngine` (conftest — the seam):**
```python
class FakeDownloadEngine:
    """Duck-types spotdl_core.download.DownloadEngine.download. Configurable per
    request via a rulebook: emit a scripted list of ProgressEvents (calling
    on_progress), optionally await an asyncio.Event/sleep to simulate a slow step
    (so cancellation/drain tests have a window), then return a DownloadOutcome
    (DOWNLOADED writing a real file into config.output_dir, SKIPPED, or FAILED)."""
    def __init__(self, *, config: DownloadConfig, script=...) -> None: ...
    async def download(self, request, on_progress=None) -> DownloadOutcome: ...
```
The pool is built with an `engine` object exposing `async download(request, on_progress)` — the real `DownloadEngine` in production, `FakeDownloadEngine` in tests. This is the constructor seam the integration test (Task 11) uses.

**Building the per-job `DownloadRequest` (worker responsibility):** from the job row + its batch + the joined `tracks`/`matches` rows, construct a Plan 4 `DownloadRequest`: `track` reconstructed from the `tracks` row (+ album), `candidate` from the `matches` row (`AudioCandidate(provider=target_provider, provider_id=target_id, url=target_url, name=candidate_name, artists=tuple(candidate_artists or ()), duration_ms=candidate_duration_ms)`), `output_format/bitrate/output_template` from the batch, `list_name=batch.name`, `list_position=job.list_position`, `list_length=batch.total_jobs`, `embed_lyrics/generate_lrc/sponsor_block` from the batch, `archive` loaded from `paths.load_archive(archive_path)` when `batch.update_archive`; **`overwrite = OverwriteMode.FORCE` when `job.attempts > 0`** (the CONTRACT 1 recovery-integrity rule — a recovered job must never trust a possibly converted-but-untagged file at its output path), else the batch's overwrite mode. **Engine/session knobs from `Settings` (the Plan-8 amendment — settings-sourced, not batch columns):** `restrict=settings.download_restrict`, `max_filename_length=settings.download_max_filename_length`, `id3_separator=settings.download_id3_separator`, `detect_formats=settings.download_detect_formats`, `skip_explicit=settings.download_skip_explicit`, `respect_skip_file=settings.download_respect_skip_file`, `create_skip_file=settings.download_create_skip_file`, `retain_track_cover=settings.download_retain_track_cover`; when `settings.download_scan_existing`, `known_paths` = a scan of `effective_library_path()` for audio files (performed once per `pool.start()` and cached on the pool — v4's scan-once-per-run parity); when `settings.download_playlist_numbering` and the batch is a PLAYLIST, rebuild the request's `track` with `track_number=job.list_position` and `album` name = `batch.name` (v4 `playlist_numbering` parity). A worker test asserts the recording `FakeDownloadEngine` sees these settings-sourced fields on the built request. `match_id is None` → skip the fetch: mark the job `failed` with `error_step="fetch"`, `error_message="no viable match"` (never call the engine).

**`_run_job` flow (per CONTRACT 1 + 2):**
1. Under the pool `asyncio.Lock`: `job = await job_repo.claim(job_id, now)`; if `None`, return (cancelled/gone). Commit. Broadcast `job_started`.
2. Register `self._running[job_id] = current_task`. Start the throttle pump.
3. Build the request; `outcome = await engine.download(request, on_progress)`.
4. Map outcome → terminal transition (`mark_completed` with `skip_reason` for SKIPPED; `mark_failed` for FAILED). Final progress flush + `job_finished`/`job_failed` broadcast.
5. `except asyncio.CancelledError`: if `self._shutting_down` → `job_repo.requeue` (running→queued, "recovered", no broadcast or a `job_queued` re-broadcast); else → `mark_cancelled` + best-effort delete partial `output_path` + broadcast `job_cancelled`. **Re-raise** if shutting down so the worker task exits.
6. `finally`: stop the pump, `self._running.pop(job_id, None)`, then **batch-finalize check** under the lock: if `batch_repo.pending_count(batch_id) == 0` and `mark_finalized(batch_id)` returns `True` → run `finalizer.finalize(batch_id)` and broadcast `batch_finished`.

**Tests (offline, in-memory DB, `FakeDownloadEngine`):**
- happy path: enqueue a scripted DOWNLOADED job → status `completed`, `output_path` set, file exists, progress reached 1.0, WS stub saw `job_started`→`progress`→`job_finished`.
- skip: engine returns SKIPPED(ALREADY_EXISTS) → `completed` + `skip_reason="already_exists"`, `job_finished.skipped is True`.
- failure isolation: engine returns FAILED(step="convert") → `failed`, `error_step="convert"`; other queued jobs still run.
- **cancellation:** engine awaits an event mid-run; `request_cancel(job_id)` → task cancelled at the await boundary → status `cancelled`, `job_cancelled` broadcast, partial file removed. Cancel a still-`queued` job → `cancelled`, engine never called.
- **crash recovery:** seed a `running` job (simulating a crash), `await pool.start()` → `recover_orphaned` flips it to `queued` with `attempts==1`, worker picks it up and completes it. Assert no job is left `running` after `start()` settles.
- **recovery re-processes, never file-skips (the crash-after-convert case):** seed a `running` job whose planned output file **already exists** in the library (simulating a crash between ConvertStep and EmbedStep) with the batch's `overwrite=SKIP`; `await pool.start()` → the worker rebuilds the request and the recording `FakeDownloadEngine` asserts it received `overwrite==OverwriteMode.FORCE` (not the batch's SKIP) and returns DOWNLOADED — the suspect file was re-processed, and the job is `completed` with `skip_reason is None` (not a skip). Companion assertion: a **fresh** (attempts==0) job with the same pre-existing file keeps `overwrite==SKIP` (legitimate skips still work).
- **temp sweep:** seed a stray file in `effective_temp_dir()`; `pool.start()` removes it (and never raises if removal fails — assert via a read-only file/monkeypatched `unlink`).
- **graceful drain:** engine sleeps beyond a tiny `drain_timeout_s`; `pool.shutdown(drain_timeout_s=0.01)` → the in-flight job is re-queued (`queued`, `started_at` NULL), not cancelled/failed; a fast in-flight job within the window completes.
- **no double-run:** two workers, one queued id enqueued twice (defensive) → `claim` transitions once; engine called once.
- **batch finalize once:** a 2-job batch; both finish → finalizer invoked exactly once (assert via a spy finalizer), `batch_finished` broadcast once.
- **no stuck states sweep:** after each scenario, assert every job is in a terminal-or-queued state (never orphaned `running`).

- [ ] **Step N — GREEN + gates.** `make check` green (all async, no network, no ffmpeg). **Commit:** `feat(server): asyncio download worker pool — state machine, cancellation, drain, crash recovery`.

---

### Task 7: `BatchFinalizer` — archive update, m3u generation, `.spotdl` v2 emission

**Files:**
- Create: `apps/server/src/spotdl_server/services/batch.py`
- Complete: `apps/server/src/spotdl_server/downloads/savefile.py` (`build_save_file` body)
- Create: `apps/server/tests/services/test_batch_finalizer.py`

**Contract vs freedom:** the **post-processing order** (archive → m3u → save-file) and the CONTRACT 7 `.spotdl` v2 output are fixed (matches v4 order; Plan 8 reads the save-file). The finalizer **reuses Plan 4 batch utilities** (`post.gen_m3u_files`, `post.archive_update`, `paths.load_archive`/`save_archive`) — it must NOT re-implement m3u/archive logic.

**`BatchFinalizer` (CONTRACT):**
```python
class BatchFinalizer:
    def __init__(self, *, sessionmaker: async_sessionmaker[AsyncSession],
                 settings: Settings) -> None: ...
    async def finalize(self, batch_id: UUID) -> BatchFinalizeResult: ...
        # opens its own session; idempotency already guaranteed by the pool's
        # mark_finalized gate (Task 6). Order (v4 parity, downloader.py 319-354):
        #   1) archive: if batch.update_archive -> load_archive(path); archive_update(
        #      current, [(track_url, ok) for each job],
        #      add_unavailable=settings.download_add_unavailable); save_archive.
        #   2) m3u: if batch.generate_m3u -> build post.M3uEntry per completed job
        #      (track, output_path, list_name=batch.name); post.gen_m3u_files(
        #      entries, batch.m3u_template, batch.output_template, output_format, ...).
        #   3) save-file: if batch.generate_save_file -> build_save_file(batch, jobs,
        #      tracks, matches); write dump_save_file(model) to batch.save_file_path.
        # returns paths produced (m3u_paths, save_file_path) for the WsBatchFinished msg.
```
`BatchFinalizeResult{m3u_paths: list[Path], save_file_path: Path | None, counts: dict[str,int]}`.

Archive path: `settings.effective_library_path() / ".spotdl-archive.txt"` unless a per-batch path is configured (v1: fixed library-root archive). m3u/save-file default paths derive under the library root when the batch didn't pin one (`m3u_template` default `"{list[0]}.m3u8"` per Plan 4; save-file default `<library>/<name or 'download'>.spotdl`).

**Tests (offline, in-memory DB, tmp library dir):** a completed 2-track PLAYLIST batch with `generate_m3u/generate_save_file/update_archive=True`: archive file gains both track urls (order-stable, sorted by `save_archive`); an `.m3u8` is written containing `#EXTM3U` + both entries (delegated to Plan 4 `gen_m3u_files` — assert the file exists and has the header, not the exact templating which Plan 4 tests own); the `.spotdl` file parses as `SaveFileV2(version=2, kind="playlist", songs=[2])` with each song carrying its `match` + `download.status="completed"`; a failed job still appears in `songs` with `download.status="failed"` but is excluded from archive/m3u. Finalizer is safe to call once (idempotency owned by the pool gate; a direct double-call test asserts it does not double-append the archive because it rewrites, not appends).

- [ ] **Step 4 — GREEN + gates.** `make check` green. **Commit:** `feat(server): batch finalizer — archive/m3u/.spotdl v2 emission (v4 order)`.

---

### Task 8: Lifespan wiring, mode gating, auth dependency

**Files:**
- Modify: `apps/server/src/spotdl_server/app.py` (lifespan + conditional mount), `api/deps.py`
- Create: `apps/server/tests/api/test_download_mode_gating.py`

**Contract vs freedom:** the **mode/auth matrix** and the **startup gating** (router mounted or not) are CONTRACT (spec §4). The engine-injection seam is CONTRACT (tests need it).

**Lifespan additions (`app.py`, no singletons):**
```python
def create_app(settings=None, *, download_engine=None) -> FastAPI:
    # download_engine: optional override (FakeDownloadEngine in tests). None -> built
    # lazily in the lifespan via build_default_engine(settings.download_config()) ONLY
    # when settings.downloads_enabled().
    ...
    @asynccontextmanager
    async def lifespan(app):
        # ... Plan 5/6 engine/sessionmaker/registry/clock/limiter setup ...
        if settings.downloads_enabled():
            engine = download_engine or build_default_engine(settings.download_config())
            hub = ProgressHub()
            finalizer = BatchFinalizer(sessionmaker=app.state.sessionmaker, settings=settings)
            pool = DownloadWorkerPool(sessionmaker=app.state.sessionmaker, engine=engine,
                                      hub=hub, settings=settings, finalizer=finalizer,
                                      clock=app.state.clock)
            app.state.download_hub = hub
            app.state.download_pool = pool
            await pool.start()          # crash recovery + spawn workers
        try:
            yield
        finally:
            if settings.downloads_enabled():
                await app.state.download_pool.shutdown()   # graceful drain
            # ... Plan 5/6 teardown ...
```

**Mode gating (startup, spec §4):** in `create_app`, `if settings.downloads_enabled(): app.include_router(downloads_router); app.include_router(progress_ws_router)`. **Hosted mounts neither, and does not build the pool/hub/engine.** This replaces Plan 5's commented seam.

**Startup fail-fast:** `create_app` calls `settings.require_download_auth_consistency()` (Task 1) right where Plan 6 calls `require_auth_secret()` — a selfhost operator who sets `downloads_require_auth=True` while auth is inactive gets a `RuntimeError` at boot, never a silently-open download surface.

**Auth dependency (`api/deps.py`) — `require_download_access` (CONTRACT matrix):**
```python
async def require_download_access(request, auth = Depends(get_auth_context)) -> AuthContext:
    """embedded -> always allow (loopback; auth_active() is False by default there).
       selfhost -> allow unless settings.downloads_require_auth and settings.auth_active()
                   (Plan 6's DERIVED gate — never raw auth_enabled, whose None default
                   would make the requirement silently no-op), in which case require
                   auth.kind != 'anonymous' (401 authentication_required).
       hosted   -> unreachable (router not mounted).
    The inconsistent combination (downloads_require_auth without active auth) cannot
    reach here — create_app fails fast at startup."""
```
Plus `get_download_pool`/`get_download_hub` (read `request.app.state`; 503 if downloads disabled — defensive, though the route won't be mounted) and `get_download_queue_service(session, ...)` composing `DownloadQueueService` with `requested_by = auth.user_id`.

**Tests (`test_download_mode_gating.py`, offline):**
- `test_hosted_mounts_no_download_routes` — build `create_app(Settings(mode=HOSTED))`; assert no route path starts with `/api/v1/downloads` and no `/ws/progress` route exists; assert `app.state` has no `download_pool`.
- `test_selfhost_mounts_download_routes` and `test_embedded_mounts_download_routes` — the routes exist.
- `test_selfhost_requires_auth_when_configured` — with `downloads_require_auth=True`, `auth_enabled=True` + secret, `require_download_access` rejects anonymous (401) and admits a valid JWT; embedded allows anonymous.
- `test_selfhost_require_auth_without_active_auth_fails_startup` — `create_app(Settings(mode=SELFHOST, downloads_require_auth=True, auth_enabled=False))` raises `RuntimeError` (the None/False-falsy no-op bug is impossible by construction).
- lifespan build uses the injected `FakeDownloadEngine` (no real engine constructed offline) — assert `pool.start()`/`shutdown()` run cleanly via the ASGI lifespan (httpx `ASGITransport` with lifespan, or `LifespanManager`).

- [ ] **Step N — GREEN + gates.** `make check` green. **Commit:** `feat(server): download lifespan wiring, startup mode gating, auth access dependency`.

---

### Task 9: HTTP download router (`POST/GET/DELETE /downloads`, file delivery, batch/save-file)

**Files:**
- Create: `apps/server/src/spotdl_server/api/routers/downloads.py`
- Create: `apps/server/tests/api/test_downloads_api.py`, `tests/api/test_download_file_api.py`

**Contract vs freedom:** the endpoint surface (CONTRACT 4) + file semantics (CONTRACT 6) are fixed. Router ≤200 lines, no business logic (delegates to `DownloadQueueService`/`BatchFinalizer`/repos via service deps), no ORM import.

**Router (all `Depends(require_download_access)`):**
- `POST /downloads` → `service.submit(req)`; after the service commits, `pool.enqueue(ids)` + `hub.broadcast(WsJobQueued(...))` per job; return `DownloadSubmitResponse` (201). `NoMatchFound` from expand → 404 `no_match_found` (Plan 5 handler). Artist entity → `UnsupportedBatchEntity` → 400 `unsupported_entity` detail `{"entity_type":"artist"}` (new `ErrorCode` row registered in `api/errors.py`'s `_status_and_code` table).
- `GET /downloads?status=&batch_id=&limit=&offset=` → `service.list_jobs(...)`.
- `GET /downloads/{job_id}` → `service.get_job(id)` (404 via `NotFoundError`).
- `DELETE /downloads/{job_id}` → `pool.request_cancel(id)`; if `False` and job terminal → 409 `download_failed` detail `{"reason":"already_terminal"}`; else return the refreshed `DownloadJobOut` (204/200). Broadcast handled by the pool/worker.
- `GET /downloads/{job_id}/file` → CONTRACT 6 (load job; ready check; path-traversal check; `FileResponse` or `X-Accel-Redirect`).
- `GET /downloads/batches/{batch_id}` → `service.get_batch(id)`.
- `GET /downloads/batches/{batch_id}/save-file` → build `SaveFileV2` for the batch (via a small service/finalizer helper reading jobs+tracks+matches); return `Response(dump_save_file(model), media_type="application/json")` + `Content-Disposition: attachment; filename="<name>.spotdl"`.

**Tests (offline, `httpx.ASGITransport`, `FakeDownloadEngine` injected via `create_app(download_engine=...)`, fake registry for resolve):**
- submit a track url → 201 + batch with 1 job; the pool actually runs it (await settle) → `GET /downloads/{id}` eventually `completed`.
- submit album → N jobs, ordered `list_position`.
- list with `status=completed` / `batch_id=` filters + pagination (`total`).
- cancel a queued job → `cancelled`; cancel a terminal job → 409.
- `test_download_file_api.py`: completed job with a real file under the tmp library → 200 stream + `Content-Disposition`; not-ready (queued) → 409; **path traversal:** a job whose `output_path` points outside the library root → 404 (not leaked); missing file → 404; with `download_x_accel_prefix` set → empty body + `X-Accel-Redirect` header, correct relative path.
- save-file endpoint → valid `SaveFileV2` JSON, `version==2`, attachment header.

- [ ] **Step N — GREEN + gates.** `make check` green; `test_routers_under_200_lines` (Plan 5) still passes for `downloads.py`. **Commit:** `feat(server): /downloads router — submit/list/cancel/file/batch/save-file`.

---

### Task 10: WebSocket router (`WS /ws/progress`)

**Files:**
- Create: `apps/server/src/spotdl_server/api/routers/progress_ws.py`
- Create: `apps/server/tests/api/test_progress_ws.py`

**Contract vs freedom:** CONTRACT 3 protocol + the WS auth rule are fixed. Router ≤200 lines.

**Router:**
```python
@router.websocket("/ws/progress")
async def progress_ws(websocket: WebSocket) -> None:
    # 1) auth: mirror require_download_access using a query-param token (?token=...)
    #    because browsers cannot set Authorization on WS. embedded -> open (auth_active()
    #    False by default); selfhost -> if ws_progress_require_auth (derived from
    #    downloads_require_auth) AND settings.auth_active() require a valid JWT/PAT
    #    token, else open; hosted -> route not mounted. (The inconsistent require-auth-
    #    without-active-auth combination is unrepresentable — startup fail-fast, Task 8.)
    #    Close with code 4401 on auth failure BEFORE accept-completion semantics.
    # 2) hub.register(websocket); send WsHello (protocol_version, CONTRACT 3) as the
    #    first frame; then snapshot current non-terminal jobs.
    # 3) loop: await websocket.receive() to detect disconnect (ignore inbound payloads);
    #    on WebSocketDisconnect -> hub.unregister; return. Never let one client error
    #    affect broadcasts (hub.broadcast already isolates send failures).
```
Auth token validation reuses Plan 6 `TokenService.verify_access` / PAT lookup via the same logic `get_auth_context` uses, but sourced from the `token` query param.

**Tests (offline, Starlette `TestClient.websocket_connect` against the ASGI app with `FakeDownloadEngine`):**
- the first received frame is `{"type":"hello","protocol_version":1}`.
- connect, then submit a job via the HTTP API in the same app → the WS client receives `job_queued`→`job_started`→`progress`→`job_finished` in order after the hello (drive the fake engine to emit scripted progress).
- two clients both receive broadcasts; disconnect one → the other keeps receiving (client-gone isolation).
- selfhost + `ws_progress_require_auth=True`: connecting without `?token=` closes with 4401; with a valid token connects.
- embedded: connects with no token.

- [ ] **Step N — GREEN + gates.** `make check` green. **Commit:** `feat(server): WS /ws/progress fan-out endpoint with per-mode auth`.

---

### Task 11: OpenAPI regen + in-sync test + end-to-end integration + self-review

**Files:**
- Modify: `apps/server/openapi.json` (regenerate), `apps/server/scripts/export_openapi.py` (unchanged if it already builds in SELFHOST — verify the download routes now appear)
- Create: `apps/server/tests/api/test_downloads_integration.py`
- Modify: `apps/server/tests/test_openapi.py` (assert a download path is documented)

- [ ] **Step 1 — RED-ish: extend `test_openapi.py`.** After regen, `test_openapi_in_sync` compares byte-for-byte (fails → "run `make openapi`"); add `test_download_routes_documented`: `/api/v1/downloads` `POST` and `/api/v1/downloads/{job_id}/file` `GET` are present in the SELFHOST-built schema, and the WS route is excluded (FastAPI does not emit WS in OpenAPI — assert the HTTP surface only).

- [ ] **Step 2 — `test_downloads_integration.py` (the acceptance test, fully offline).** Real in-memory DB (migrated via Alembic so the amendment migration is exercised), fake provider registry (resolve returns a track + a persisted match), `FakeDownloadEngine` injected via `create_app(download_engine=...)`, httpx `ASGITransport` + a WS `TestClient` on the same app:
  1. open `WS /ws/progress`.
  2. `POST /downloads {track url, generate_save_file, generate_m3u}` → 201, batch of 1.
  3. observe WS `job_queued`→`job_started`→`progress`→`job_finished` (fake engine writes a real file into the tmp library and emits scripted progress).
  4. `GET /downloads/{id}` → `completed`; `GET /downloads/{id}/file` → 200 with the file bytes + `Content-Disposition`.
  5. `GET /downloads/batches/{batch_id}/save-file` → `SaveFileV2 version==2`.
  6. assert the finalizer produced an m3u + save-file on disk and a `batch_finished` WS message arrived.
  Plus the **crash-recovery** and **cancellation** scenarios wired through the HTTP/WS surface (seed a stale `running` row before app start → after start it completes; submit a slow job then `DELETE` it → `cancelled` + WS `job_cancelled`).

- [ ] **Step 3 — regenerate + commit `openapi.json` (and re-verify `ws-protocol.json`).** `make openapi`; verify the download HTTP routes + `ErrorEnvelope` responses (incl. the new `unsupported_entity` code) appear; `make ws-schema` is a no-op if Task 2's artifact is current (the in-sync test guards drift); commit.

- [ ] **Step 4 — layering + gates.** `uv run lint-imports` green (worker depends on a `Broadcaster` Protocol, not `api/`; services import no fastapi; routers import no ORM). `make check` green.

- [ ] **Step 5 — Commit:** `test(server): downloads OpenAPI sync + offline end-to-end integration (submit→WS→file→save-file)`.

---

## Self-review

**Every §6.2/§6.3 download requirement mapped:**

| Spec requirement | Where |
|---|---|
| `POST /downloads` | CONTRACT 4; Task 4 (service) + Task 9 (router) |
| `GET /downloads` (list, filters, pagination) | CONTRACT 4; `DownloadJobRepository.list`; Task 4/9 |
| `DELETE /downloads/{id}` (cancel) | CONTRACT 1/2 (queued + running); Task 6 (`request_cancel`) + Task 9 |
| `GET /downloads/{id}/file` (browser delivery) | CONTRACT 6; Task 9 (`FileResponse`/`X-Accel-Redirect`, path-traversal, completed-only) |
| `WS /ws/progress` (single fan-out) | CONTRACT 3; Task 5 (hub) + Task 10 (router) |
| DB-backed jobs, no Redis/celery, in-process asyncio pool | CONTRACT 2; Task 6 |
| Jobs survive restarts (crash recovery) | CONTRACT 1 recovery; Task 3 `recover_orphaned` + Task 6 `start()` |
| Progress via WebSocket | CONTRACT 3/5; Task 5/6 throttle pump → hub |
| Server settings: concurrency, library path, default format/bitrate/template | Task 1 settings + `/config` download_defaults |
| Full Plan 4 option coverage via Settings (Plan 8 required amendment) | Task 1 eleven `download_*` engine/session knobs → Task 6 request-build / Task 7 `add_unavailable` |
| Mode gating: hosted NOT mounted; selfhost + embedded enabled | spec §4; Task 8 startup gating + `test_download_mode_gating` |
| Batch: album/playlist expansion server-side | CONTRACT 4; Task 4 `submit` expand |
| m3u per playlist job group, archive maintenance, .spotdl v2 | CONTRACT 7; Task 7 `BatchFinalizer` (reuses Plan 4 `post`/`paths`) |

**Job state machine has no stuck states.** Cancelled-while-running (task.cancel at await boundary → `cancelled`, partial file removed); crash mid-step (boot `recover_orphaned` running→queued, single-process invariant); graceful shutdown (drain then re-queue, not fail); WS client gone (`broadcast` isolates per-client send failures — a dead socket never blocks a job or another client). Every terminal transition sets `finished_at`; the worker's `finally` always removes the task from `_running` and runs the idempotent batch-finalize gate. The Task 6 "no stuck states sweep" asserts no orphaned `running` after each scenario.

**Recovery never trusts file existence.** A crash/drain mid-Convert/Embed leaves a converted-but-untagged or partial file at the planned output path; the `attempts` column (Amendment C) marks every recovered/re-queued job, and the worker forces `overwrite=FORCE` for `attempts > 0` so the engine re-fetches/re-converts/re-embeds instead of `plan_skip`-ing the suspect file as `ALREADY_EXISTS` (CONTRACT 1 recovery-integrity rule; Task 6 crash-after-convert test pins both the FORCE override and that fresh jobs keep legitimate skip behaviour). `pool.start()` also sweeps the temp dir for crash-orphaned mid-fetch partials.

**Auth gating cannot silently no-op.** The download/WS gates key on Plan 6's derived `settings.auth_active()` (never raw `auth_enabled`, whose `None` default would falsy-out the check in selfhost), and `create_app` fails fast via `require_download_auth_consistency()` when `downloads_require_auth=True` while auth is inactive — mirroring Plan 6's `require_auth_secret()` pattern, with a startup test pinning it.

**`.spotdl` v2 schema complete for Plan 8 sync.** Each song carries full track metadata + the chosen `match` (audio target with url/score/matcher_version) + `download` settings/result — enough for `spotdl sync` to reconcile (re-download missing, prune removed, reuse or re-match). Versioned (`version==2`) and self-describing so Plan 8 auto-migrates v4's bare-array format. Documented DB-metadata gap (date/publisher/copyright/cover serialize null) is additive-safe.

**Consistency with Plans 4/5/6 (exact names quoted):** consumes Plan 4 `DownloadEngine.download(request, on_progress) -> DownloadOutcome`, `DownloadConfig`, `DownloadRequest`, `DownloadOutcome`/`OutcomeStatus`/`SkipReason`, `ProgressEvent`/`ProgressPhase`/`ProgressCallback`, `build_default_engine`, `post.gen_m3u_files`/`post.M3uEntry`/`post.archive_update`, `paths.load_archive`/`save_archive` — never re-implementing pipeline or m3u/archive logic. Uses Plan 5 `DownloadStatus`, `DownloadJob` ORM, `ErrorEnvelope`/`ErrorCode` (`downloads_disabled`/`download_failed` rows already defined-now in Plan 5), `NotFoundError`, `ResolveService`/`EntityService`/`MatchRepository`/`TrackRepository`, `build_sessionmaker`, `ConfigResponse`/`FeatureFlags`. Uses Plan 6 `AuthContext`/`ANONYMOUS`/`get_auth_context`/`require_user`, `Clock`, `TokenService.verify_access`. The download engine's per-track failure isolation (Plan 4) means the worker never sees a raised pipeline error except `CancelledError` (a `BaseException`, deliberately not caught by the engine) — the cancellation seam depends on exactly that Plan 4 guarantee.

**Cancellation seam is honest, not aspirational.** asyncio task cancellation delivers at the `await` boundary between the engine's `to_thread` steps; the in-flight blocking step (yt-dlp/ffmpeg) completes in its thread first (threads can't be force-killed) — latency bounded by one step, documented as v1 granularity. No fictional mid-ffmpeg interrupt.

**Single-process boundary documented.** Claim safety = one `asyncio.Lock` in one process; crash recovery = unconditional running→queued at boot; multi-process (`SELECT FOR UPDATE SKIP LOCKED`) is a noted non-goal, not silently assumed.

**WS protocol is codegen-consumable.** The `WsMessage` union ships as a committed, deterministic JSON Schema artifact (`apps/server/ws-protocol.json`, `make ws-schema`, in-sync test) with a `WsHello` version envelope (`protocol_version=1`) sent as the first frame — Plan 8's generated clients get typed WS messages the same way they get typed HTTP models from `openapi.json`.

**Plan 8's required Settings amendment is folded in, not deferred.** The eleven engine/session knobs Plan 8 flagged (`download_restrict`, `download_max_filename_length`, `download_id3_separator`, `download_detect_formats`, `download_skip_explicit`, `download_respect_skip_file`, `download_create_skip_file`, `download_playlist_numbering`, `download_retain_track_cover`, `download_add_unavailable`, `download_scan_existing`) live in Task 1's `Settings` with exact Plan 4 `DownloadRequest` names/types/v4-parity defaults, flow into the worker's request-build (Task 6; `scan_existing`→`known_paths` scanned once per `pool.start()`; `playlist_numbering` remaps track_number/album for playlist batches) and the finalizer's `archive_update(add_unavailable=...)` (Task 7), and surface read-only in `/config`'s `DownloadDefaults` — additive Settings + request-build only: no new API request field, no schema column, no migration, preserving the schema-frozen guarantee. `test_engine_knob_settings_present` is the fail-loud guard Plan 8's Task 7 expects.

**Endpoint surface is spec-mapped, additions are pinned.** The three endpoints beyond §6.2's literal list (`GET /downloads/{job_id}`, `GET /downloads/batches/{batch_id}`, `GET .../save-file`) carry explicit scope-note justifications under CONTRACT 4 (polling fallback; batch-oriented queue UI; the pinned `.spotdl` v2 emission endpoint for `spotdl save`/`sync`). The artist rejection uses a purpose-minted `unsupported_entity` error code with a typed detail payload rather than stretching `unsupported_url`.

**No TBDs.** Every task has exact files, CONTRACT-pinned signatures, test names, and gates. The Plan-5 schema amendments (incl. the `attempts` recovery column) are flagged at the top as REQUIRED (not ALTERed here); Task 1's guard test fails if they are absent. Bounded implementer choices (archive path location) are stated with a v1 default, not left open; the WS connect-snapshot and hello frame are pinned, not optional.
