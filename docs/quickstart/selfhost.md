# Quickstart: Self-hosting

Run your own spotDL server for your household or team. Self-hosters pull the
**same Docker image** the community instance runs — it is byte-identical (built
from the same `deploy/Dockerfile`).

## One container (SQLite)

```bash
export SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32)
docker compose -f deploy/docker-compose.selfhost.yml up -d
```

This runs a single container with a named volume for data (SQLite by default).
Open `http://localhost:8000` for the web UI, or point the CLI at it:

```bash
spotdl --api-url http://localhost:8000 "<url>"
```

## Options at a glance

| You want… | Do this |
|---|---|
| A single box, minimal setup | The compose command above (SQLite) — see [Docker & Compose](../self-hosting/docker.md) |
| Postgres instead of SQLite | Add the Postgres override — see [Docker & Compose](../self-hosting/docker.md) |
| HTTPS on a public domain | Put [Caddy or another reverse proxy](../self-hosting/reverse-proxy.md) in front |
| A managed cloud deploy | [Railway config-as-code](../self-hosting/railway.md) |
| Durable data | [Backups & restore](../self-hosting/backups.md) |

## Configuration

The server is configured entirely through `SPOTDL_`-prefixed environment
variables. The self-host stack ships a `deploy/.env.example` listing every
recognized variable with placeholders; copy it to `.env` and fill in at least
`SPOTDL_AUTH_SECRET_KEY` (`openssl rand -hex 32`).

Start with [Docker & Compose](../self-hosting/docker.md) for the full walk-through.
