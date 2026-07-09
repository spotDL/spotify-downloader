# Contributing

spotDL is a community project. Contributions — code, docs, matcher corpus cases,
bug reports — are welcome.

- **Chat:** the [spotDL Discord](https://discord.gg/xCa23pwJWH) is where
  development and support happen.
- **Issues:** file bugs and feature requests on
  [GitHub](https://github.com/spotDL/spotify-downloader/issues) using the issue
  forms.

## Repository layout

v5 is a uv-managed Python monorepo plus a pnpm web app:

```
packages/core     # spotdl-core: providers, matching, download, tagging
apps/server       # spotdl-server: FastAPI app, DB, community layer, observability
apps/cli          # spotdl: CLI + TUI (talks to the server)
apps/web          # the React web UI (built and embedded into spotdl-server)
deploy/           # Dockerfile, compose, Railway, Caddy, backups
docs/             # this site (mkdocs-material)
scripts/          # generators (docs, version bump, binary build) + corpus tools
```

Dependency direction is `core ← server ← cli`, enforced by import-linter.

## Development setup

Requires **uv**, **Python 3.13+**, **Node 22+** and **pnpm 11.10.0**.

```bash
make sync          # install the Python workspace (all packages)
make web-install   # install web deps
make check         # lint + typecheck + test (Python + web)
```

## Docs

The docs site is mkdocs-material. Build it locally:

```bash
make docs          # regenerate the migration guide, then mkdocs build --strict
uv run mkdocs serve # live preview
```

The **migration guide** (`docs/migration/v4-to-v5.md`) is **generated** from the
CLI's compat-shim table — do not edit it by hand. Run `make docs` to regenerate,
and `make docs-check` to verify it is in sync (CI enforces this). The **API
reference** is rendered from the server's committed `apps/server/openapi.json`;
regenerate that with `make openapi`.

## Releasing (maintainers)

Releases are automated from git tags:

- **Version** is single-sourced across the three published packages
  (`spotdl-core`, `spotdl-server`, `spotdl`) by `scripts/bump_version.py`; CI
  guards that all locations agree.
- **PyPI** publishing uses **Trusted Publishing** (OIDC — no API tokens). Each
  of the three PyPI projects is configured with this repository, the
  `release-pypi.yml` workflow and the `pypi` environment as a trusted publisher.
  Packages publish in dependency order: `spotdl-core` → `spotdl-server` →
  `spotdl`.
- **Docker** images publish to GHCR on every `v5` push and tag; Docker Hub and
  the `latest` tag are applied only at GA.
- **Binaries** (PyInstaller) build on a per-OS matrix and attach to the GitHub
  release.
- **Docs** deploy to GitHub Pages via `mkdocs gh-deploy`.

Pre-releases are tagged `v5.0.0aN`; `pip install spotdl` keeps serving stable v4
until the GA `5.0.0` tag.
