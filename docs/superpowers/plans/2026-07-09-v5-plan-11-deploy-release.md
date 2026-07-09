# spotDL v5 — Deployment, Hosting, Observability, Docs & Release (Plan 11 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Opus-class implementers assumed.** Much of this plan is infrastructure config: use TDD where a Python unit is testable (observability code), and explicit **verification commands** (build the image, boot it, curl an endpoint) where the artifact is YAML/Dockerfile/docs.

**Goal:** Ship everything needed to run, distribute, and release spotDL v5 (spec §9 community hosting & ops, §12 migration & release). Concretely: server observability (structlog JSON logs + `/metrics` Prometheus endpoint + optional Sentry), a single multi-stage Docker image published to GHCR (byte-identical to what Railway runs), the self-host compose stack + Caddy example, Railway config-as-code with managed Postgres + Redis + Cloudflare notes, the mkdocs-material docs site (incl. the v4→v5 migration guide **generated** from Plan 8's shim table and an API reference that reuses Plan 5's committed server OpenAPI artifact), PyPI trusted-publishing (dependency-ordered `spotdl-core → spotdl-server → spotdl`), PyInstaller binaries that default to the TUI, nightly Postgres backups with a restore drill, a v5 README + repo housekeeping, and a documented GA-cutover runbook. **This plan does NOT perform the GA cutover** (Docker Hub `latest` switch, `legacy-v4` retag, `master` swap) — it produces the runbook for it.

**Architecture:** Per spec §9/§12. One server codebase, one Docker image; mode is chosen at runtime by `SPOTDL_MODE` (`hosted|selfhost|embedded`, spec §4). The community instance runs on **Railway** (server in `hosted` mode + managed Postgres + managed Redis) behind **Cloudflare**; self-hosters pull the **same GHCR image**. The built React SPA (Plan 10) is embedded as static assets inside the `spotdl-server` package so `spotdl web`, the Docker image, and the PyPI wheel all serve the UI with no runtime fetch (spec §8). Observability code lives in `apps/server` (`spotdl_server.observability`), instrumenting the existing resolve/provider/queue/match seams from Plans 5–7. Everything deployable lives under `deploy/`; docs under `docs/`; release automation under `.github/workflows/` + `scripts/`.

**Tech Stack:** structlog, prometheus-client, optional sentry-sdk (server extras). Docker (multi-stage, buildx multi-arch amd64+arm64), Caddy. Railway config-as-code (`railway.toml`). mkdocs-material + mkdocs-gen-files + mkdocs-swagger-ui-tag. PyInstaller (matrix incl. aarch64). GitHub Actions: GHCR/Docker Hub publish (`docker/*-action`), PyPI trusted publishing (`pypa/gh-action-pypi-publish`, OIDC), `mkdocs gh-deploy`. pg_dump + rclone/aws-cli for backups. Python 3.13, uv workspace; Node 22 / pnpm 11.10.0 for the web build.

## Global Constraints

- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from there unless a step says otherwise.
- Python `>=3.13`; Node `>=22`; **pnpm `11.10.0`** — the ONE pnpm pin everywhere, matching Plan 10 Task 1's `"packageManager": "pnpm@11.10.0"` in `apps/web/package.json` and the existing ci.yml `web` job; single uv lockfile at the workspace root. Package names/versions: `spotdl-core`, `spotdl-server`, `spotdl` (CLI). All three currently at `5.0.0a0`.
- Server settings use `pydantic-settings` with `env_prefix="SPOTDL_"` (Plans 1/5/6). **Every runtime env var this plan introduces is `SPOTDL_`-prefixed** so it flows through `Settings` uniformly. The one exception is the standard container `PORT` (Railway/compose convention), which the entrypoint maps.
- Dependency direction `core ← server ← cli` stays machine-enforced (import-linter). Nothing in `deploy/`, `docs/`, or `scripts/` may violate it; the docs migration-guide generator imports `spotdl_cli` (the CLI is the top of the stack — allowed).
- **No code is copied from the `xnetcat-rewrite` branch.** The repo-root `Dockerfile`, `docker-compose*.yml`, `railway.toml`, and `nginx/` currently present on the `master`/scaffolding checkout are **anti-pattern references only** (they assume a `backend/`+`frontend/`+`core/` layout that does not exist in v5). This plan writes fresh artifacts under `deploy/` against the real `apps/`+`packages/` layout and deletes the stale root copies (Task 2/4).
- **Secrets never live in the repo.** See the Secrets Location table below — every secret is a GitHub Actions secret, a GitHub environment secret (OIDC needs none), or a Railway service variable. CI/compose/docs reference them by name only. `.env.example` ships with placeholder values and is the only committed env file.
- `make check` (lint + typecheck + test + web-check) must pass at the end of every task that touches Python or web code. Config-only tasks run the task's stated verification command instead; they must not break `make check`.
- CI additions are **new jobs**; the existing `python` and `web` jobs in `.github/workflows/ci.yml` stay green and unmodified except for additive `needs`/matrix where noted.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## Plan series roadmap (context — not part of this plan)

1. Bootstrap monorepo — **done** (`create_app(settings)`, `SPOTDL_MODE`, `/api/v1/health`, `/api/v1/config`).
2. `core.providers`. 3. `core.matching` + golden corpus. 4. `core.download`. 5. Server foundation (schema, resolve/search/entity, `bootstrap.upgrade_to_head`, OpenAPI artifact). 6. Server community layer (auth, votes, reports, admin, **rate limiting** w/ optional Redis). 7. Server downloads (queue, WS progress). 8. Generated clients + CLI + **v4 compat shim table** (`V4_FLAG_TABLE`). 9. Textual TUI. 10. Web UI (built SPA embedded in `spotdl-server`).
11. **This plan** — deploy, hosting, observability, docs, release.

## What already exists (consumed, not recreated)

- **Server app factory (CONTRACT, Plan 5):** `spotdl_server.app.create_app(settings: Settings | None = None, *, registry: ProviderRegistry | None = None) -> FastAPI`. Lifespan builds engine/sessionmaker/registry on `app.state`. Endpoints today: `GET /api/v1/health`, `GET /api/v1/config`.
- **Migration entry point (CONTRACT, Plan 5):** `spotdl_server.bootstrap.upgrade_to_head(settings)` — programmatic, idempotent Alembic upgrade against `settings.effective_database_url()`, package-relative config (works from any CWD and from a wheel). **This is the only migration entry point; the container entrypoint calls it, never raw `alembic`.** Plan 5 packages the alembic scripts dir into the `spotdl-server` wheel (Hatch includes) so this works from the venv/wheel — Task 2's `--no-editable` build depends on that.
- **Settings (`env_prefix="SPOTDL_"`, Plans 1/5/6):** `mode: DeploymentMode(HOSTED|SELFHOST|EMBEDDED)`, `data_dir`, `database_url` + `effective_database_url()`, `db_echo`, `auth_secret_key: SecretStr | None`, token TTLs, OAuth creds, `redis_url: str | None`, `rate_limit_enabled: bool`. Plan 6 selects `RedisRateLimiter` **only when `settings.redis_url` is set AND the optional `redis` package is importable**, else `InMemoryRateLimiter`; the middleware is added at startup only in `hosted` mode or when `rate_limit_enabled` is `True`.
- **`GET /metrics` is explicitly NOT implemented by Plan 5** ("out of scope and NOT routed here"). This plan implements it.
- **Error envelope (Plan 5):** `ErrorEnvelope{code, message, detail}`, `ErrorCode` StrEnum, `register_exception_handlers(app)`.
- **Compat shim (Plan 8):** `spotdl_cli`'s module-level `V4_FLAG_TABLE` (the four row-kinds SAME/RENAME/SOFT-DROP/DROP) plus the `.spotdl` v4→v2 field table are "**also the migration-guide source**". This plan's generator renders them to Markdown.
- **CLI default API URL placeholder (Plan 8):** `spotdl_cli/transport.py` ships a placeholder community URL with the note "the real community URL is pinned in Plan 11 (spec §12); MUST NOT ship as a localhost stub, localhost is NEVER the default." Task 6 pins it.
- **Web build (Plan 10):** `pnpm -C apps/web build` → `apps/web/dist`. Runtime-configurable API base URL (spec §8), so one SPA build serves any deployment.

