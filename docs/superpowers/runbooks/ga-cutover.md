# spotDL v5 GA-cutover runbook

> **Status: DOCUMENTED, NOT EXECUTED.** This is Plan 11 Task 12. It is the ordered
> checklist a human release manager follows to promote spotDL v5 from pre-release to
> General Availability. **No command in this file is run as part of Plan 11.** Every
> step lists its exact command and owner; nothing here fires automatically.

The cutover flips three public surfaces at once — PyPI (`pip install spotdl` starts
returning 5.0.0), Docker Hub (`spotdl/spotify-downloader:latest` becomes the v5
image), and the GitHub default branch (`master` starts showing v5). The whole point
of this runbook is that those flips happen in a **safe order** with a **rollback for
each**, and that v4 users are given a stable `legacy-v4` pin **before** anything
flips out from under them.

Owners referenced below:

- **RM** — Release Manager (drives the cutover, holds PyPI + Docker Hub + GitHub
  admin).
- **Ops** — whoever owns the Railway project + Cloudflare zone.

---

## Preconditions (verify ALL before starting — RM + Ops)

Do not begin the cutover until every box is green:

- [ ] **PyPI Trusted Publishers configured** for all three projects (`spotdl-core`,
      `spotdl-server`, `spotdl`): repo `spotDL/spotify-downloader`, workflow
      `release-pypi.yml`, environment `pypi`. See `docs/contributing.md` →
      "PyPI Trusted Publishing". No API token is stored; OIDC must already be wired.
- [ ] **GitHub `pypi` environment exists** (Settings → Environments) — the publish
      jobs reference `environment: pypi`.
- [ ] **Docker Hub secrets present**: repo secrets `DOCKERHUB_USERNAME` and
      `DOCKERHUB_TOKEN` (the token must have push rights to `spotdl/spotify-downloader`).
      GHCR needs no secret — it uses the built-in `GITHUB_TOKEN` with `packages: write`.
- [ ] **Railway production healthy** (see Step 1) — the community server must already
      be live in `hosted` mode before the CLI's pinned default points users at it.
- [ ] **CLI default already pinned** to the community domain: `DEFAULT_API_URL =
      https://api.spotdl.dev` (Plan 11 Task 6). Confirm it is HTTPS and not localhost.
- [ ] **Version chosen and consistent**: run `python scripts/bump_version.py --check`
      on the release commit — it must report a single agreed version. The GA version
      is a final PEP 440 number (e.g. `5.0.0`), i.e. it contains no `a` (that is how
      `release-docker.yml` distinguishes GA from a pre-release).
- [ ] **A recent pre-release was exercised**: at least one `v5.0.0aN` tag has already
      published to PyPI/GHCR and been smoke-tested with `pip install --pre spotdl`.

---

## Step 1 — Confirm the community server is live (Ops)

The CLI's shipped default points every fresh install at the community server, so it
MUST be live and healthy in `hosted` mode before GA.

```sh
# Health + metrics on the Cloudflare-fronted Railway production domain.
curl -fsS https://api.spotdl.dev/api/v1/health         # -> {"status":"ok"}
curl -fsS https://api.spotdl.dev/metrics | grep spotdl_ # Prometheus metrics present
```

- [ ] `/api/v1/health` returns `{"status":"ok"}`.
- [ ] `/metrics` returns Prometheus text with the `spotdl_*` families.
- [ ] Railway production is running the intended image tag, `numReplicas = 1`,
      managed Postgres + Redis attached (see `deploy/railway.toml` and
      `docs/self-hosting/railway.md`).

If this step is not green, **stop** — do not cut GA against a dead community server.

---

## Step 2 — Retag the current v4 Docker image as `legacy-v4` (RM) — BEFORE the GA tag

> **ORDERING IS LOAD-BEARING.** Pushing the GA tag (`git push origin v5 --tags`,
> Step 3) triggers `release-docker.yml` (it fires on tag push, not on the Release),
> whose `dockerhub` job **moves `:latest` to the v5 image**. So the v4 `:latest`
> must be preserved under a stable `legacy-v4` tag *first*, while `:latest` still
> points at v4. Do this step, verify it, then proceed to Step 3.

