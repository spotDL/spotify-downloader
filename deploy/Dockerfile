# syntax=docker/dockerfile:1

# ---- Stage 1: build the web SPA (Plan 10) ----
FROM node:22-alpine AS web-builder
# Railway requires cache-mount ids prefixed with its service cacheKey (s/<service-id>);
# it injects RAILWAY_SERVICE_ID as a build arg. Plain Docker leaves it empty and the
# id degrades to a local constant — behavior identical for self-hosters.
ARG RAILWAY_SERVICE_ID
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate   # matches apps/web packageManager pin (Plan 10) + ci.yml
WORKDIR /w
# pnpm-workspace.yaml carries the `allowBuilds` policy (e.g. msw: false); without
# it pnpm 11 fails the install with ERR_PNPM_IGNORED_BUILDS on unapproved scripts.
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./apps/web/
RUN --mount=type=cache,id=s/${RAILWAY_SERVICE_ID}-pnpm-store,target=/root/.local/share/pnpm/store pnpm -C apps/web install --frozen-lockfile
COPY apps/web/ ./apps/web/
RUN pnpm -C apps/web build          # -> /w/apps/web/dist

# ---- Stage 2: resolve Python deps + build the server venv ----
FROM python:3.13-slim AS py-builder
ARG RAILWAY_SERVICE_ID
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
# Build the venv at its FINAL runtime path (/app/.venv). uv writes absolute
# interpreter paths into console-script shebangs (uvicorn, alembic, …), so a venv
# built at one path and copied to another is not relocatable — the scripts would
# point at a missing interpreter. Building it where stage 3 mounts it keeps every
# entry point valid.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY apps/server/ ./apps/server/
# apps/cli is a declared uv workspace member; its manifest must exist on disk for
# `uv sync` to build the workspace graph, even though we only install
# spotdl-server. Copying just the manifest keeps the build layer minimal.
COPY apps/cli/pyproject.toml ./apps/cli/pyproject.toml
# The SPA is embedded INTO the server package (spotdl_server/webui, the Plan 10
# dir the wheel force-includes via apps/server/pyproject.toml `artifacts`) BEFORE
# the wheel is built, so the built wheel ships the UI (spec §8). The server wheel
# must ALSO package the alembic scripts dir (Plan 5 Hatch force-include) so
# upgrade_to_head works from the installed venv, never the CWD.
COPY --from=web-builder /w/apps/web/dist ./apps/server/src/spotdl_server/webui/
# --no-editable installs a BUILT wheel (webui + alembic packaged) into the venv,
# so stage 3 needs only the venv — no fragile source overlay. --extra redis/sentry bake
# in the optional Redis rate-limit backend for the hosted image (CONTRACT D).
RUN --mount=type=cache,id=s/${RAILWAY_SERVICE_ID}-uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package spotdl-server --extra redis --extra sentry

# ---- Stage 3: runtime ----
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r spotdl && useradd -r -g spotdl spotdl
WORKDIR /app
COPY --from=py-builder /app/.venv /app/.venv
COPY deploy/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/data && chown -R spotdl:spotdl /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SPOTDL_MODE=selfhost \
    SPOTDL_DATA_DIR=/app/data \
    SPOTDL_DATABASE_URL="sqlite+aiosqlite:////app/data/spotdl.db"
USER spotdl
EXPOSE 8000
# No VOLUME hint: compose (docker-compose.selfhost.yml) declares the /app/data
# mount itself, and Railway's builder rejects Dockerfile VOLUME outright.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
