.PHONY: sync lint typecheck test check web-install web-check openapi ws-schema

sync:
	uv sync --all-packages

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

check: lint typecheck test web-check
