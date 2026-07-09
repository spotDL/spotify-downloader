# Self-hosting with Docker & Compose

spotDL ships a single multi-stage Docker image that bundles the server and the
web UI. The **same image** runs the community instance and every self-host — it
is byte-identical (same `deploy/Dockerfile`, same GHCR tag). The runtime mode is
chosen by the `SPOTDL_MODE` environment variable.

- **Image:** `ghcr.io/spotdl/spotify-downloader`
- **Tags:** `edge` (latest `v5` branch build), `5.0.0aN` (pre-releases), and —
  after GA — `X.Y.Z` / `X.Y` / `latest`.

## One container (SQLite)

The simplest deployment is one container with one volume, using SQLite. Use the
provided compose file:

```bash
# Set a random JWT signing key first
export SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32)

docker compose -f deploy/docker-compose.selfhost.yml up -d
```

Then open `http://localhost:8000` (web UI) or hit `/api/v1/health`:

```bash
curl -fsS http://localhost:8000/api/v1/health   # {"status":"ok"}
```

The image runs as a **non-root** user, migrates the database on boot, and stores
everything under the `/app/data` volume.

## Postgres instead of SQLite

SQLite is fine for a single box. For a bigger deployment, add the Postgres
override — it is additive:

```bash
export SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32)
export SPOTDL_DB_PASSWORD=$(openssl rand -hex 16)

docker compose \
  -f deploy/docker-compose.selfhost.yml \
  -f deploy/docker-compose.postgres.yml \
  up -d
```

The override adds a `postgres:17` service, waits for it to be healthy, and points
the app at it via `SPOTDL_DATABASE_URL=postgresql+asyncpg://…`.

## Configuration

Everything is configured through `SPOTDL_`-prefixed environment variables. Copy
the shipped example and edit it:

```bash
cp deploy/.env.example .env
```

Key variables:

| Variable | Purpose |
|---|---|
| `SPOTDL_MODE` | `selfhost` (default in the image) or `hosted` |
| `SPOTDL_AUTH_SECRET_KEY` | JWT signing key — **required**; `openssl rand -hex 32` |
| `SPOTDL_DATABASE_URL` | Database URL; defaults to SQLite under `/app/data` |
| `SPOTDL_DATA_DIR` | Data directory (default `/app/data`) |
| `SPOTDL_LOG_LEVEL` | `INFO` by default; JSON logs to stdout |
| `SPOTDL_SENTRY_DSN` | Optional error reporting |
| `SPOTDL_REDIS_URL` | Optional; enables the Redis-backed rate limiter |

Never commit secrets. `deploy/.env.example` is the only committed env file and
carries placeholders only.

## Observability

The server emits **structured JSON logs** to stdout (one object per line) and
exposes Prometheus metrics at `GET /metrics` (request rates, cache hit ratio,
provider error rates, queue depths, matcher-version distribution). Point your
log shipper at stdout and your Prometheus scraper at `/metrics`.

## Building the image locally

The compose file pulls the published image by default. To build from source
instead, uncomment the `build:` block in
`deploy/docker-compose.selfhost.yml`, or:

```bash
docker build -f deploy/Dockerfile -t spotdl:local .
```

## Migrate-on-boot & scaling

The container runs database migrations on startup (via the programmatic
`upgrade_to_head`, never raw `alembic`). **This is safe only with a single
instance.** Two containers booting at once would race the migration. To run more
than one replica, first move migrations out of the entrypoint — either wrap them
in a Postgres advisory lock or run them as a separate release-phase step. This
coupling is documented for the managed deploy in
[Railway](railway.md#migrate-on-boot-and-scaling) too.

## Going public

To expose the server on a domain with HTTPS, put a reverse proxy in front — see
[Caddy / reverse proxy](reverse-proxy.md). Then set up
[backups](backups.md).