```sh
# Preserve today's v4 :latest under legacy-v4 (no rebuild; copies the manifest list,
# preserving multi-arch). Run while :latest is STILL the v4 image.
docker buildx imagetools create \
  --tag docker.io/spotdl/spotify-downloader:legacy-v4 \
  docker.io/spotdl/spotify-downloader:latest

# Verify the new tag resolves and note its digest for the rollback record.
docker buildx imagetools inspect docker.io/spotdl/spotify-downloader:legacy-v4
```

Fallback if `imagetools` is unavailable (single-arch pull/retag/push):

```sh
docker pull  docker.io/spotdl/spotify-downloader:latest
docker tag   docker.io/spotdl/spotify-downloader:latest \
             docker.io/spotdl/spotify-downloader:legacy-v4
docker push  docker.io/spotdl/spotify-downloader:legacy-v4
```

- [ ] `legacy-v4` exists on Docker Hub and resolves to the current v4 image.
- [ ] **Record the v4 `:latest` digest here** (needed to roll `:latest` back):
      `________________________________`
- [ ] Announce to v4 users (README / Discord / docs migration page) that pinning
      `spotdl/spotify-downloader:legacy-v4` keeps them on v4.

---

## Step 3 — Tag GA and publish the GitHub Release (RM)

This is the trigger that fans out to all three release workflows.

```sh
# On the release commit (v5 branch), set the final version everywhere and commit.
python scripts/bump_version.py 5.0.0
git commit -am "release: spotDL 5.0.0"

# Tag and push. The GitHub Release (next) is what fires the publish workflows.
git tag v5.0.0
git push origin v5 --tags

# Create the GitHub Release from the tag (publishing it triggers the workflows).
gh release create v5.0.0 --title "spotDL 5.0.0" --notes-file <release-notes.md>
```

Two distinct triggers fire here — know which command does what:

1. **The tag push** (`git push origin v5 --tags`, above) triggers
   **`release-docker.yml`** — GHCR gets `5.0.0`, `5.0`, `sha-<short>`, and (GA
   only) `latest`; the `dockerhub` job (final-tag-gated) pushes
   `spotdl/spotify-downloader` including `:latest`. **This is the moment
   `:latest` flips to v5** — hence Step 2 ran first.
2. **Publishing the GitHub Release** triggers, in parallel:
   - **`release-pypi.yml`** — builds & publishes **in dependency order**
     `spotdl-core` → `spotdl-server` → `spotdl` (each pinned
     `spotdl-server==5.0.0` etc.), via OIDC Trusted Publishing (no token).
   - **`release-binaries.yml`** — PyInstaller matrix (linux/macos/windows +
     aarch64), uploaded to the GitHub Release.

- [ ] All three workflows go green (watch the Actions tab; do not proceed on a red
      publish).
- [ ] PyPI shows `spotdl 5.0.0`, `spotdl-server 5.0.0`, `spotdl-core 5.0.0`.
- [ ] Docker Hub `:latest` and `:5.0.0` are the v5 image; GHCR `:latest`/`:5.0.0`
      likewise; `legacy-v4` still points at v4.

---

## Step 4 — `master` branch swap (RM, GitHub admin)

The stable v4 tree stays on `master` until this step. v4 is already preserved out of
band — `~/Projects/xnetcat/spotdl-v4-reference/`, full git history, and the
**`v4-final` tag** — so the swap is reversible.

```sh
# 1. Immortalize the current v4 master as an annotated tag (idempotent if it exists).
git fetch origin
git tag -a v4-final origin/master -m "Final v4 release tree" || true
git push origin v4-final

# 2A. PREFERRED: make v5 the default branch (keeps master's v4 history intact).
#     GitHub: Settings → Branches → Default branch → switch to `v5` → confirm.
#     (Or via API/CLI:)
gh api -X PATCH repos/spotDL/spotify-downloader -f default_branch=v5

# 2B. ALTERNATIVE (if the team wants v5 to live on `master`): merge v5 into master
#     with history preserved. Only do this after 2A is agreed against.
#     git checkout master && git merge --no-ff v5 && git push origin master
```

- [ ] `v4-final` tag pushed and visible on GitHub.
- [ ] Default branch is now `v5` (or `master` now holds v5 per the chosen option).
- [ ] Branch protections / required checks re-pointed at the new default branch.
- [ ] Open PRs re-based / retargeted as needed.

**Rollback for the swap:** set the default branch back to `master` (Settings →
Branches, or `gh api -X PATCH … -f default_branch=master`). No history is lost — the
v4 tree is on `master` + `v4-final`; the v5 tree stays on `v5`.

