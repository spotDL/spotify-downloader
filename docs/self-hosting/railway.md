# Railway

The community instance runs on [Railway](https://railway.app/) in `hosted` mode
with managed Postgres and Redis, behind Cloudflare. You can deploy your own the
same way. Railway builds from the same `deploy/Dockerfile` as every other
deployment.

## Config-as-code

`deploy/railway.toml` pins the build and deploy behavior:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "deploy/Dockerfile"
watchPatterns = ["apps/server/**", "apps/web/**", "packages/**", "deploy/Dockerfile"]

[deploy]
startCommand = "/app/docker-entrypoint.sh"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
numReplicas = 1
```

## Service variables

Set these on the Railway service (dashboard → Variables). **They are never
committed.** Railway reference variables wire the managed plugins in:

```bash
SPOTDL_MODE=hosted
SPOTDL_DATABASE_URL=${{Postgres.DATABASE_URL}}   # asyncpg URL (see note below)
SPOTDL_REDIS_URL=${{Redis.REDIS_URL}}            # enables the Redis rate limiter
SPOTDL_RATE_LIMIT_ENABLED=true
SPOTDL_AUTH_SECRET_KEY=<openssl rand -hex 32>
SPOTDL_SPOTIFY_CLIENT_ID=<operator credential>
SPOTDL_SPOTIFY_CLIENT_SECRET=<operator credential>
SPOTDL_SENTRY_DSN=<optional>
SPOTDL_LOG_LEVEL=INFO
SPOTDL_CLIENT_IP_HEADER=cf-connecting-ip         # trust Cloudflare's client IP
```

### The `+asyncpg` driver mapping

The server uses the async SQLAlchemy driver, so `SPOTDL_DATABASE_URL` must use
the `postgresql+asyncpg://` scheme. Railway's `${{Postgres.DATABASE_URL}}`
reference provides a `postgresql://` URL; the server maps it to the async driver
via `effective_database_url()`. (Backups use a separate **libpq** URL — see
[Backups & restore](backups.md).)

### Redis rate limiting

The rate limiter uses its Redis backend automatically **when
`SPOTDL_REDIS_URL` is set and the `redis` package is present** — the `redis`
extra is baked into the hosted image, so setting the reference variable is all
that is required. Without it, an in-memory limiter is used.

## Staging → production

Promote by tag, not by rebuilding:

1. Deploy to a **staging** Railway environment (its own Postgres/Redis).
2. Smoke it: `curl https://staging.../api/v1/health` and `.../metrics`.
3. Promote the **same image tag** to the **production** environment.

## Cloudflare

Cloudflare sits in front of the production domain:

- **Proxied DNS** (orange cloud) for the domain.
- **Bypass cache** for `/api/*` and `/metrics` (dynamic; never cache API
  responses or metrics).
- **WAF / rate rules** complementing the app's own Redis limiter.
- **TLS** is terminated at Cloudflare → Railway. (For a non-Cloudflare
  self-host, terminate at [Caddy](reverse-proxy.md) instead.)

Because Cloudflare fronts the app, set `SPOTDL_CLIENT_IP_HEADER=cf-connecting-ip`
so the limiter and logs see the real client IP.

## Migrate-on-boot and scaling

The entrypoint runs Alembic migrations on boot. That is race-free **only because
`numReplicas = 1`.** Two replicas booting concurrently would race the migration.

To scale beyond one replica you must first decouple migrations:

- wrap `upgrade_to_head` in a Postgres advisory lock (`pg_advisory_lock`), **or**
- move it to a separate release-phase step (a Railway pre-deploy command or a
  one-off job) and strip it from the entrypoint.

Do not raise `numReplicas` before doing one of those.

## Go-live gate

Before v5 GA, the community server must be **live in `hosted` mode with Postgres
and Redis** and healthy behind Cloudflare (`/api/v1/health` and `/metrics`
green), with the CLI's default API URL pointed at it. This gate is part of the
GA-cutover runbook.
