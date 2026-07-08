# spotDL v5

Ground-up rewrite of spotify-downloader as a monorepo: a self-hostable
server (metadata, search, matching, lyrics, community curation), the
`spotdl` CLI/TUI, and a web UI.

**Status: pre-alpha rewrite.** Stable v4 lives on the `master` branch.

- Design spec: `docs/superpowers/specs/2026-07-08-v5-monorepo-rewrite-design.md`
- Layout: `apps/server`, `apps/cli`, `apps/web`, `packages/core`

## Development

Requires: uv, Python 3.13+, pnpm 9, Node 22+.

    make sync        # install python workspace
    make web-install # install web deps
    make check       # lint + typecheck + test everything
