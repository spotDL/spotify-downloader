.PHONY: sync lint typecheck test check web-install web-check web-clients web-clients-check web-build web-embed web-e2e dist openapi ws-schema clients docs docs-check

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

# Build the production SPA bundle (apps/web/dist).
web-build:
	pnpm -C apps/web run build

# Copy the built SPA into the server package so the wheel can ship it (Plan 10).
# The target dir is git-ignored and force-included by apps/server/pyproject.toml.
web-embed:
	rm -rf apps/server/src/spotdl_server/webui
	mkdir -p apps/server/src/spotdl_server/webui
	cp -R apps/web/dist/. apps/server/src/spotdl_server/webui/

# Playwright e2e: build + embed the SPA, then drive it against the seeded server
# (playwright.config.ts boots apps/server/scripts/serve_e2e.py). Kept OUT of
# web-check / check — it needs a built server + a browser (CI runs it as its own
# job; run `pnpm -C apps/web exec playwright install chromium` first locally).
web-e2e: web-build web-embed
	pnpm -C apps/web exec playwright test

# Build the spotdl-server wheel with the SPA embedded: build → embed → wheel.
dist: web-build web-embed
	uv build --wheel --package spotdl-server

openapi:
	uv run python apps/server/scripts/export_openapi.py

ws-schema:
	uv run python apps/server/scripts/export_ws_schema.py

# Regenerate the checked-in CLI client (Plan 8 Task 1) from the server's
# committed OpenAPI + WS-protocol artifacts. Deterministic: pinned generators,
# no timestamps, `ruff format` post-processing → byte-stable output. The in-sync
# test (apps/cli/tests/test_clients_in_sync.py) fails if the tree drifts.
clients:
	uv run openapi-python-client generate \
		--path apps/server/openapi.json \
		--meta none \
		--output-path apps/cli/src/spotdl_cli/_generated/api \
		--config scripts/openapi-python-client.yaml \
		--overwrite
	uv run python -c "import json,sys; json.dump(json.load(open('apps/server/ws-protocol.json'))['message'], sys.stdout)" \
		| uv run datamodel-codegen --input-file-type jsonschema \
			--output apps/cli/src/spotdl_cli/_generated/ws_models.py \
			--output-model-type pydantic_v2.BaseModel \
			--target-python-version 3.13 --use-standard-collections --use-union-operator \
			--class-name WsMessage --disable-timestamp
	uv run ruff check --select I --fix apps/cli/src/spotdl_cli/_generated
	uv run ruff format apps/cli/src/spotdl_cli/_generated

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
