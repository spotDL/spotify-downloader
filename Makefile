.PHONY: sync lint typecheck test check web-install web-check

sync:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports

typecheck:
	uv run mypy packages/core/src apps/server/src apps/cli/src

test:
	uv run pytest

web-install:
	pnpm -C apps/web install

web-check:
	pnpm -C apps/web run type-check
	pnpm -C apps/web run test

check: lint typecheck test web-check
