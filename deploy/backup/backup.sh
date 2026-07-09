#!/usr/bin/env bash
#
# Nightly Postgres backup for the hosted spotDL instance (Plan 11 CONTRACT I).
#
# Runs on the Railway "backup" cron service (postgresql-client + rclone image,
# cronSchedule = "0 3 * * *"). It dumps Postgres, compresses the dump, uploads
# it to object storage (Cloudflare R2 / S3 via rclone), and prunes old dumps.
#
# Required environment (set as Railway service variables — never committed):
#   SPOTDL_DATABASE_URL_PSQL   libpq Postgres URL to dump. This is the *libpq*
#                              form (postgresql://...), NOT the app's async URL
#                              (postgresql+asyncpg://...): pg_dump speaks libpq
#                              and does not understand the SQLAlchemy +asyncpg
#                              driver suffix. Point it at the same database with
#                              the "+asyncpg" removed.
#   SPOTDL_BACKUP_REMOTE       rclone remote + path, e.g. "r2:spotdl-backups".
# Optional:
#   SPOTDL_BACKUP_RETENTION    max age before a dump is pruned (default "30d").
#
# rclone remote credentials (R2/S3 keys) live in the service environment / an
# rclone.conf mounted into the service — never in this repo.
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="spotdl-${STAMP}.sql.gz"
TMP="/tmp/${FILE}"

# libpq URL (no +asyncpg). pg_dump | gzip → local temp, then upload.
pg_dump "${SPOTDL_DATABASE_URL_PSQL:?SPOTDL_DATABASE_URL_PSQL is required}" \
  | gzip >"${TMP}"

rclone copyto "${TMP}" "${SPOTDL_BACKUP_REMOTE:?SPOTDL_BACKUP_REMOTE is required}/${FILE}"

# Retention: drop dumps older than the configured age.
rclone delete --min-age "${SPOTDL_BACKUP_RETENTION:-30d}" "${SPOTDL_BACKUP_REMOTE}"

# Free the local temp; the durable copy is in object storage.
rm -f "${TMP}"

echo "backup ok: ${SPOTDL_BACKUP_REMOTE}/${FILE}"
