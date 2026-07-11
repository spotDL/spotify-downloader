# Deploying the community server on Railway

The community-hosted spotDL instance runs in **`hosted` mode** on
[Railway](https://railway.app), fronted by Cloudflare on the **spotdl.dev** zone
(`spotdl.dev` for the site, `api.spotdl.dev` for the API). The Railway project,
domain, managed Postgres, and managed Redis are already provisioned; this page is
the config-as-code contract plus the operator runbook.

The image Railway builds is the **same `deploy/Dockerfile`** self-hosters pull
from GHCR — byte-identical build, same tag (spec §9). Nothing about hosting is a
private fork.

## Config-as-code: `deploy/railway.toml`

Build and deploy behavior is pinned in `deploy/railway.toml` (in the repository):

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "deploy/Dockerfile"
watchPatterns = ["apps/server/**", "apps/web/**", "packages/**", "deploy/Dockerfile"]

[deploy]
startCommand = "/app/docker-entrypoint.sh"   # migrations then uvicorn --factory
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
numReplicas = 1
```

The `startCommand` is the same entrypoint the container ships with: it runs
`upgrade_to_head` (the programmatic, idempotent Alembic upgrade — never raw
`alembic`) and then launches `uvicorn --factory spotdl_server.app:create_app`.

## Migrate-on-boot ⟷ `numReplicas = 1` (READ BEFORE SCALING) { #migrate-on-boot-and-scaling }

Migrations run **on boot, inside the entrypoint** (CONTRACT B). That is only
race-free with a **single instance**. `numReplicas = 1` is therefore a hard
safety coupling, not a capacity choice:

- Self-host (one compose container) is single-instance by construction.
- Railway is single-instance **only because `railway.toml` pins `numReplicas = 1`.**

Two replicas booting concurrently would race Alembic against the same database.
**Do not raise `numReplicas` above 1 until you have decoupled migrations first**,
by one of:

1. **Postgres advisory lock** — wrap the `upgrade_to_head` call so it acquires a
   `pg_advisory_lock` before migrating and releases it after; late replicas block
   on the lock, observe head, and proceed. Then it is safe to scale.
2. **Release-phase / pre-deploy migration** — move `upgrade_to_head` out of the
   entrypoint into a separate one-off step (Railway pre-deploy command or a
   dedicated release job) that runs once per deploy, and strip the migration line
   from `docker-entrypoint.sh` so the app containers only serve.

This coupling is called out in three places that must stay in sync: the
`docker-entrypoint.sh` comment, the `numReplicas` comment in `railway.toml`, and
this document.

## Service variables (set in the Railway dashboard — NEVER committed)

Set these on the service in the Railway dashboard. Reference variables
(`${{Postgres.DATABASE_URL}}`, `${{Redis.REDIS_URL}}`) are resolved by Railway
from the linked plugins at deploy time.

| Variable | Value | Notes |
| --- | --- | --- |
| `SPOTDL_MODE` | `hosted` | Full community surface; no local download engine. |
| `SPOTDL_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | See the `+asyncpg` driver note below. |
| `SPOTDL_REDIS_URL` | `${{Redis.REDIS_URL}}` | Presence enables the `RedisRateLimiter` (Plan 6). |
| `SPOTDL_RATE_LIMIT_ENABLED` | `true` | Belt-and-suspenders; hosted mode defaults it on anyway. |
| `SPOTDL_AUTH_SECRET_KEY` | `<openssl rand -hex 32>` | Token signing key; server fails fast without it. |
| `SPOTDL_SPOTIFY_CLIENT_ID` | `<operator>` | Operator's Spotify app credential. |
| `SPOTDL_SPOTIFY_CLIENT_SECRET` | `<operator>` | Operator's Spotify app credential. |
| `SPOTDL_SPOTIFY_PREFER_ANONYMOUS` | `false` | **Required on datacenter IPs.** The provider defaults to the anonymous web-player token (right for residential self-hosts), but Spotify persistently 429s anonymous API calls from cloud-provider IPs — and because the anon *token fetch* still succeeds, the client-credentials fallback never engages. `false` makes the operator credentials primary; anonymous becomes the fallback. |
| `SPOTDL_SENTRY_DSN` | `<optional>` | Error reporting; blank disables. |
| `SPOTDL_LOG_LEVEL` | `INFO` | Structured JSON log level. |
| `SPOTDL_CLIENT_IP_HEADER` | `cf-connecting-ip` | Trust Cloudflare's client-IP header for rate limiting + logs. |

### `+asyncpg` driver mapping

Railway's `${{Postgres.DATABASE_URL}}` is a plain `postgresql://…` URL, but the
server needs an **async** driver. `Settings.effective_database_url()` asserts the
URL names `+asyncpg` (or `+aiosqlite`). Map the reference variable to the async
driver form when you set `SPOTDL_DATABASE_URL`, e.g.:

```
postgresql+asyncpg://<user>:<pass>@<host>:<port>/<db>
```

Either edit the value to insert `+asyncpg` after `postgresql`, or set
`SPOTDL_DATABASE_URL` to `${{Postgres.DATABASE_URL}}` and confirm the resolved
value carries `+asyncpg` (Railway lets you template it). A `postgresql://` URL
without an async driver will fail the startup assertion by design — no silent
sync fallback.

### Redis rate limiting

The rate limiter's backend is selected purely by the **presence** of
`SPOTDL_REDIS_URL`: `build_rate_limiter()` returns a `RedisRateLimiter` when the
URL is set **and** the `redis` package is importable, otherwise the in-process
limiter. The hosted image bakes the `redis` extra in at build time
(`uv sync --frozen --no-dev --no-editable --package spotdl-server --extra redis`
in `deploy/Dockerfile`, CONTRACT B), so Redis "just works" once the reference
variable is set. The same image is what self-hosters pull; `redis` sits unused
there unless they set `SPOTDL_REDIS_URL` too.

## Staging → production promotion path

Deployments are **not** auto-promoted. The path (documented, run by the operator):

1. Deploy to the **staging** Railway environment first — it has its own Postgres
   and Redis plugins, isolated from production data.
2. Smoke it: `curl https://<staging-host>/api/v1/health` returns `{"status":"ok"}`
   and `curl https://<staging-host>/metrics` exports the `spotdl_*` metrics.
3. Promote the **same image tag** to the **production** environment (Railway
   environment promotion; no rebuild — the artifact that passed staging is what
   ships).

A local dry-run of the config is `railway up --detach` (builds and deploys the
current tree). It is **not** run in CI — CI validates that `railway.toml` parses;
the actual `railway up` is an operator action against the live project.

## Cloudflare in front (production)

Cloudflare sits in front of the production domain (spec §9):

- **Proxied DNS** — the `spotdl.dev` / `api.spotdl.dev` records are orange-clouded
  (proxied) so all traffic passes through Cloudflare.
- **TLS is terminated at Cloudflare → Railway.** Cloudflare holds the edge
  certificate; the origin connection to Railway is TLS as well. There is **no
  Caddy** in the hosted path — Caddy (`deploy/Caddyfile.example`) is the
  **self-host alternative** for operators who terminate TLS themselves.
- **Cache bypass for the API and metrics** — add cache rules that **bypass cache
  for `/api/*` and `/metrics`** so dynamic responses and the Prometheus scrape
  are never served stale from the edge. The SPA static assets can stay cached.
- **WAF / rate rules complement the app limiter** — Cloudflare WAF and rate rules
  are a coarse outer layer (bot/abuse mitigation, per-IP ceilings) that sits
  **in front of**, not instead of, the app's Redis-backed limiter. Because
  `SPOTDL_CLIENT_IP_HEADER=cf-connecting-ip`, the app trusts Cloudflare's
  client-IP header for its own per-identity limiting and structured logs.

## Go-live gate (GA)

The community server **must be live in `hosted` mode with both Postgres and Redis
before GA** (spec §12.8). This gate is referenced by the GA runbook (Plan 11
Task 12) and by the CLI default-endpoint work (Task 6, which points the CLI's
`DEFAULT_API_URL` at `https://api.spotdl.dev`). GA cannot be declared until a
health check and a `/metrics` scrape against the production `api.spotdl.dev` host
both pass.
