#!/bin/sh
set -e
# Migrate-on-boot: safe only with a SINGLE instance (compose selfhost; Railway numReplicas=1).
# Raising replicas requires an advisory lock or a release-phase migration instead — see docs/self-hosting/railway.md.
python -c "from spotdl_server.bootstrap import upgrade_to_head; from spotdl_server.settings import Settings; upgrade_to_head(Settings())"
exec uvicorn --factory spotdl_server.app:create_app --host 0.0.0.0 --port "${PORT:-8000}" --no-access-log
