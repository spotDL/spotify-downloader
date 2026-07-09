# spotDL backups & restore

Nightly Postgres backups for the hosted spotDL instance, plus the restore
procedure and the quarterly restore drill (Plan 11 CONTRACT I).

| File | Purpose |
|---|---|
| `backup.sh` | `pg_dump \| gzip \| rclone upload` + retention. Runs on the Railway cron service. |
| `restore.sh` | Stream a chosen dump back into a target Postgres (recovery + drill). |

The user-facing version of this runbook is published at
[`docs/self-hosting/backups.md`](../../docs/self-hosting/backups.md).

## What gets backed up

The database only — accounts, votes, reports, match curation and metadata
snapshots. Downloaded audio is not backed up (it is re-downloadable and, on the
hosted instance, not retained server-side).

- **Postgres** (hosted / larger self-host): nightly `pg_dump` to object storage
  via `backup.sh`.
- **SQLite** (single-container self-host default): copy the volume file — see
  the [SQLite alternative](#sqlite-self-host-alternative) below.

## The Railway backup cron service

Add a **second service** to the same Railway project (alongside the server):

- **Image:** a small image with `postgresql-client` (for `pg_dump`) and
  `rclone` (for uploads). Mount this `deploy/backup/` directory (or bake the
  scripts in) and set the start command to `bash deploy/backup/backup.sh`.
- **Schedule:** `cronSchedule = "0 3 * * *"` (nightly at 03:00 UTC).
- **Healthcheck:** none.
- **Restart policy:** never (it is a one-shot cron job, not a long-running
  service).

### Service variables (set in the Railway dashboard — never committed)

| Variable | Required | Purpose |
|---|---|---|
| `SPOTDL_DATABASE_URL_PSQL` | yes | **libpq** Postgres URL to dump (see note below). |
| `SPOTDL_BACKUP_REMOTE` | yes | rclone remote + path, e.g. `r2:spotdl-backups`. |
| `SPOTDL_BACKUP_RETENTION` | no | Max dump age before pruning (default `30d`). |
| rclone remote credentials | yes | R2/S3 keys, via rclone env vars or a mounted `rclone.conf`. |

### The libpq vs `+asyncpg` URL distinction

The server connects with the **async** SQLAlchemy driver, so its
`SPOTDL_DATABASE_URL` is `postgresql+asyncpg://…`. `pg_dump` speaks **libpq**
and does not understand the `+asyncpg` driver suffix. The backup service
therefore reads a **separate** `SPOTDL_DATABASE_URL_PSQL` — the same database
with the driver suffix removed (`postgresql://…`). Keeping them distinct avoids
handing a SQLAlchemy URL to a libpq tool.

### Retention

`backup.sh` runs `rclone delete --min-age "${SPOTDL_BACKUP_RETENTION:-30d}"`
after each upload, pruning dumps older than the window. Thirty days of nightly
dumps is the default; raise it for longer history (object storage is cheap).

## Restoring

`restore.sh` streams a dump from the remote straight into a target database (no
local temp file):

```bash
export SPOTDL_BACKUP_REMOTE=r2:spotdl-backups

# A specific dump into an explicit target:
./restore.sh spotdl-20260709T030000Z.sql.gz "postgresql://user:pass@host:5432/target"

# Or the most recent dump into $SPOTDL_RESTORE_TARGET_URL:
export SPOTDL_RESTORE_TARGET_URL="postgresql://user:pass@host:5432/target"
./restore.sh latest
```

The target URL is also a **libpq** URL. Restore into a throwaway/target
database — never the live app DB unless you intend to overwrite it.

## Quarterly restore drill

A backup you have never restored is a hope, not a backup. Once a quarter, prove
recovery end-to-end and record the outcome:

- [ ] **Provision a throwaway Postgres** (a scratch Railway Postgres, or a local
      `postgres:17` container). Note its libpq URL.
- [ ] **Restore the latest dump** into it:
      `SPOTDL_BACKUP_REMOTE=… SPOTDL_RESTORE_TARGET_URL=<throwaway> ./restore.sh latest`.
- [ ] **Boot the server image** against the throwaway DB
      (`SPOTDL_DATABASE_URL=postgresql+asyncpg://…<throwaway>`, note the async
      driver here).
- [ ] **Health check:** `curl -fsS http://<host>/api/v1/health` → `{"status":"ok"}`.
- [ ] **Functional check:** one `POST /api/v1/resolve` with a known Spotify URL
      returns resolved metadata (proves the restored data + schema are usable).
- [ ] **Record the outcome** (date, dump restored, pass/fail, notes) in the
      table below, then tear down the throwaway DB.

| Date | Dump restored | Health | Resolve | Notes |
|---|---|---|---|---|
| _YYYY-MM-DD_ | _spotdl-…sql.gz_ | ☐ | ☐ | |

## SQLite self-host alternative

On the single-container SQLite default there is no database server to dump — the
whole database is one file under the data volume. Copy it (stop the container
first for a clean copy, or accept a crash-consistent copy):

```bash
docker compose -f deploy/docker-compose.selfhost.yml stop
docker run --rm -v spotdl_spotdl_data:/data -v "$PWD":/backup alpine \
  cp /data/spotdl.db "/backup/spotdl-$(date -u +%Y%m%dT%H%M%SZ).db"
docker compose -f deploy/docker-compose.selfhost.yml start
```

Restore by copying the file back into the volume and starting the container.
Ship copies off-box on whatever schedule suits you.
