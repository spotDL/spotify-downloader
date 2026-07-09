<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# spotDL v5

**Download music from Spotify metadata — with tags, album art and lyrics —
matched from YouTube and other providers.**

[![PyPI version](https://img.shields.io/pypi/v/spotdl?include_prereleases&label=pypi)](https://pypi.org/project/spotdl/)
[![Python](https://img.shields.io/pypi/pyversions/spotdl)](https://pypi.org/project/spotdl/)
[![Docker image](https://img.shields.io/badge/ghcr.io-spotdl%2Fspotify--downloader-blue?logo=docker)](https://github.com/spotDL/spotify-downloader/pkgs/container/spotify-downloader)
[![Docs](https://img.shields.io/badge/docs-spotdl.dev-green)](https://spotdl.dev)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord)](https://discord.gg/xCa23pwJWH)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

</div>

> [!WARNING]
> **spotDL v5 is a pre-release, in-progress ground-up rewrite** living on the
> `v5` branch. **Stable v4 remains on the `master` branch and is what a plain
> `pip install spotdl` installs until v5 reaches general availability (GA).**
> To try v5 today, use the pre-release install below.

---

## What v5 is

spotDL v4 was a single monolithic CLI. v5 splits into one codebase that runs as:

- **a server** — resolves Spotify metadata, searches audio providers, **ranks
  matches** (refined by community voting), and serves lyrics;
- **the `spotdl` CLI and a built-in TUI**;
- **a web UI**, bundled inside the package (no runtime download).

You use all three from the same `spotdl` install, and pick where matching runs:
the free **community server** (`api.spotdl.dev`), an **embedded** in-process
server (fully offline), or your own **self-hosted** instance. Downloading always
happens locally. No Spotify API keys are needed — metadata is served by the
server.

## Install

```bash
# Pre-release (installs v5):
pip install --pre spotdl

# After GA, a plain install will get v5:
pip install spotdl
```

spotDL needs **Python 3.13+** and **FFmpeg** (`spotdl ffmpeg download`, or your
package manager). Standalone binaries and a Docker image are also published —
see the [installation docs](https://spotdl.dev/installation/).

## Quickstart

```bash
# Download a track, album, playlist or artist
spotdl "https://open.spotify.com/track/..."

# Free-text search
spotdl "deadmau5 strobe"

# No arguments in a terminal → launches the interactive TUI
spotdl

# The bundled web UI
spotdl web

# Keep a folder in sync with a playlist
spotdl sync "https://open.spotify.com/playlist/..." --save-file mymusic.spotdl
```

By default the CLI uses the community server for metadata/matching. Force the
offline embedded server with `--offline`, or point at your own with
`--api-url https://spotdl.example.com`.

## Migrating from v4

**Most v4 commands work unchanged, and the CLI auto-translates the rest** (renamed
flags are rewritten with a note; obsolete no-ops are ignored; removed flags fail
fast with a pointer). See the generated, always-in-sync guide:

➡️ **[Migrating from spotDL v4](https://spotdl.dev/migration/v4-to-v5/)**

## Community server & self-hosting

- **Community server** — the shared instance at [spotdl.dev](https://spotdl.dev)
  (API `https://api.spotdl.dev`). It is cache-first and rate-limited; please read
  the [etiquette & fair-use guide](https://spotdl.dev/community/etiquette/), and
  self-host or use `--offline` for heavy/automated use.
- **Self-hosting** — run your own with the same Docker image the community
  instance uses:

  ```bash
  export SPOTDL_AUTH_SECRET_KEY=$(openssl rand -hex 32)
  docker compose -f deploy/docker-compose.selfhost.yml up -d
  ```

  See the [self-hosting docs](https://spotdl.dev/self-hosting/docker/) for
  Postgres, reverse proxies, Railway and [backups](https://spotdl.dev/self-hosting/backups/).

## Documentation

Full docs live at **[spotdl.dev](https://spotdl.dev)**:
[installation](https://spotdl.dev/installation/) ·
[CLI](https://spotdl.dev/quickstart/cli/) ·
[web UI](https://spotdl.dev/quickstart/web/) ·
[self-hosting](https://spotdl.dev/self-hosting/docker/) ·
[API reference](https://spotdl.dev/api/) ·
[migrating from v4](https://spotdl.dev/migration/v4-to-v5/).

## Contributing

Issues and PRs are welcome — see [`docs/contributing.md`](docs/contributing.md).
Development and support happen on the
[spotDL Discord](https://discord.gg/xCa23pwJWH).

```bash
make sync          # install the Python workspace
make web-install   # install web deps
make check         # lint + typecheck + test (Python + web)
```

## Legal

spotDL downloads metadata from Spotify and audio from providers such as YouTube.
Use it only for content you are legally permitted to download. spotDL is not
affiliated with Spotify or any provider. Released under the [MIT license](LICENSE).