## Secrets location (authoritative — nothing below is committed)

| Secret / value | Lives in | Consumed by |
|---|---|---|
| PyPI publish (per project: `spotdl-core`, `spotdl-server`, `spotdl`) | **Nothing stored** — OIDC Trusted Publishing; GitHub environment `pypi` + PyPI project trusted-publisher config | `release-pypi.yml` |
| GHCR push | Built-in `GITHUB_TOKEN` (`packages: write`) | `release-docker.yml` |
| Docker Hub push | GH Actions secrets `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` | `release-docker.yml` (GA job) |
| Railway deploy token | Railway project (GitHub-repo trigger) or GH secret `RAILWAY_TOKEN` if CLI-deployed | Railway build trigger |
| `SPOTDL_AUTH_SECRET_KEY` (hosted JWT key) | Railway service variable | server runtime |
| `SPOTDL_DATABASE_URL` | Railway reference var `${{Postgres.DATABASE_URL}}` | server runtime |
| `SPOTDL_REDIS_URL` | Railway reference var `${{Redis.REDIS_URL}}` | server runtime (rate limit) |
| Spotify operator creds (`SPOTDL_SPOTIFY_CLIENT_ID/_SECRET`, names per Plan 2) | Railway service variable | server runtime |
| `SPOTDL_SENTRY_DSN` (optional) | Railway service variable (self-host: user env) | server runtime |
| Object-storage creds for backups (`SPOTDL_BACKUP_*` / rclone/S3) | Railway backup-service variables | `deploy/backup/backup.sh` on Railway cron |
| Cloudflare | Managed in Cloudflare dashboard (no repo/CI secret) | edge |

---

## THE CONTRACTS (authoritative — verbatim; implementers copy these, only internals are free)

### CONTRACT A — Observability: structlog JSON log schema + `/metrics`

**Module:** `apps/server/src/spotdl_server/observability/` — `logging.py`, `metrics.py`, `middleware.py`, `sentry.py`, `__init__.py`. No FastAPI/ORM types leak into `metrics.py`/`logging.py` (plain functions + module-level metric objects).

**A1 — structlog JSON logs.** `configure_logging(settings)` installs a structlog processor chain emitting **one JSON object per line** to stdout. Standard-library logging (uvicorn, sqlalchemy, alembic) is routed through structlog via `logging.config.dictConfig` so every line shares the schema. Log level from `settings.log_level` (new field, default `"INFO"`). Fields on **every** record:

```
ts            ISO-8601 UTC, e.g. "2026-07-09T12:34:56.789Z"   (structlog.processors.TimeStamper(fmt="iso", utc=True))
level         "debug"|"info"|"warning"|"error"|"critical"
event         the log message (string)
logger        logger name (e.g. "spotdl_server.services.resolve")
mode          settings.mode.value  ("hosted"|"selfhost"|"embedded")
```

Request-scoped records (added by the middleware via `structlog.contextvars`) additionally carry:

```
request_id    correlation id (see A3)
method        HTTP method
path          route template ("/api/v1/tracks/{id}", NOT the concrete path — no high-cardinality)
status_code   int
duration_ms   float, wall-clock request duration
client_ip     best-effort client IP — read from `settings.client_ip_header` (Plan 6; e.g. "cf-connecting-ip" behind Cloudflare) when set, else X-Forwarded-For first hop, else peer. MUST use the same header the rate limiter trusts, so logs and limiting agree.
```

Exceptions add `exc_info` rendered to an `exception` field (traceback string). **No secrets, tokens, passwords, full query strings, or request bodies are ever logged.** In `embedded` mode logging defaults to level `WARNING` and a console (non-JSON) renderer for a clean CLI experience; `hosted`/`selfhost` default to JSON.

**A2 — `/metrics` Prometheus endpoint.** `create_metrics_router() -> APIRouter` mounts `GET /metrics` (top-level, **not** under `/api/v1` — spec §9 says `/metrics`) returning `prometheus_client.generate_latest()` with content-type `text/plain; version=0.0.4`. Mounted by `create_app` unless `settings.metrics_enabled` is `False` (new field, default `True`). Uses a module-level `REGISTRY` (the default global registry). Metric objects (created once at import; label sets fixed and low-cardinality):

```
spotdl_http_requests_total          Counter    labels: method, path, status_code     # request rate
spotdl_http_request_duration_seconds Histogram  labels: method, path                   # latency (buckets: .01,.025,.05,.1,.25,.5,1,2.5,5,10)
spotdl_cache_events_total           Counter    labels: entity_type, result            # result="hit"|"miss"  → cache hit ratio
spotdl_provider_requests_total      Counter    labels: provider, capability, outcome  # outcome="ok"|"error"|"degraded" → provider error rate
spotdl_resolve_queue_depth          Gauge      (no labels)                            # bounded resolve/backpressure queue depth (§6.4)
spotdl_download_queue_depth         Gauge      labels: status                         # status="queued"|"running" (selfhost/embedded, Plan 7)
spotdl_matches_served_total         Counter    labels: matcher_version                # matcher version distribution (§9 A/B)
```

`path` label is always the **route template** (`request.scope["route"].path_format` when available, else `"__unmatched__"`) to bound cardinality. The module exposes thin increment helpers so callers never import prometheus objects directly:

```python
# spotdl_server/observability/metrics.py  (increment helpers — the ONLY public surface for instrumenting)
def record_cache_event(entity_type: str, *, hit: bool) -> None: ...
def record_provider_call(provider: str, capability: str, outcome: str) -> None: ...   # outcome in {"ok","error","degraded"}
def set_resolve_queue_depth(n: int) -> None: ...
def set_download_queue_depth(status: str, n: int) -> None: ...
def record_match_served(matcher_version: str) -> None: ...
```

Instrumentation call sites (this plan adds the calls at existing seams; it does NOT restructure services):
- `record_cache_event` — in the resolve service around the `provider_snapshots` cache-hit / cache-miss branch (Plan 5).
- `record_provider_call` — in the provider registry / `HttpProvider` wrapper (Plan 2), keyed by the `degraded_sources` outcome (spec §10).
- `set_resolve_queue_depth` — where the §6.4 resolve backpressure queue enqueues/dequeues (Plan 6). If that queue is not yet present, the gauge stays 0 and a `# TODO(plan-6-seam)`-free comment references the seam; a test asserts the gauge exists and defaults to 0.
- `set_download_queue_depth` — in Plan 7's `download_jobs` worker pool on state transitions.
- `record_match_served` — in the match-serving path (Plan 5/6) keyed by the returned `matcher_version`.

**A3 — correlation id + request-logging middleware.** `RequestContextMiddleware` (pure ASGI or `BaseHTTPMiddleware`): on each request, read inbound `X-Request-ID` (accept only a sane `[A-Za-z0-9._-]{1,128}` value, else generate `uuid4().hex`); bind `request_id` (+ method/path/client_ip) into `structlog.contextvars`; time the request; on response set the response header `X-Request-ID` and emit one structured access-log line (`event="http_request"`) with `status_code` + `duration_ms`; also `record_http_request(method, path_template, status_code, duration)` (increments the two http metrics). Always clears contextvars in a `finally`. Ordering: added so it wraps routing (runs first inbound, last outbound).

**A4 — optional Sentry.** `init_sentry(settings)` in `sentry.py`: if `settings.sentry_dsn` is set **and** `sentry_sdk` importable (behind the `sentry` extra), call `sentry_sdk.init(dsn=..., environment=settings.mode.value, traces_sample_rate=settings.sentry_traces_sample_rate, release=__version__)` with the Starlette/FastAPI integration and `send_default_pii=False`. No-op (single debug log) when unset. Called once from `create_app`.

**A5 — wiring in `create_app`.** At the top of `create_app`, before building routers: `configure_logging(settings)`, `init_sentry(settings)`. Add `RequestContextMiddleware`. Mount `create_metrics_router()` when `settings.metrics_enabled`. This is the **only** edit to `app.py`; the factory signature is unchanged.

