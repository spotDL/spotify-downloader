# Contributing

Thanks for helping build spotDL v5. This page covers the development workflow and,
in detail, **how releases are cut** (versioning + PyPI Trusted Publishing).

## Development setup

```sh
uv sync --all-packages     # Python workspace (core + server + cli)
make check                 # lint + typecheck + tests + web checks
```

The repo is a uv workspace with three published packages — `spotdl-core`,
`spotdl-server`, `spotdl` (the CLI) — plus the web UI under `apps/web`. Dependency
direction `core <- server <- cli` is machine-enforced by import-linter; nothing in
`deploy/`, `docs/`, or `scripts/` may violate it.

## Versioning — single source of truth

All three packages share one version. **Never edit a version by hand.** Use the
bumper, which writes every location atomically:

```sh
python scripts/bump_version.py 5.0.0a1     # set the version everywhere
python scripts/bump_version.py --check      # verify every location agrees (CI runs this)
```

`bump_version.py` writes, and `--check` verifies, **all** of these in lockstep:

- `[project].version` in `packages/core/pyproject.toml`, `apps/server/pyproject.toml`,
  `apps/cli/pyproject.toml`
- `__version__` in each package's `src/**/__init__.py`
- the cross-package `==` pins — `spotdl-server` requires `spotdl-core==<ver>`, and
  `spotdl` requires `spotdl-server==<ver>`

The pins matter: uv resolves the workspace deps locally, but a **published** wheel
only carries a version requirement if the dependency string declares one. Without
the `==` pin, `spotdl-server`'s wheel would ship `Requires-Dist: spotdl-core`
(unpinned) and let `pip install spotdl==5.0.0` pull a mismatched core off PyPI.
CI's `version-consistency` step (`bump_version.py --check`, in the `python` job)
fails the build on any drift.

Only PEP 440 versions are accepted (e.g. `5.0.0a1`, `5.0.0`). Pre-releases use the
alpha form `5.0.0aN`.

## Releasing

Releases are automated by `.github/workflows/release-pypi.yml` (PyPI),
`release-docker.yml` (GHCR + Docker Hub), and `release-binaries.yml` (PyInstaller).
The full GA cutover is a separate, human-run checklist:
`docs/superpowers/runbooks/ga-cutover.md`.

### Cutting a release

1. `python scripts/bump_version.py <version>` (e.g. `5.0.0a1` for a pre-release, or
   `5.0.0` for GA), then commit.
2. Tag it: `git tag v<version>` and push the tag.
3. Create a **GitHub Release** from that tag. Publishing the Release triggers
   `release-pypi.yml`, which builds and uploads **in dependency order**:
   `spotdl-core` → `spotdl-server` → `spotdl`. Each wheel is built from local
   workspace sources, so no job waits on PyPI propagation; the ordering only ensures
   a package's `==`-pinned deps already exist on the index by the time it publishes.

Pre-release tags (`v5.0.0aN`) publish `5.0.0aN` to all three projects; because PEP
440 excludes pre-releases by default, `pip install spotdl` keeps serving the last
stable (4.x) release until the GA `5.0.0` tag lands. Users opt in with
`pip install --pre spotdl`.

### PyPI Trusted Publishing (OIDC — no API tokens)

`release-pypi.yml` authenticates to PyPI via **Trusted Publishing** (OpenID
Connect). There is **no PyPI token stored anywhere** — not in the repo, not in
GitHub secrets. Instead, each PyPI project trusts this repo + workflow + environment
directly. This must be configured **once per project** in the PyPI UI:

For **each** of the three projects (`spotdl-core`, `spotdl-server`, `spotdl`):

1. Sign in to <https://pypi.org> as an owner of the project.
2. Go to the project → **Manage** → **Publishing** → **Add a new publisher**
   (GitHub Actions).
3. Fill in:
   - **Owner**: `spotDL`
   - **Repository name**: `spotify-downloader`
   - **Workflow name**: `release-pypi.yml`
   - **Environment name**: `pypi`
4. Save. Repeat for the other two projects.

> For a brand-new project name that does not yet exist on PyPI, use PyPI's
> **"pending publisher"** form (same fields) so the first upload creates the project.

On the GitHub side, each publish job declares `environment: pypi` and
`permissions: id-token: write`. Create the **`pypi` environment** under the repo's
**Settings → Environments**; you may add required reviewers there to gate publishes
behind a manual approval. No secret is added to the environment — OIDC needs none.

### Docker & binaries

- **Docker** (`release-docker.yml`): pushes to GHCR on every `v5` branch build and
  every tag; pushes to Docker Hub (`spotdl/spotify-downloader`, incl. `:latest`)
  only on GA (final) tags. GHCR uses the built-in `GITHUB_TOKEN`; Docker Hub uses
  repo secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`.
- **Binaries** (`release-binaries.yml`): PyInstaller build matrix, uploaded to the
  GitHub Release.

See the GA cutover runbook for the exact ordering, the `legacy-v4` Docker Hub retag,
the `master` branch swap, and rollback steps.
