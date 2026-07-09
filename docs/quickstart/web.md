# Quickstart: Web UI

spotDL ships a browser UI **bundled inside the package** — there is no runtime
download of a separate front-end. It is served by the same server that powers
the CLI.

## Run it locally

```bash
spotdl web
```

This starts the server in embedded mode and opens the UI (default
`http://localhost:8000`). Search for tracks, queue downloads and watch progress
live.

Options:

```bash
spotdl web --host 0.0.0.0 --port 8080
```

## Self-hosted

If you self-host the server (see [Docker & Compose](../self-hosting/docker.md)),
the web UI is served at the root of your instance automatically — the same build
is embedded in the Docker image and the PyPI wheel, so every deployment serves
the UI with no extra steps.

## Community instance

The community server at [spotdl.dev](https://spotdl.dev) also serves the web UI
for browsing and voting on matches. Heavy downloading should be done from the
CLI/embedded server or your own instance — see the
[etiquette guide](../community/etiquette.md).