**New `Settings` fields (append to `settings.py`, all `SPOTDL_`-prefixed):**
```python
log_level: str = "INFO"
metrics_enabled: bool = True
sentry_dsn: str | None = None
sentry_traces_sample_rate: float = 0.0
```

### CONTRACT B — The Docker image (`deploy/Dockerfile`)

Single multi-stage Dockerfile at `deploy/Dockerfile`, build context = repo root. Builds the SPA and the server into one image. Mode chosen at runtime by `SPOTDL_MODE`. **The GHCR image self-hosters pull is byte-identical to what Railway runs** (same Dockerfile, same tag) — spec §9.

```dockerfile
# syntax=docker/dockerfile:1

# ---- Stage 1: build the web SPA (Plan 10) ----
FROM node:22-alpine AS web-builder
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate   # matches apps/web packageManager pin (Plan 10) + ci.yml
WORKDIR /w
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./apps/web/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm -C apps/web install --frozen-lockfile
COPY apps/web/ ./apps/web/
RUN pnpm -C apps/web build          # -> /w/apps/web/dist

# ---- Stage 2: resolve Python deps + build the server venv ----
FROM python:3.13-slim AS py-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /src
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY apps/server/ ./apps/server/
# SPA is embedded INTO the server package BEFORE the wheel is built, so the built
# wheel force-includes static/** (spec §8). The server wheel must ALSO package the
# alembic scripts dir (Plan 5 Hatch config) so upgrade_to_head works from the venv.
COPY --from=web-builder /w/apps/web/dist ./apps/server/src/spotdl_server/static/
# --no-editable installs a BUILT wheel (static + alembic packaged) into the venv,
# so stage 3 needs only the venv — no fragile source overlay. --extra redis for hosted.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package spotdl-server --extra redis

# ---- Stage 3: runtime ----
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r spotdl && useradd -r -g spotdl spotdl
WORKDIR /app
COPY --from=py-builder /src/.venv /app/.venv
COPY deploy/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/data && chown -R spotdl:spotdl /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SPOTDL_MODE=selfhost \
    SPOTDL_DATA_DIR=/app/data \
    SPOTDL_DATABASE_URL="sqlite+aiosqlite:////app/data/spotdl.db"
USER spotdl
EXPOSE 8000
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

**`deploy/docker-entrypoint.sh` (CONTRACT):** runs migrations then the server; migrations use the programmatic entry point, never raw `alembic`. **Migrate-on-boot is single-instance-only:** it is safe for self-host (one container) and for Railway solely because `deploy/railway.toml` pins `numReplicas = 1`. Two replicas booting concurrently would race Alembic. Anyone raising replicas must first decouple migrations — either wrap `upgrade_to_head` in a Postgres advisory lock (`pg_advisory_lock`) or move it to a separate release-phase step (Railway pre-deploy command / one-off job) and strip it from the entrypoint. This coupling is called out in the entrypoint script comment, the railway.toml comment, and `docs/self-hosting/railway.md` (Task 5).
```sh
#!/bin/sh
set -e
# Migrate-on-boot: safe only with a SINGLE instance (compose selfhost; Railway numReplicas=1).
# Raising replicas requires an advisory lock or a release-phase migration instead — see docs/self-hosting/railway.md.
python -c "from spotdl_server.bootstrap import upgrade_to_head; from spotdl_server.settings import Settings; upgrade_to_head(Settings())"
exec uvicorn --factory spotdl_server.app:create_app --host 0.0.0.0 --port "${PORT:-8000}" --no-access-log
```
(`--no-access-log`: our `RequestContextMiddleware` emits the structured access line; uvicorn's default access log is suppressed to avoid a duplicate non-JSON line.) The `--factory` target `create_app` is called with no args, valid across the Plan 5/6/7 signature evolution (`create_app(settings=None, *, registry=None)` → adds `download_engine=None`) — it constructs `Settings()` from `SPOTDL_*` env. Add `SPOTDL_DOWNLOAD_X_ACCEL_PREFIX` (Plan 7) only when a reverse proxy serves library files.

**GHCR naming & tags:** image `ghcr.io/spotdl/spotify-downloader`. Tag rules (via `docker/metadata-action`):
- push to branch `v5` → `edge`
- git tag `v5.0.0aN` (pre-release) → `5.0.0aN` + `sha-<short>`
- git tag `vX.Y.Z` (final, GA) → `X.Y.Z`, `X.Y`, `sha-<short>` (and **`latest` only at GA**, gated — see Task 3)
Multi-arch `linux/amd64,linux/arm64`. Docker Hub `spotdl/spotify-downloader` is pushed **only** by the GA-gated job (Task 3), preserving the v4 image under `legacy-v4` (retag step lives in the GA runbook, Task 12 — not executed here).

### CONTRACT C — `deploy/docker-compose.selfhost.yml` (+ optional Postgres override)

Single service + one named volume; SQLite by default; pulls the published GHCR image (with a commented `build:` for local builds). No Redis, no Postgres by default (spec §4/§6.3: one container, one volume).

```yaml
# deploy/docker-compose.selfhost.yml
# Usage: docker compose -f deploy/docker-compose.selfhost.yml up -d
# Postgres instead of SQLite: add -f deploy/docker-compose.postgres.yml
name: spotdl
services:
  spotdl:
    image: ghcr.io/spotdl/spotify-downloader:${SPOTDL_IMAGE_TAG:-edge}
    # build: { context: .., dockerfile: deploy/Dockerfile }   # uncomment to build locally
    ports:
      - "${SPOTDL_PORT:-8000}:8000"
    environment:
      SPOTDL_MODE: selfhost
      SPOTDL_DATA_DIR: /app/data
      SPOTDL_DATABASE_URL: ${SPOTDL_DATABASE_URL:-sqlite+aiosqlite:////app/data/spotdl.db}
      SPOTDL_AUTH_SECRET_KEY: ${SPOTDL_AUTH_SECRET_KEY:?set a random secret in .env}
      SPOTDL_SENTRY_DSN: ${SPOTDL_SENTRY_DSN:-}
      SPOTDL_LOG_LEVEL: ${SPOTDL_LOG_LEVEL:-INFO}
    volumes:
      - spotdl_data:/app/data
    restart: unless-stopped
volumes:
  spotdl_data:
```

**`deploy/docker-compose.postgres.yml` (override, CONTRACT):** adds a `db` service and points the app at it; enabling Postgres is opt-in and additive.
```yaml
name: spotdl
services:
  spotdl:
    environment:
      SPOTDL_DATABASE_URL: postgresql+asyncpg://spotdl:${SPOTDL_DB_PASSWORD:?}@db:5432/spotdl
    depends_on:
      db: { condition: service_healthy }
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: spotdl
      POSTGRES_PASSWORD: ${SPOTDL_DB_PASSWORD:?}
      POSTGRES_DB: spotdl
    volumes: [ spotdl_pg:/var/lib/postgresql/data ]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U spotdl"]
      interval: 10s
      timeout: 5s
      retries: 5
volumes:
  spotdl_pg:
```

**`deploy/Caddyfile.example` (CONTRACT):** reverse proxy with automatic TLS (spec §9); the removed v4 `--enable-tls` flags now terminate here (Plan 8 DROP rows point at this file).
```
spotdl.example.com {
    encode zstd gzip
    reverse_proxy localhost:8000
    # Optional: efficient large-file delivery for the downloads library.
    # Set SPOTDL_DOWNLOAD_X_ACCEL_PREFIX (Plan 7) and add a matching
    # `handle @internal { root * /app/data; file_server }` block; documented in
    # docs/self-hosting/reverse-proxy.md.
}
```

**`deploy/.env.example` (CONTRACT):** every recognized self-host var with a placeholder; `SPOTDL_AUTH_SECRET_KEY` documented as `openssl rand -hex 32`. This is the only committed env file.

### CONTRACT D — Railway config-as-code (`deploy/railway.toml`)

Config-as-code for the community instance (`hosted` mode). Railway provides the **managed Postgres** and **managed Redis** plugins; the server binds to them via reference variables (set in the Railway dashboard/service, not in the file — the file pins build/deploy behavior). The image is built from the same `deploy/Dockerfile`.

```toml
# deploy/railway.toml  — community-hosted spotDL server
[build]
builder = "DOCKERFILE"
dockerfilePath = "deploy/Dockerfile"
watchPatterns = ["apps/server/**", "apps/web/**", "packages/**", "deploy/Dockerfile"]

[deploy]
startCommand = "/app/docker-entrypoint.sh"   # migrations (upgrade_to_head) then uvicorn --factory
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
# SAFETY COUPLING: the entrypoint runs Alembic migrations on boot (CONTRACT B).
# That is only race-free because numReplicas = 1. Do NOT raise replicas without
# first moving migrations out of the entrypoint — see the note under CONTRACT D.
numReplicas = 1
```

**Railway service variables (documented in `docs/self-hosting/railway.md`, set in dashboard — NEVER committed):**
```
SPOTDL_MODE=hosted
SPOTDL_DATABASE_URL=${{Postgres.DATABASE_URL}}      # asyncpg URL; doc notes the +asyncpg driver mapping
SPOTDL_REDIS_URL=${{Redis.REDIS_URL}}               # enables RedisRateLimiter (Plan 6)
SPOTDL_RATE_LIMIT_ENABLED=true
SPOTDL_AUTH_SECRET_KEY=<openssl rand -hex 32>
SPOTDL_SPOTIFY_CLIENT_ID=<operator>
SPOTDL_SPOTIFY_CLIENT_SECRET=<operator>
SPOTDL_SENTRY_DSN=<optional>
SPOTDL_LOG_LEVEL=INFO
SPOTDL_CLIENT_IP_HEADER=cf-connecting-ip   # trust Cloudflare's client-IP header for rate limiting + logs
```
Promotion path (documented, not automated here): **staging** Railway environment first (own DB/Redis), smoke `/api/v1/health` + `/metrics`, then promote the same image tag to **production** environment. Cloudflare sits in front of the production domain (proxied DNS, cache rules exclude `/api/*`, WAF/rate-rules complement the app's Redis limiter). The rate limiter's Redis backend is enabled purely by presence of `SPOTDL_REDIS_URL` (+ `redis` extra baked into the hosted image via `uv sync --extra redis` — see Task 5).

### CONTRACT E — Release workflows (`.github/workflows/`)

**E1 — `release-pypi.yml` (Trusted Publishing, dependency-ordered).** Trigger: `release: [published]` (GitHub Release created on a `vX.Y.Z` / `v5.0.0aN` tag) + `workflow_dispatch`. Three sequential jobs so PyPI dependency resolution never sees a missing pin (`spotdl` needs `spotdl-server`, which needs `spotdl-core`):
```yaml
name: Release to PyPI
on:
  release: { types: [published] }
  workflow_dispatch:
jobs:
  core:
    runs-on: ubuntu-latest
    environment: pypi
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build --package spotdl-core --out-dir dist
      - uses: pypa/gh-action-pypi-publish@release/v1
        with: { packages-dir: dist }
  server:
    needs: core
    runs-on: ubuntu-latest
    environment: pypi
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      # SPA must be embedded before building the server wheel (spec §8)
      - uses: pnpm/action-setup@v4
        with: { version: "11.10.0" }     # the one pnpm pin (Plan 10 packageManager + ci.yml)
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: make bundle-spa            # builds apps/web, copies dist into spotdl_server/static
      - run: uv build --package spotdl-server --out-dir dist
      - uses: pypa/gh-action-pypi-publish@release/v1
        with: { packages-dir: dist }
  cli:
    needs: server
    runs-on: ubuntu-latest
    environment: pypi
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build --package spotdl --out-dir dist
      - uses: pypa/gh-action-pypi-publish@release/v1
        with: { packages-dir: dist }
```
Pre-release flow: tag `v5.0.0a1` → the three projects publish `5.0.0a1`; `pip install spotdl` keeps serving 4.x (PEP 440 pre-release exclusion) until GA `5.0.0`. No API tokens: each PyPI project (`spotdl-core`, `spotdl-server`, `spotdl`) is configured with this repo + `release-pypi.yml` + environment `pypi` as a Trusted Publisher. **No PyPI-propagation race:** each job builds its wheel from **local workspace sources** (`uv build` resolves `{workspace = true}` deps from the checkout), so no build step ever needs a just-published package to be visible on PyPI; the core→server→cli ordering exists only so that by the time `spotdl` is installable, its `==`-pinned dependencies already exist on the index.

**E2 — `release-docker.yml` (GHCR always; Docker Hub GA-gated).** Trigger: push to `v5`, tags `v*`, `workflow_dispatch`. Uses `docker/setup-qemu-action`, `docker/setup-buildx-action`, `docker/metadata-action` (tag rules per CONTRACT B), builds `deploy/Dockerfile` multi-arch `linux/amd64,linux/arm64`, pushes to GHCR (login with `GITHUB_TOKEN`). A **separate job `dockerhub`** with `if: startsWith(github.ref, 'refs/tags/v') && !contains(github.ref, 'a')` (final tags only) logs into Docker Hub with `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` and pushes `spotdl/spotify-downloader`; `latest` is applied only here. `legacy-v4` retag is a manual GA-runbook step (Task 12).

**E3 — `release-binaries.yml` (PyInstaller matrix).** Trigger: `release: [published]`, `workflow_dispatch`. Matrix `ubuntu-latest`, `macos-latest`, `windows-latest`; a separate `build-arm` job builds `linux/aarch64` via `uraimo/run-on-arch-action@v3` (mirrors v4). Each job runs `make bundle-spa` (binary embeds the SPA) then `uv run python scripts/build_binary.py`, uploads artifacts to the GitHub Release via `softprops/action-gh-release@v2`. Binary smoke test (see CONTRACT G) runs before upload.

**E4 — `docs.yml` (gh-pages).** Trigger: push to `v5` touching `docs/**` / `mkdocs.yml` / generator scripts / `apps/server/openapi.json`, + `workflow_dispatch`. `uv sync --group docs`, then `uv run mkdocs gh-deploy --force`. The build regenerates the migration guide and copies Plan 5's `apps/server/openapi.json` into the site (CONTRACT F); a drift-check job runs `make docs-check` (migration-guide drift; the OpenAPI artifact is already drift-guarded by Plan 5's in-sync test in the `python` job) and fails if stale.

### CONTRACT F — Docs site (`mkdocs.yml` nav + generators)

mkdocs-material. Generated content is produced by pinned scripts run via `mkdocs-gen-files` at build time (like v4's `gen_ref_nav.py`), and also committed + drift-checked in CI.

**`mkdocs.yml` nav (CONTRACT):**
```yaml
site_name: spotDL
site_url: https://spotdl.github.io/spotify-downloader
repo_url: https://github.com/spotDL/spotify-downloader
theme:
  name: material
  features: [navigation.tabs, navigation.sections, navigation.top, content.code.copy, content.code.annotate]
plugins:
  - search
  - gen-files: { scripts: [scripts/docs/gen_migration_guide.py, scripts/docs/copy_openapi.py] }
  - swagger-ui-tag        # renders api/openapi.json (copied from apps/server/openapi.json; self-contained, no external CDN at runtime)
nav:
  - Home: index.md
  - Installation: installation.md
  - Quickstart:
      - CLI: quickstart/cli.md
      - Web UI: quickstart/web.md
      - Self-hosting: quickstart/selfhost.md
  - Community server:
      - Usage: community/usage.md
      - Etiquette & fair use: community/etiquette.md
  - Self-hosting:
      - Docker & Compose: self-hosting/docker.md
      - Caddy / reverse proxy: self-hosting/reverse-proxy.md
      - Railway: self-hosting/railway.md
      - Backups & restore: self-hosting/backups.md
  - Migrating from v4: migration/v4-to-v5.md     # GENERATED (gen_migration_guide.py)
  - API reference: api/index.md                  # Swagger UI over Plan 5's apps/server/openapi.json (SELFHOST = full surface)
  - Contributing: contributing.md
```

**`scripts/docs/gen_migration_guide.py` (CONTRACT — pinned generator):** imports `spotdl_cli`'s `V4_FLAG_TABLE` and the `.spotdl` v4→v2 field table (Plan 8) and renders `migration/v4-to-v5.md`: an intro, a **flag table** (columns: v4 flag · kind · v5 form / pointer) grouped by row-kind (SAME/RENAME/SOFT-DROP/DROP), the verbatim `--playlist-retain-track-cover` behavior-gap note, and the `.spotdl` auto-migration section. **Single source of truth** — the guide is never hand-edited. Under `mkdocs-gen-files` it writes into the virtual docs tree; a standalone `--check` mode (used by CI + a `make docs-check` target) writes to `docs/migration/v4-to-v5.md` and fails if the committed file differs (drift guard, mirroring Plan 8's client in-sync guard).

**`scripts/docs/copy_openapi.py` (CONTRACT — thin gen-files shim, NOT a second generator):** the OpenAPI reference **reuses Plan 5's committed build artifact** `apps/server/openapi.json` — which Plan 5 Task 11 generates via `apps/server/scripts/export_openapi.py` with `Settings(mode=DeploymentMode.SELFHOST)` (verified: SELFHOST is the full surface, downloads/queue endpoints included; deterministic `sort_keys=True` output; guarded by Plan 5's `test_openapi_in_sync` + `--check`). This shim only copies that file into the virtual docs tree as `api/openapi.json` at mkdocs build time. There is deliberately **no** `scripts/docs/export_openapi.py` and no second drift guard — one exporter, one committed artifact, one in-sync test (Plan 5's). `api/index.md` is a stub embedding `<swagger-ui src="../openapi.json"/>`.

### CONTRACT G — PyInstaller binary (`scripts/build_binary.py`, default action = TUI)

Ports v4's `scripts/build.py` to the v5 layout. The binary bundles the **server + embedded SPA + CLI** (the CLI runs the server in-process for offline use, spec §7). Entry point is `spotdl_cli.__main__:main`; because the CLI's bare-TTY behavior already launches the TUI (Plan 8: "`spotdl` in a TTY → `tui`"), the **binary's default action is the TUI** with no extra flag (spec §12.7). ffmpeg is NOT bundled; first run offers `spotdl ffmpeg download` (Plan 8 Task 11).

```python
# scripts/build_binary.py  (CONTRACT — shape)
import os, sys
from pathlib import Path
import PyInstaller.__main__
from spotdl_cli import __version__            # single-sourced version
import spotdl_server
STATIC = Path(spotdl_server.__file__).parent / "static"     # embedded SPA (must exist: run `make bundle-spa` first)
assert STATIC.is_dir(), "run `make bundle-spa` before building the binary"
PyInstaller.__main__.run([
    "apps/cli/src/spotdl_cli/__main__.py",
    "--onefile", "--console",                                # console app; bare invocation still launches the TUI
    "--name", f"spotdl-{__version__}-{sys.platform}",
    "--add-data", f"{STATIC}{os.pathsep}spotdl_server/static",
    "--collect-all", "spotdl_server", "--collect-all", "spotdl_core",
    "--collect-submodules", "yt_dlp",
])
```
**Binary smoke test (runs in `release-binaries.yml` before upload):** execute the built binary as `spotdl --version` (exits 0, prints the version) and `spotdl web --help` (proves the embedded server + SPA path imports). A TTY-less run of bare `spotdl` must NOT hang (falls back to help/non-interactive), asserted in the CLI's own tests (Plan 8/9) and referenced here.

### CONTRACT H — Version single-source (`scripts/bump_version.py`)

One command sets the version across all three published packages so dependency-ordered publishing always agrees.
```python
# scripts/bump_version.py <version>   (CONTRACT)
# Writes [project].version in: apps/cli/pyproject.toml, apps/server/pyproject.toml, packages/core/pyproject.toml
# and __version__ in each package's src __init__.py. Refuses non-PEP-440 versions.
# `--check` mode: assert all SIX locations (3 pyproject [project].version + 3 __init__ __version__) agree, else exit 1 (CI guard).
```
CI adds a `version-consistency` step (`uv run python scripts/bump_version.py --check`) to the existing `python` job's tail (additive, keeps it green).

### CONTRACT I — Backup & restore runbook (`deploy/backup/`)

Nightly `pg_dump` of the hosted Postgres to object storage, run by a **Railway cron service** (spec §9). Self-hosters on SQLite copy the volume; the doc covers both.
```sh
# deploy/backup/backup.sh   (CONTRACT — runs on the Railway backup cron service)
set -euo pipefail
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="spotdl-${STAMP}.sql.gz"
pg_dump "${SPOTDL_DATABASE_URL_PSQL:?}" | gzip > "/tmp/${FILE}"     # libpq URL (no +asyncpg)
rclone copyto "/tmp/${FILE}" "${SPOTDL_BACKUP_REMOTE:?}/${FILE}"    # remote configured via env (R2/S3)
rclone delete --min-age "${SPOTDL_BACKUP_RETENTION:-30d}" "${SPOTDL_BACKUP_REMOTE}"   # retention
```
Railway backup service (documented, added as a second service in the same project): image with `postgresql-client` + `rclone`, `cronSchedule = "0 3 * * *"`, no healthcheck, restart never. `deploy/backup/restore.sh` streams a chosen dump back into a target DB. **Restore drill (documented, quarterly):** pull the latest dump into a throwaway Railway/Postgres, `restore.sh`, boot the image against it, `curl /api/v1/health` + one `POST /resolve`, record the result in the runbook. Object-storage creds live in Railway env only.

---

## Files produced by this plan

```
deploy/
├─ Dockerfile                       [CONTRACT B]
├─ docker-entrypoint.sh             [CONTRACT B]
├─ docker-compose.selfhost.yml      [CONTRACT C]
├─ docker-compose.postgres.yml      [CONTRACT C]
├─ Caddyfile.example                [CONTRACT C]
├─ .env.example                     [CONTRACT C]
├─ railway.toml                     [CONTRACT D]
└─ backup/{backup.sh,restore.sh,README.md}   [CONTRACT I]
apps/server/src/spotdl_server/
├─ observability/{__init__.py,logging.py,metrics.py,middleware.py,sentry.py}   [CONTRACT A]
├─ app.py                           (edited: wire observability — CONTRACT A5)
├─ settings.py                      (edited: +log_level, metrics_enabled, sentry_dsn, sentry_traces_sample_rate)
└─ static/                          (build artifact: embedded SPA; gitignored, produced by `make bundle-spa`)
docs/
├─ mkdocs.yml is at repo root; docs/ holds: index.md, installation.md,
│  quickstart/{cli,web,selfhost}.md, community/{usage,etiquette}.md,
│  self-hosting/{docker,reverse-proxy,railway,backups}.md, contributing.md,
│  migration/v4-to-v5.md (GENERATED), api/index.md (openapi.json is copied at build
│  time from Plan 5's committed apps/server/openapi.json — not committed twice)
mkdocs.yml                          [CONTRACT F]
scripts/
├─ build_binary.py                  [CONTRACT G]
├─ bump_version.py                  [CONTRACT H]
└─ docs/{gen_migration_guide.py,copy_openapi.py}   [CONTRACT F]
.github/workflows/
├─ release-pypi.yml                 [CONTRACT E1]
├─ release-docker.yml               [CONTRACT E2]
├─ release-binaries.yml             [CONTRACT E3]
├─ docs.yml                         [CONTRACT E4]
└─ ci.yml                           (edited: +docker-smoke, +compose-smoke, +docs-check, +version-consistency jobs)
.github/ISSUE_TEMPLATE/             (bug/feature/self-host + config.yml → Discord)
README.md                           (rewritten for v5)
Makefile                            (edited: +bundle-spa, +docs, +docs-check targets)
docs/superpowers/runbooks/ga-cutover.md    [Task 12 — documented, NOT executed]
```

---

## Tasks

### Task 1: Observability — structlog JSON logs, `/metrics`, correlation-id middleware, optional Sentry (TDD)

**Files:** Create `apps/server/src/spotdl_server/observability/{__init__,logging,metrics,middleware,sentry}.py`; edit `settings.py` (4 new fields), `app.py` (CONTRACT A5), `apps/server/pyproject.toml` (deps: `structlog`, `prometheus-client`; optional extra `sentry = ["sentry-sdk>=2"]`). Create tests under `apps/server/tests/observability/`.

**Interfaces:** Produces CONTRACT A surface (log schema, `/metrics`, increment helpers, middleware, Sentry init). Consumes Plan 5 `create_app`, `Settings`.

- [ ] **Step 1 (RED):** Tests: (a) `configure_logging` emits one JSON line per record with fields `ts, level, event, logger, mode` (capture stdout, parse JSON); secrets never appear. (b) A request through `httpx.ASGITransport` yields an access-log line with `request_id, method, path (template), status_code, duration_ms` and the response carries `X-Request-ID`; an inbound `X-Request-ID` is echoed; a malformed one is replaced. (c) `GET /metrics` returns 200 `text/plain` and contains every metric name from CONTRACT A2; the `spotdl_http_requests_total` counter increments after a request; `path` label is the route template, not the concrete id. (d) increment helpers move their metrics; `set_resolve_queue_depth`/`set_download_queue_depth` default 0. (e) `init_sentry` is a no-op without `sentry_dsn` and does not import `sentry_sdk` at module import. (f) `metrics_enabled=False` unmounts `/metrics` (404).
- [ ] **Step 2 (GREEN):** Implement per CONTRACT A. Route stdlib logging (uvicorn/sqlalchemy) through structlog via `dictConfig`. Use the default prometheus registry; guard against double-registration under repeated `create_app` in tests (module-level metric objects created once at import — safe).
- [ ] **Step 3:** Wire `create_app` (A5). Add `--no-access-log` note is in the entrypoint (Task 2), not here.
- [ ] **Step 4:** `make check` green. Verify manually: `uv run uvicorn --factory spotdl_server.app:create_app` then `curl -s localhost:8000/metrics | grep spotdl_` shows the metric names and `curl -sD- localhost:8000/api/v1/health` shows `x-request-id`.

**Instrumentation note:** wiring the helpers into resolve/provider/queue/match seams happens in this task where those seams already exist (Plans 5/6/7 are merged before Plan 11); where a seam is absent, add the call behind the same function boundary and leave the gauge at 0 with a test. Do NOT restructure services.

### Task 2: Docker image (multi-stage, SPA-embedding) + `make bundle-spa` + local boot verification

**Files:** Create `deploy/Dockerfile`, `deploy/docker-entrypoint.sh`; edit `Makefile` (+`bundle-spa`: `pnpm -C apps/web build && rm -rf apps/server/src/spotdl_server/static && cp -r apps/web/dist apps/server/src/spotdl_server/static`); edit `.gitignore` (ignore `apps/server/src/spotdl_server/static/`); edit `apps/server/pyproject.toml` (package-data / force-include `static/**` in the wheel; add `redis` extra usage note). Delete stale root `Dockerfile`, `docker-compose*.yml`, `railway.toml`, `nginx/` (anti-pattern scaffolding).

**Interfaces:** Produces CONTRACT B. Consumes `bootstrap.upgrade_to_head`, `create_app`, Plan 10 web build.

- [ ] **Step 1:** Write `make bundle-spa`; confirm it populates `spotdl_server/static/index.html`.
- [ ] **Step 2:** Write `deploy/Dockerfile` + entrypoint per CONTRACT B.
- [ ] **Step 3 (verify):** `docker build -f deploy/Dockerfile -t spotdl:test .` then `docker run -d -e SPOTDL_AUTH_SECRET_KEY=x -p 8000:8000 spotdl:test`; poll `curl -fsS localhost:8000/api/v1/health` → `{"status":"ok"}`; `curl -s localhost:8000/` returns the SPA `index.html`; `curl -s localhost:8000/metrics | grep spotdl_http_requests_total`. Confirm the container runs as non-root (`docker exec … id -u` ≠ 0) and migrations ran (logs show `upgrade_to_head`).
- [ ] **Step 4:** `make check` still green (SPA static dir gitignored; no Python import of it required for tests).
- [ ] **Step 5 (pnpm pin consistency):** assert ONE pnpm version everywhere: `apps/web/package.json` `"packageManager": "pnpm@11.10.0"` (Plan 10 Task 1 — if Plan 10 hasn't landed it yet, add it here), ci.yml `web` job `pnpm/action-setup` `version: "11.10.0"` (already so — leave it), this Dockerfile's corepack line, and the E1 server job. `grep -rn 'pnpm' .github/workflows deploy/Dockerfile apps/web/package.json` shows only `11.10.0`.

### Task 3: GHCR + Docker Hub publish workflow (multi-arch; Docker Hub GA-gated)

**Files:** Create `.github/workflows/release-docker.yml` (CONTRACT E2).

- [ ] **Step 1:** GHCR job: `metadata-action` tag rules (edge / pre-release / GA + `latest` gated), buildx multi-arch, push to `ghcr.io/spotdl/spotify-downloader`, login via `GITHUB_TOKEN` (`permissions: packages: write`).
- [ ] **Step 2:** Docker Hub job guarded to final tags only, secrets `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN`, pushes `spotdl/spotify-downloader` incl. `latest`.
- [ ] **Step 3 (verify):** `actionlint .github/workflows/release-docker.yml` clean; dry-run the metadata step logic locally with `docker/metadata-action`'s documented examples (assert `edge` on branch, `5.0.0a1` on a pre-release tag, `latest` NOT emitted on a pre-release tag). No push on PRs.

### Task 4: Self-host compose + Postgres override + Caddy + `.env.example` + CI compose smoke

**Files:** Create `deploy/docker-compose.selfhost.yml`, `deploy/docker-compose.postgres.yml`, `deploy/Caddyfile.example`, `deploy/.env.example` (CONTRACT C). Edit `.github/workflows/ci.yml` (+`compose-smoke` job).

- [ ] **Step 1:** Write the compose files + Caddy + env example per CONTRACT C.
- [ ] **Step 2 (verify):** locally, `SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32) docker compose -f deploy/docker-compose.selfhost.yml up -d --build`; poll health; then bring up the Postgres overlay (`-f … -f deploy/docker-compose.postgres.yml`) and confirm health with `SPOTDL_DATABASE_URL` pointing at `db`.
- [ ] **Step 3:** `compose-smoke` CI job: build the image, `docker compose -f deploy/docker-compose.selfhost.yml up -d`, wait-for-health loop against `/api/v1/health`, `curl` `/metrics`, then tear down. Keep it a separate job (does not gate the existing `python`/`web` jobs).
- [ ] **Step 4:** `actionlint` clean; `make check` unaffected.

### Task 5: Railway config-as-code + Redis rate-limit wiring + Cloudflare notes + deployment doc

**Files:** Create `deploy/railway.toml` (CONTRACT D); create `docs/self-hosting/railway.md`. Edit `deploy/Dockerfile` or the server build so the **hosted image includes the `redis` extra** (e.g. `uv sync --frozen --no-dev --package spotdl-server --extra redis`) — the same image self-hosters pull, redis unused unless `SPOTDL_REDIS_URL` set.

- [ ] **Step 1:** Write `deploy/railway.toml`. Document every service variable (values in dashboard only), the `${{Postgres.DATABASE_URL}}`/`${{Redis.REDIS_URL}}` reference vars and the `+asyncpg` driver mapping note, and the staging→production promotion path. `docs/self-hosting/railway.md` MUST include the **migrate-on-boot ⟷ `numReplicas = 1` coupling** (CONTRACT B/D): scaling beyond one replica requires wrapping `upgrade_to_head` in a Postgres advisory lock or moving migrations to a release-phase/pre-deploy step first.
- [ ] **Step 2:** Document Cloudflare: proxied DNS, bypass-cache for `/api/*` and `/metrics`, WAF/rate rules complementing the app limiter, and that TLS is terminated at Cloudflare→Railway (Caddy is the self-host alternative).
- [ ] **Step 3:** Note the community-server go-live gate: it must be live in `hosted` mode with Postgres+Redis before GA (spec §12.8) — referenced by the GA runbook (Task 12) and Task 6.
- [ ] **Step 4 (verify):** `railway.toml` parses (documented `railway up --detach` dry note; not executed in CI). Confirm `redis` importable inside the built image (`docker run … python -c "import redis"`).

### Task 6: Pin the CLI default `api_url` — THE PLAN'S ONLY HUMAN-INPUT GATE

**Files:** Edit `apps/cli/src/spotdl_cli/transport.py` (replace the Plan 8 placeholder `DEFAULT_API_URL`); edit/confirm the CLI config default; add a CLI test asserting the default is HTTPS and is not localhost.

> **⚠️ HUMAN-INPUT GATE (the only one in this plan).** The value is the **community server's public domain** chosen by the operator (spec §12.8: "the CLI default `api_url` points at it … must not ship as a localhost stub"). The implementer MUST obtain the final domain from the human before completing this task. Parameterize as `SPOTDL_COMMUNITY_URL` for discussion; the pinned constant is e.g. `https://api.spotdl.io` (placeholder — **confirm with the human**). Blocking check: the task is NOT done until a real HTTPS domain is committed. Everything else in this plan proceeds without human input.

- [ ] **Step 1:** Confirm the domain with the human (this is the gate). It must match the Cloudflare-fronted Railway production domain from Task 5.
- [ ] **Step 2:** Replace the placeholder; the default is overridable via config/env (Plan 8 precedence: CLI > env > file > default) but the shipped default is the real HTTPS URL.
- [ ] **Step 3 (test):** assert `DEFAULT_API_URL.startswith("https://")` and `"localhost" not in DEFAULT_API_URL` and `"127.0.0.1" not in DEFAULT_API_URL`; assert `--offline`/config override still wins.
- [ ] **Step 4:** `make check` green.

### Task 7: Docs site — mkdocs-material, generated migration guide + OpenAPI reference, drift guards

**Files:** Create `mkdocs.yml` (CONTRACT F); `scripts/docs/gen_migration_guide.py`, `scripts/docs/copy_openapi.py`; the hand-written docs pages listed in the layout (index, installation, quickstart×3, community×2, self-hosting×4, contributing); `docs/migration/v4-to-v5.md` (generated, committed) + `docs/api/index.md`. Edit root `pyproject.toml` (add `docs` dependency-group: `mkdocs-material`, `mkdocs-gen-files`, `mkdocs-swagger-ui-tag`), `Makefile` (+`docs`, +`docs-check`). Create `.github/workflows/docs.yml` (CONTRACT E4).

- [ ] **Step 1:** Write `gen_migration_guide.py` per CONTRACT F with its `--check` drift mode: imports `spotdl_cli`'s `V4_FLAG_TABLE` + `.spotdl` field table; render includes the verbatim `--playlist-retain-track-cover` gap note. Write `copy_openapi.py`: a thin `mkdocs-gen-files` shim copying **Plan 5's committed `apps/server/openapi.json`** (generated in SELFHOST mode = full surface incl. downloads; kept in sync by Plan 5's `test_openapi_in_sync`) into the docs tree — do NOT add a second exporter or drift guard.
- [ ] **Step 2:** Write `mkdocs.yml` nav + the hand-written pages. `community/etiquette.md` covers fair use of the shared instance (cache-first, rate limits, self-host for heavy use); `quickstart/selfhost.md` + `self-hosting/*` reference the `deploy/` artifacts; `self-hosting/backups.md` embeds CONTRACT I.
- [ ] **Step 3 (verify):** `uv run mkdocs build --strict` succeeds (no broken links/nav). `make docs-check` (runs `gen_migration_guide.py --check`; the OpenAPI artifact is covered by Plan 5's `test_openapi_in_sync`) passes on the committed files.
- [ ] **Step 4:** `docs.yml`: build + drift-check job + `mkdocs gh-deploy --force` on `v5`. `actionlint` clean.

### Task 8: PyInstaller binary build script + matrix workflow + binary smoke test

**Files:** Create `scripts/build_binary.py` (CONTRACT G); create `.github/workflows/release-binaries.yml` (CONTRACT E3). Edit `apps/cli/pyproject.toml` or a `dev`/`build` group to include `pyinstaller`.

- [ ] **Step 1:** Port v4's `build.py` to the v5 layout (CONTRACT G): entry `spotdl_cli/__main__.py`, `--collect-all spotdl_server spotdl_core`, embed the SPA `--add-data`, require `make bundle-spa` first, name `spotdl-{version}-{platform}`.
- [ ] **Step 2 (verify locally):** `make bundle-spa && uv run python scripts/build_binary.py`; run `./dist/spotdl-* --version` (exit 0) and `./dist/spotdl-* web --help`.
- [ ] **Step 3:** `release-binaries.yml`: matrix (ubuntu/macos/windows) + `build-arm` (aarch64 via `run-on-arch-action`), each runs bundle-spa → build → smoke → `action-gh-release` upload. Trigger on release + `workflow_dispatch`.
- [ ] **Step 4:** `actionlint` clean.

### Task 9: PyPI trusted-publishing workflow + version single-source + CI version guard

**Files:** Create `.github/workflows/release-pypi.yml` (CONTRACT E1); `scripts/bump_version.py` (CONTRACT H). Edit `ci.yml` (+`version-consistency` step). Confirm each package `pyproject.toml` declares real version pins for its workspace deps at build time (uv resolves `{workspace=true}` to the pinned version in built wheels — verify the built `spotdl-server` wheel requires `spotdl-core==<ver>` and `spotdl` requires `spotdl-server==<ver>`).

- [ ] **Step 1:** Write `bump_version.py` (writes 3 pyprojects + 3 `__version__`; `--check`). Run it to set `5.0.0a1` as the first pre-release across all packages.
- [ ] **Step 2 (verify pins):** `uv build --package spotdl-server` then inspect the wheel METADATA: `Requires-Dist: spotdl-core==5.0.0a1`. Same for `spotdl` → `spotdl-server==5.0.0a1`. This is what makes the dependency-ordered publish correct.
- [ ] **Step 3:** Write `release-pypi.yml` (core→server→cli, `environment: pypi`, `id-token: write`, server job runs `make bundle-spa`).
- [ ] **Step 4:** Add `version-consistency` (`bump_version.py --check`) to the `python` job. `actionlint` clean; `make check` green. Document the PyPI Trusted-Publisher config steps (per project) in `docs/contributing.md` (release section) — configured in PyPI UI, no secret.

### Task 10: Nightly backup + restore runbook

**Files:** Create `deploy/backup/{backup.sh,restore.sh,README.md}` (CONTRACT I). Document the Railway backup cron service in `docs/self-hosting/backups.md` (extend from Task 7).

- [ ] **Step 1:** Write `backup.sh` (pg_dump | gzip | rclone upload + retention) and `restore.sh` (download + gunzip | psql into a target DB). `shellcheck` clean.
- [ ] **Step 2:** Document the Railway cron service (postgres-client + rclone image, `cronSchedule="0 3 * * *"`, env-provided remote+creds), the libpq vs `+asyncpg` URL distinction (`SPOTDL_DATABASE_URL_PSQL`), retention, and the SQLite self-host alternative (volume copy).
- [ ] **Step 3:** Document the quarterly restore drill (restore into a throwaway DB, boot image, `curl /api/v1/health` + one `POST /resolve`, record outcome) as a checklist.
- [ ] **Step 4 (verify):** `bash -n deploy/backup/*.sh` and `shellcheck deploy/backup/*.sh` pass.

### Task 11: v5 README rewrite + repo housekeeping (issue templates → Discord, badges)

**Files:** Rewrite `README.md`; create `.github/ISSUE_TEMPLATE/{bug_report.yml,feature_request.yml,self_hosting.yml,config.yml}`. Optionally `.github/PULL_REQUEST_TEMPLATE.md`.

- [ ] **Step 1:** README: what v5 is (server + CLI/TUI + web), install (`pip install spotdl` post-GA; pre-release `pip install --pre spotdl`), quickstart, community-server + self-host pointers, badges (PyPI, Docker, docs, Discord), and a prominent "migrating from v4" link. State clearly that stable v4 remains on `master` until GA.
- [ ] **Step 2:** Issue templates as GitHub `.yml` forms; `config.yml` with `blank_issues_enabled: false` and a `contact_links` entry pointing at the Discord (mirrors v4's practice of routing support to Discord).
- [ ] **Step 3 (verify):** YAML lints; links resolve; `mkdocs build --strict` unaffected (README not in nav unless included).

### Task 12: GA-cutover release checklist runbook (DOCUMENTED — NOT executed)

**Files:** Create `docs/superpowers/runbooks/ga-cutover.md`.

- [ ] **Step 1:** Write the ordered GA runbook, each step with the exact command and owner, explicitly NOT run in this plan:
  1. Community server confirmed live in `hosted` mode on Railway production behind Cloudflare (health + `/metrics` green); CLI `DEFAULT_API_URL` already pointing at it (Task 6).
  2. Final `git tag vX.Y.Z` → triggers `release-pypi.yml` (core→server→cli publish `5.0.0`), `release-docker.yml` GA job (GHCR + Docker Hub `latest`), `release-binaries.yml`.
  3. Docker Hub: retag the existing v4 image `legacy-v4` **before** `latest` flips (documented `docker buildx imagetools create` / pull-retag-push commands), so v4 users pin `legacy-v4`.
  4. `master` branch swap: v4 tree preserved (already in `spotdl-v4-reference/` + git history/tag `v4-final`), then v5 becomes the default branch (or `v5` merged into `master`) — with the exact `git`/GitHub-settings steps and a rollback note.
  5. Docs: `docs.yml` deploy of the v5 site; verify the migration guide renders.
  6. Post-cutover smoke: fresh `pip install spotdl` (no `--pre`) gets 5.0.0; `docker pull spotdl/spotify-downloader:latest` boots; binary from the release runs.
- [ ] **Step 2:** Include a rollback section (yank a bad PyPI release / repoint Docker `latest` / revert branch swap) and the secret/permissions preconditions (PyPI trusted publishers configured, Docker Hub secrets present, Railway prod healthy).
- [ ] **Step 3 (verify):** Doc-only; `mkdocs build --strict` (if linked) and markdown lint pass. No commands executed.

---

## Self-review (against spec §9/§12 + the plan requirements)

**Spec §9 (community hosting & ops) coverage:**
- Railway server + managed Postgres + Redis → Task 5 (CONTRACT D; reference vars). ✓
- Cloudflare in front → Task 5 Step 2. ✓
- GHCR image byte-identical to Railway → same `deploy/Dockerfile` used by both (CONTRACT B/D); Tasks 2/3/5. ✓
- `deploy/docker-compose.selfhost.yml` single service + volume + optional Postgres override → Task 4 (CONTRACT C). ✓
- Caddy TLS example → Task 4 (CONTRACT C). ✓
- Structured JSON logs → Task 1 (CONTRACT A1). ✓
- Prometheus `/metrics` with request rates, cache hit ratio, provider error rates, resolve queue depth, matcher version distribution → Task 1 (CONTRACT A2, all five named + http/download extras). ✓
- Optional Sentry via env → Task 1 (CONTRACT A4, `SPOTDL_SENTRY_DSN`). ✓
- Nightly Postgres backups to object storage → Task 10 (CONTRACT I). ✓
- Matcher A/B note → `spotdl_matches_served_total{matcher_version}` metric (CONTRACT A2) surfaces the version distribution the hosted A/B compares; the A/B *promotion mechanism* is server-side (Plan 6, versioned weights) — observability for it lands here. ✓ (mechanism itself deferred to its owning plan, not this one)

**Spec §12 (migration & release) coverage:**
- PyPI `5.0.0aN` pre-releases → GA on `spotdl` → Task 9 (CONTRACT E1; pre-release flow noted). ✓
- Docker Hub switch with `legacy-v4` tag → Task 3 (GA-gated push) + Task 12 (retag runbook step, not executed). ✓
- Docs site rewrite + migration guide generated from shim table → Task 7 (CONTRACT F, `gen_migration_guide.py` imports `V4_FLAG_TABLE`). ✓
- PyInstaller binaries defaulting to TUI → Task 8 (CONTRACT G; bare TTY → TUI via Plan 8/9 behavior). ✓
- Community server live before GA → Task 5 Step 3 + Task 12 Step 1 (gate). ✓
- CLI default `api_url` pinned, never localhost → Task 6 (the single human-input gate; HTTPS + non-localhost test). ✓

**Requirements checklist:**
- Verbatim CONTRACT blocks for every required item: Docker image (B), compose selfhost + postgres override (C), observability log schema + metrics list (A), Railway config (D), release workflow YAMLs (E1–E4), docs nav + generated migration guide with pinned script (F), backup/ops runbook (I), plus PyInstaller (G) and version single-source (H). ✓
- Secrets never in repo; each secret's home stated → Secrets Location table + per-task notes. ✓
- CI additions are new jobs (`docker-smoke`/`compose-smoke`/`docs-check`/`version-consistency`); existing `python`/`web` jobs stay green. ✓
- The single human-input gate (community domain) is clearly and singularly marked (Task 6, ⚠️ block). Every other value is pinned or parameterized with a concrete default. ✓
- No TBDs elsewhere: the only unresolved value is the domain in Task 6, by design. ✓
- Every §9/§12 item is mapped to a task or explicitly deferred to the GA runbook (Docker Hub `latest` flip, `legacy-v4` retag, `master` swap → Task 12, documented not executed). ✓
- TDD where testable (Task 1 observability is full RED→GREEN); verification commands for infra config (Tasks 2–12 use build/boot/curl/actionlint/shellcheck/`mkdocs --strict`). ✓
- Established conventions: worktree `~/Projects/xnetcat/spotdl-v5`, commit trailer, `make check` green per code task. ✓

**Deferred (with reason):** Matcher A/B promotion logic (owned by the matching/community plans; this plan provides its observability). The GA cutover actions themselves (Task 12 is the runbook, executed by a human at release time). Web UI page work (Plan 10; this plan only packages the built SPA).

## Task summary

1. **Observability (TDD):** structlog JSON logs, `/metrics` with the 7 named metrics + increment helpers, correlation-id request middleware, optional Sentry; wired in `create_app`.
2. **Docker image:** single multi-stage `deploy/Dockerfile` (SPA-embedding, non-root, migrations-on-boot via `upgrade_to_head`), `make bundle-spa`; delete stale root scaffolding; boot-and-curl verification.
3. **GHCR/Docker Hub workflow:** multi-arch GHCR on branch/tags (`edge`/pre-release/GA), Docker Hub `latest` GA-gated.
4. **Compose + Caddy + env:** `docker-compose.selfhost.yml` (+ Postgres override), `Caddyfile.example`, `.env.example`, CI compose smoke.
5. **Railway:** `railway.toml`, Redis rate-limit wiring (`redis` extra + `SPOTDL_REDIS_URL`), Cloudflare notes, staging→prod promotion doc.
6. **CLI default api_url — SINGLE HUMAN-INPUT GATE:** pin the community HTTPS domain; test it is never localhost.
7. **Docs site:** mkdocs-material nav; migration guide GENERATED from Plan 8's `V4_FLAG_TABLE` (drift-guarded); OpenAPI reference reusing Plan 5's committed SELFHOST `apps/server/openapi.json`; gh-pages workflow.
8. **PyInstaller:** `build_binary.py` (bundles server+SPA; bare TTY → TUI default), matrix + aarch64 workflow, binary smoke test.
9. **PyPI publishing:** trusted publishing, dependency-ordered core→server→cli, `bump_version.py` single-source + CI version guard.
10. **Backups:** nightly Railway pg_dump→object-storage cron, restore script, quarterly restore-drill runbook.
11. **README + housekeeping:** v5 README, badges, issue templates routing support to Discord.
12. **GA-cutover runbook (documented, NOT executed):** Docker Hub `latest` switch, `legacy-v4` retag, `master` swap, rollback + preconditions.

Draft path: `/Users/xnetcat/Projects/xnetcat/spotify-downloader/.superpowers/sdd/plan-11-draft.md`
