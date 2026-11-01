#!/bin/sh
set -e

uv --project /app lock --upgrade
uv --project /app sync --no-dev --frozen

exec uv run --project /app --no-dev --frozen --no-sync spotdl "$@"
