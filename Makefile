.PHONY: sync lint typecheck test check web-install web-check openapi ws-schema docs docs-check

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
