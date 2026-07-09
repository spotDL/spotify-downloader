#!/usr/bin/env bash
#
# Restore a spotDL Postgres dump produced by backup.sh (Plan 11 CONTRACT I).
#
# Streams a chosen (gzipped) dump from the backup remote straight into a target
# Postgres. Used both for real recovery and for the quarterly restore drill
# (restore into a throwaway database, boot the image against it, smoke-test).
#
# Usage:
#   restore.sh <dump-name|latest> [target-libpq-url]
#
#   <dump-name>   e.g. "spotdl-20260709T030000Z.sql.gz", or the literal "latest"
#                 to pick the most recent dump in SPOTDL_BACKUP_REMOTE.
#   target URL    libpq Postgres URL to restore INTO. Defaults to
#                 $SPOTDL_RESTORE_TARGET_URL. This MUST be a throwaway/target DB,
#                 never the live app database unless you intend to overwrite it.
#
# Required environment:
#   SPOTDL_BACKUP_REMOTE        rclone remote + path the dumps live under.
# Optional:
#   SPOTDL_RESTORE_TARGET_URL   default target libpq URL when arg 2 is omitted.
#
# rclone remote credentials live in the environment — never in this repo.
set -euo pipefail

usage() {
  echo "usage: restore.sh <dump-name|latest> [target-libpq-url]" >&2
  exit 2
}

[ "$#" -ge 1 ] || usage

DUMP="$1"
TARGET="${2:-${SPOTDL_RESTORE_TARGET_URL:?target URL required (arg 2 or SPOTDL_RESTORE_TARGET_URL)}}"
REMOTE="${SPOTDL_BACKUP_REMOTE:?SPOTDL_BACKUP_REMOTE is required}"

if [ "${DUMP}" = "latest" ]; then
  # Newest dump by name (timestamps sort lexicographically). rclone lsf prints
  # one filename per line; take the last after sorting.
  DUMP="$(rclone lsf "${REMOTE}" --include 'spotdl-*.sql.gz' | sort | tail -n 1)"
  [ -n "${DUMP}" ] || {
    echo "no dumps found under ${REMOTE}" >&2
    exit 1
  }
  echo "latest dump: ${DUMP}" >&2
fi

echo "restoring ${REMOTE}/${DUMP} → target database" >&2

# Stream: object storage → gunzip → psql. No local temp file.
rclone cat "${REMOTE}/${DUMP}" | gunzip | psql "${TARGET}"

echo "restore ok: ${DUMP}"
