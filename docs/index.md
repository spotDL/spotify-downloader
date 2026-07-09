# spotDL

**spotDL finds the music that matches your Spotify metadata and downloads it —
with tags, album art and lyrics — from YouTube and other providers.**

spotDL **v5** is a ground-up rewrite. Instead of a monolithic CLI, it is now:

- a **server** that resolves metadata, searches providers, ranks audio matches
  (with community voting) and serves lyrics;
- the **`spotdl` CLI** and a built-in **TUI**;
- a **web UI**, bundled in the package (no runtime download).

You can use spotDL three ways, all from the same `spotdl` package:

| Mode | What runs | Best for |
|---|---|---|
| **Community server** | The CLI talks to the shared instance at `api.spotdl.dev` | Getting started, occasional use |
| **Embedded** | The CLI runs the server in-process on your machine | Offline / private use, heavy downloading |
| **Self-hosted** | You run the server (Docker/Railway) for your household or team | A shared instance you control |

!!! warning "Pre-release"
    v5 is a pre-release. A plain `pip install spotdl` still installs the stable
    **v4** line until v5 reaches general availability (GA). See
    [Installation](installation.md) for how to try the pre-release, and
    [Migrating from v4](migration/v4-to-v5.md) if you are coming from v4.

## Quick start

```bash
pip install --pre spotdl        # pre-release; installs v5
spotdl "https://open.spotify.com/track/..."   # download a track
spotdl                          # no arguments in a terminal → launches the TUI
```

The CLI defaults to the community server at `https://api.spotdl.dev` for
metadata and matching, and downloads audio locally. No Spotify API keys are
required — metadata is served by the server.

## Where to next

- **[Installation](installation.md)** — pip, pipx, Docker, standalone binary.
- **[Quickstart: CLI](quickstart/cli.md)** — the everyday commands.
- **[Quickstart: Web UI](quickstart/web.md)** — the bundled browser app.
- **[Community server](community/usage.md)** — using the shared instance, and
  its **[etiquette & fair use](community/etiquette.md)**.
- **[Self-hosting](self-hosting/docker.md)** — run your own with Docker, a
  reverse proxy, or Railway, plus [backups](self-hosting/backups.md).
- **[Migrating from v4](migration/v4-to-v5.md)** — what changed and how the CLI
  auto-translates v4 commands.
- **[API reference](api/index.md)** — the server's HTTP API.

## Legal

spotDL downloads metadata from the Spotify catalog and audio from providers such
as YouTube. Use it only for content you are legally permitted to download. spotDL
is not affiliated with Spotify or any provider. Released under the MIT license.
