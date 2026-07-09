# Backups & restore

Your spotDL instance holds accounts, votes, reports and match curation — data
you cannot re-derive. Back it up.

How you back up depends on your database:

- **Postgres** (hosted / larger self-host): nightly `pg_dump` to object storage.
- **SQLite** (single-container default): copy the volume file.

## Postgres: nightly `pg_dump` to object storage

The community instance backs up nightly with a small script that dumps Postgres,
compresses it, uploads it to object storage (Cloudflare R2 / S3 via `rclone`),
and prunes old dumps. The script lives at `deploy/backup/backup.sh`:

```sh
set -euo pipefail
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="spotdl-${STAMP}.sql.gz"
pg_dump "${SPOTDL_DATABASE_URL_PSQL:?}" | gzip > "/tmp/${FILE}"     # libpq URL (no +asyncpg)
rclone copyto "/tmp/${FILE}" "${SPOTDL_BACKUP_REMOTE:?}/${FILE}"    # remote configured via env (R2/S3)
rclone delete --min-age "${SPOTDL_BACKUP_RETENTION:-30d}" "${SPOTDL_BACKUP_REMOTE}"   # retention
```

!!! note "libpq vs `+asyncpg`"
    `pg_dump` speaks **libpq**, not SQLAlchemy. It needs a plain
    `postgresql://…` URL, so backups read a separate `SPOTDL_DATABASE_URL_PSQL`
    variable — **not** the app's `postgresql+asyncpg://…` `SPOTDL_DATABASE_URL`.
    Point it at the same database with the driver suffix removed.

The environment variables the script reads:

| Variable | Purpose |
|---|---|
| `SPOTDL_DATABASE_URL_PSQL` | libpq Postgres URL to dump (`postgresql://…`) |
| `SPOTDL_BACKUP_REMOTE` | `rclone` remote + path, e.g. `r2:spotdl-backups` |
| `SPOTDL_BACKUP_RETENTION` | max age before a dump is pruned (default `30d`) |

`rclone`'s remote credentials (R2/S3 keys) live in the backup service's
environment only — never in the repo.

## SQLite: copy the volume

On the single-container SQLite default there is no database server to dump — the
whole database is one file under the data volume. Stop the container (or accept a
crash-consistent copy) and copy `spotdl.db`:

```bash
docker compose -f deploy/docker-compose.selfhost.yml stop
docker run --rm -v spotdl_spotdl_data:/data -v "$PWD":/backup alpine \
  cp /data/spotdl.db "/backup/spotdl-$(date -u +%Y%m%dT%H%M%SZ).db"
docker compose -f deploy/docker-compose.selfhost.yml start
```

Ship the copy off-box on whatever schedule suits you.

Full runbook — including the Railway backup **cron service** and the quarterly
**restore drill** — is documented below; the scripts and their README live under
`deploy/backup/`.