---

## Step 5 — Deploy the v5 docs site (RM)

```sh
# docs.yml deploys on pushes to v5 touching docs/**; trigger manually if needed.
gh workflow run docs.yml --ref v5
```

- [ ] `docs.yml` (mkdocs `gh-deploy`) succeeds.
- [ ] The **migration guide** renders — open `Migrating from v4` (generated from the
      CLI `V4_FLAG_TABLE`) and confirm the flag table + `.spotdl` auto-migration
      section are present and not stale (the drift-check job must be green).
- [ ] The API reference (Swagger UI over the committed `apps/server/openapi.json`)
      loads.

---

## Step 6 — Post-cutover smoke (RM) — prove the public surfaces from a clean machine

Run on a machine/container with no spotDL installed.

```sh
# PyPI: a plain install (NO --pre) must now resolve to the GA version.
python -m venv /tmp/ga && . /tmp/ga/bin/activate
pip install spotdl
python -c "import importlib.metadata as m; assert m.version('spotdl')=='5.0.0', m.version('spotdl')"
spotdl --version        # prints 5.0.0

# Docker: latest must boot and pass health.
docker run -d --name ga-smoke -e SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32) \
  -p 8000:8000 spotdl/spotify-downloader:latest
curl -fsS http://localhost:8000/api/v1/health    # {"status":"ok"}
docker rm -f ga-smoke

# Binary: the release asset for this platform runs (bare invocation -> TUI).
#   download the asset from the GitHub Release, then:
./spotdl-5.0.0-<platform> --version               # exit 0, prints 5.0.0
```

- [ ] `pip install spotdl` (no `--pre`) yields `5.0.0`.
- [ ] `docker pull spotdl/spotify-downloader:latest` boots and passes `/api/v1/health`.
- [ ] A release binary runs and reports `5.0.0`.
- [ ] `legacy-v4` still pulls the v4 image (v4 users unaffected).

Cutover complete.

---

## Rollback

Each flip has an independent, fast rollback. Roll back the smallest surface that is
broken; you do not have to undo everything.

### Bad PyPI release

PyPI uploads are immutable — you cannot re-upload the same version. **Yank** the bad
release so resolvers skip it (existing pins still work, new installs avoid it):

- PyPI UI: project → **Manage** → **Releases** → the version → **Options → Yank**.
- Then ship a fixed **post-release**: `python scripts/bump_version.py 5.0.0.post1`,
  re-tag, re-release. `pip install spotdl` resolves to the post-release.
- Yanking `spotdl` (the CLI) is usually enough; yank `spotdl-server` / `spotdl-core`
  too only if the defect is in those wheels.

### Docker `:latest` regressed

Repoint `:latest` back to the previous digest recorded in Step 2 (or to the last-good
v5 tag):

```sh
# Roll :latest back to the recorded v4 digest (full revert to v4):
docker buildx imagetools create \
  --tag docker.io/spotdl/spotify-downloader:latest \
  docker.io/spotdl/spotify-downloader:legacy-v4

# Or roll forward/back to a specific good v5 build:
docker buildx imagetools create \
  --tag docker.io/spotdl/spotify-downloader:latest \
  docker.io/spotdl/spotify-downloader:5.0.0
```

`legacy-v4` is never modified by the workflows, so it is always a safe `:latest`
target.

### Branch swap regretted

Set the GitHub default branch back to `master` (Settings → Branches, or
`gh api -X PATCH repos/spotDL/spotify-downloader -f default_branch=master`). The v4
tree is intact on `master` + `v4-final`; the v5 tree stays on `v5`. Re-point branch
protections back to `master`.

### Community server unhealthy after cutover (Ops)

Roll the Railway production service back to the previous healthy image tag (Railway
→ Deployments → redeploy the prior deploy), or promote the staging environment's
known-good tag. Cloudflare can serve a maintenance page in the interim. Because the
CLI default points at `api.spotdl.dev`, keeping that domain healthy is the priority.

---

## Verification of this document (Plan 11 Task 12, Step 3)

This runbook is **doc-only**; no command in it was executed during Plan 11. It is not
part of the mkdocs site `nav` (it lives under `docs/superpowers/runbooks/`), so
`mkdocs build --strict` does not link it; it is validated by review and Markdown
sanity only.
