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

## The Railway backup cron service

On the hosted instance, `backup.sh` runs as a **second Railway service** in the
same project as the server:

- **Image:** a small image with `postgresql-client` (for `pg_dump`) and `rclone`
  (for uploads); start command `bash deploy/backup/backup.sh`.
- **Schedule:** `cronSchedule = "0 3 * * *"` (nightly, 03:00 UTC).
- **Healthcheck:** none. **Restart policy:** never — it is a one-shot cron job.
- **Variables** (dashboard only): `SPOTDL_DATABASE_URL_PSQL` (the **libpq** URL,
  see the note above), `SPOTDL_BACKUP_REMOTE` (e.g. `r2:spotdl-backups`),
  optional `SPOTDL_BACKUP_RETENTION` (default `30d`), and the rclone remote
  credentials. None of these are committed.

## Restoring

`deploy/backup/restore.sh` streams a dump from the remote straight into a target
database:

```bash
export SPOTDL_BACKUP_REMOTE=r2:spotdl-backups

# A specific dump into an explicit libpq target URL:
./deploy/backup/restore.sh spotdl-20260709T030000Z.sql.gz \
  "postgresql://user:pass@host:5432/target"

# Or the most recent dump into $SPOTDL_RESTORE_TARGET_URL:
export SPOTDL_RESTORE_TARGET_URL="postgresql://user:pass@host:5432/target"
./deploy/backup/restore.sh latest
```

Restore into a throwaway/target database — never the live app DB unless you
intend to overwrite it.

## Quarterly restore drill

A backup you have never restored is a hope, not a backup. Once a quarter, prove
recovery end-to-end and record the result:

1. **Provision a throwaway Postgres** (scratch Railway Postgres or a local
   `postgres:17` container); note its libpq URL.
2. **Restore the latest dump** into it:
   `SPOTDL_BACKUP_REMOTE=… SPOTDL_RESTORE_TARGET_URL=<throwaway> ./deploy/backup/restore.sh latest`.
3. **Boot the server image** against the throwaway DB
   (`SPOTDL_DATABASE_URL=postgresql+asyncpg://…<throwaway>` — note the async
   driver here, unlike the libpq restore URL).
4. **Health:** `curl -fsS http://<host>/api/v1/health` → `{"status":"ok"}`.
5. **Function:** one `POST /api/v1/resolve` with a known Spotify URL returns
   resolved metadata (proves the restored data + schema are usable).
6. **Record the outcome** (date, dump, pass/fail) and tear down the throwaway DB.

The full runbook, the drill checklist and an outcome log live alongside the
scripts in `deploy/backup/README.md`.
