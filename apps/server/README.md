# `apps/server` — spotDL v5 metadata backend

FastAPI + SQLAlchemy 2 (async) + Alembic backend implementing the read side of
spec §6: the §6.1 database schema, the entity persistence layer (provider-snapshot
cache → deterministic canonical merge → matches/lyrics/links), and the
non-auth/non-download `/api/v1` surface (`POST /resolve`, `GET /search`, typed
entity GETs, `/tracks/{id}/matches`, `/tracks/{id}/lyrics`, `/config`, `/health`).

Auth/votes/reports/admin are **Plan 6**; downloads and WebSocket progress are
**Plan 7**. The schema is designed complete so neither plan ALTERs a table
created here.

## Layering (spec §6) — a contract, not a convention

```
api.routers  →  services  →  repositories  →  db
(HTTP only)     (orchestration) (ORM queries)   (schema)
```

- **Routers** (`api/routers/`) import only `fastapi`, the Pydantic API schemas,
  and service classes (reached through `api/deps.py`). They never import
  `sqlalchemy` or the ORM models, and each router file stays **≤200 lines**.
- **Services** (`services/`) take and return plain DTOs; they orchestrate
  repositories and the core provider registry/matcher. They never import
  `fastapi`.
- **Repositories** (`repositories/`) are the **sole** holders of SQLAlchemy query
  code.
- **`db/`** defines the schema (models, enums, base) and imports none of the
  layers above it.
- **Core** (`packages/core`) is reached only through the Plan 2 `ProviderRegistry`
  and the Plan 3 `match()` function. `apps/server` is the only consumer of core.

`api/deps.py`, `api/errors.py` and `api/schemas.py` are HTTP glue that sit
**outside** the four layers by design: `deps.py` composes the request-scoped
session (so it legitimately imports SQLAlchemy) and wires services into routers.

### How the layering is enforced

Two independent, always-on guards:

1. **`.importlinter`** — the `server_layers` (layers), `routers_no_orm` and
   `services_no_fastapi` (forbidden) contracts check the whole import graph. Run
   with `uv run lint-imports` (part of `make lint` / `make check`).
2. **`tests/test_layering.py`** — a source-level `ast` check that fails with a
   precise per-file message the moment a router imports the ORM, a service
   imports FastAPI, a lower layer imports a higher one, or a router file exceeds
   200 lines. This is the single home for the router line-count rule.

`tests/test_integration_resolve_flow.py` is the Plan 5 acceptance test: it
migrates a tmp-file SQLite DB via `spotdl_server.bootstrap.upgrade_to_head`
(the real boot path Plan 8's embedded CLI uses — not `metadata.create_all`),
injects a fake provider registry through `create_app(settings, registry=...)`,
and drives the full `resolve → read → matches → lyrics → re-resolve` flow over
`httpx.ASGITransport`, asserting degraded-source surfacing and that a re-resolve
reuses the one canonical track with its matches replaced (not duplicated).

## Running

```bash
make check     # lint (+ lint-imports) + typecheck + test + web-check
uv run pytest apps/server/tests
```

The default suite is fully **offline**: SQLite (in-memory or tmp file) and fake
providers at the registry seam — no network, no Postgres required. Postgres-backed
dual-dialect tests skip locally when `SPOTDL_TEST_POSTGRES_URL` is unset and run in
CI.
