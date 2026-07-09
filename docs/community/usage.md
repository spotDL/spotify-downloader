# Community server

spotDL runs a free, shared community instance so you can use the tool without
running any infrastructure. The CLI talks to it by default.

- **Web UI / docs:** [spotdl.dev](https://spotdl.dev)
- **API base URL:** `https://api.spotdl.dev`

## What the community server does

- Resolves Spotify metadata (tracks, albums, artists, playlists).
- Searches audio providers and **ranks candidate matches**.
- Serves lyrics.
- Collects **community votes** on matches and lyrics so results improve over
  time, and accepts reports of bad matches.

What it does **not** do: it does not download audio for you. Downloading happens
on your machine (CLI/embedded server or your self-hosted instance). The shared
instance is metadata + matching + curation only.

## Accounts

Browsing, searching and resolving work anonymously. **Voting, submitting
matches and reporting** require an account so curation stays accountable. Create
one from the web UI or:

```bash
spotdl auth login
```

`spotdl auth *` always talks to the remote server (never the embedded one).

## Using it from the CLI

Nothing to configure — the default API URL is `https://api.spotdl.dev`. To be
explicit, or to override for one command:

```bash
spotdl --api-url https://api.spotdl.dev "<url>"
```

If the community server is unreachable, the CLI transparently falls back to the
in-process embedded server (with a one-line notice) so downloads still work.
`--offline` skips the probe entirely.

## Be a good neighbour

The shared instance is a common resource with rate limits. Please read
[Etiquette & fair use](etiquette.md) — in short: it is cache-first and
rate-limited, and heavy or automated use should run against your own
[self-hosted](../self-hosting/docker.md) or embedded server.
