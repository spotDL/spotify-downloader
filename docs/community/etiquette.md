# Etiquette & fair use

The community server at `api.spotdl.dev` is a **free, shared resource** paid for
and operated by volunteers. A few rules keep it fast and available for everyone.

## It is cache-first

Metadata the server has seen before is served from a permanent snapshot cache —
that is what makes it fast and cheap to run. When you resolve a popular album,
you are almost always hitting warm cache. Please:

- **Resolve the entity you actually want** (an album/playlist URL) rather than
  looping thousands of individual track lookups.
- **Don't bust the cache** with churn — repeated identical requests in a tight
  loop provide no benefit and burn shared capacity.

## It is rate-limited

The server enforces per-client rate limits (backed by Redis on the hosted
instance). If you hit them you will get `429` responses; back off and retry
rather than hammering. The limits are sized for interactive, human-paced use.

## Heavy or automated use → self-host or embedded

If you are doing any of the following, **do not** point it at the community
instance:

- Bulk-downloading large libraries or many playlists back-to-back.
- Running spotDL from a script, cron job, CI pipeline or bot.
- Building something on top of the API.

Instead, run matching locally. Both are free and give you no rate limits:

- **Embedded** — add `--offline` (or set your API URL to the embedded server).
  The CLI runs the server in-process; nothing touches `spotdl.dev`.

    ```bash
    spotdl --offline "<url>"
    ```

- **Self-hosted** — run your own instance and point the CLI at it. See
  [Self-hosting](../self-hosting/docker.md).

    ```bash
    spotdl --api-url https://spotdl.example.com "<url>"
    ```

The community server exists to get people started and to pool curation (votes,
reports). Downloading is always local anyway — so moving heavy work off the
shared instance costs you nothing and keeps it healthy for the next person.

## Curate, don't abuse

Votes and reports make matches better for everyone. Please vote honestly and
report genuinely bad matches — don't game the ranking.
