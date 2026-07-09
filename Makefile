.PHONY: sync lint typecheck test check web-install web-check web-clients web-clients-check openapi ws-schema docs docs-check

sync:
	uv sync --all-packages --all-groups

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports

typecheck:
	uv run mypy packages/core/src apps/server/src apps/cli/src scripts

test:
	uv run pytest

web-install:
	pnpm -C apps/web install

web-check:
	pnpm -C apps/web run lint
	pnpm -C apps/web run type-check
	pnpm -C apps/web run test
	pnpm -C apps/web run build

# Regenerate the checked-in TS API client + WS types from the server artifacts
# (apps/server/openapi.json, apps/server/ws-protocol.json). Never hand-edit the
# output; run this and commit it.
web-clients:
	pnpm -C apps/web run generate:api
	pnpm -C apps/web run generate:ws

# In-sync guard (CONTRACT A3): regenerate and fail if the committed client is
# stale. Sibling of the Python client's test_clients_in_sync. Run in CI.
web-clients-check: web-clients
	git diff --exit-code apps/web/src/api/generated apps/web/src/api/ws-types.gen.ts apps/web/src/api/ws-protocol.gen.ts \
		|| (echo 'generated TS client is stale — run `make web-clients` and commit'; exit 1)

openapi:
	uv run python apps/server/scripts/export_openapi.py

ws-schema:
	uv run python apps/server/scripts/export_ws_schema.py

# Regenerate the committed migration guide from the CLI shim table, then build
# the docs site strictly (fails on broken links / missing nav pages). The
# OpenAPI reference is copied at build time from apps/server/openapi.json.
docs:
	uv run --group docs python scripts/docs/gen_migration_guide.py
	uv run --group docs mkdocs build --strict

# Drift guard: fail if the committed migration guide is stale (mirrors Plan 5's
# openapi in-sync test for the API reference). Run in CI.
docs-check:
	uv run --group docs python scripts/docs/gen_migration_guide.py --check

check: lint typecheck test web-check
