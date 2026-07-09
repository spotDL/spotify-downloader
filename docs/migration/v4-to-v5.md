<!-- GENERATED FILE — do not edit by hand.
     Source: spotdl_cli.shim (V4_FLAG_TABLE + SPOTDL_FIELD_TABLE), rendered by
     scripts/docs/gen_migration_guide.py. Run `make docs` to regenerate. -->

# Migrating from spotDL v4

spotDL v5 is a ground-up rewrite (server + CLI/TUI + web UI). Most everyday `spotdl` commands work exactly as before — `spotdl <url>` still downloads. The CLI ships a **compat shim** that translates a v4 invocation on the fly: renamed flags are rewritten (with a one-line note), obsolete no-ops are ignored (with a warning), and flags whose behavior genuinely moved server-side fail fast with a pointer to the replacement.

> Stable v4 remains installed by a plain `pip install spotdl` until v5 reaches GA. This guide is generated from the CLI's translation table, so it is always in sync with what the shim actually does.

## What changed at a glance

- **Metadata, search and matching are server-side.** No Spotify client ID/secret on your machine — the community server (or your self-hosted one) serves metadata and ranks audio matches; community voting refines them.
- **The web UI is bundled** in the package (spec §8) — no runtime GitHub fetch.
- **TLS terminates at a reverse proxy** for self-hosting (see the [self-hosting docs](../self-hosting/reverse-proxy.md)), not via client flags.
- **`.spotdl` files are auto-migrated** from v4's bare array to the v2 format on load.

## Flag translation table

Every v4 `arguments.py` flag is accounted for below, grouped by how the shim treats it.

### Unchanged flags (SAME)

These flags keep the same name and meaning — copy them across verbatim.

| v4 flag | v5 form / pointer |
|---|---|
| `--output` | `--output` (output template incl. dir) |
| `--format` | `--format` |
| `--bitrate` | `--bitrate` |
| `--overwrite` | `--overwrite` |
| `--restrict` | `--restrict` (`--restrict` with no value → `--restrict strict`) |
| `--m3u` | `--m3u` (optional value; default `{list[0]}.m3u8`) |
| `--save-file` | `--save-file` |
| `--archive` | `--archive` |
| `--cookie-file` | `--cookie-file` |
| `--proxy` | `--proxy` |
| `--threads` | `--threads` (download concurrency) |
| `--ffmpeg` | `--ffmpeg` (executable path) |
| `--ffmpeg-args` | `--ffmpeg-args` |
| `--yt-dlp-args` | `--yt-dlp-args` |
| `--sponsor-block` | `--sponsor-block` |
| `--generate-lrc` | `--generate-lrc` |
| `--save-errors` | `--save-errors` |
| `--print-errors` | `--print-errors` |
| `--skip-explicit` | `--skip-explicit` |
| `--detect-formats` | `--detect-formats` |
| `--max-filename-length` | `--max-filename-length` |
| `--id3-separator` | `--id3-separator` |
| `--playlist-numbering` | `--playlist-numbering` |
| `--add-unavailable` | `--add-unavailable` |
| `--create-skip-file` | `--create-skip-file` |
| `--respect-skip-file` | `--respect-skip-file` |
| `--log-level` | `--log-level` |
| `--host / --port` | `--host` / `--port` (on `web`/`server`) |
| `--version / -v` | `--version` (global eager flag printing the version; `spotdl version` also works) |

### Renamed flags (RENAME)

These flags were renamed. `spotdl` auto-translates a v4 invocation and prints a one-line note; update your scripts to the v5 form.

| v4 flag | v5 form / pointer |
|---|---|
| `--scan-for-songs` | `--scan` |
| `--playlist-retain-track-cover` | `--retain-track-cover` — **documented behavior gap:** v4's flag *also* set each track's album name to the playlist name; v5's `--retain-track-cover` only retains per-track cover art. To get the album-name override too, combine with `--playlist-numbering`. The rendered migration guide carries this note verbatim. |
| `--sync-without-deleting` | `--no-delete` (on `sync`) |
| `--sync-remove-lrc` | `--remove-lrc` (on `sync`) |
| `--redownload` | `--redownload` (on `meta`; kept) |
| `--skip-album-art` | `--skip-album-art` (on `meta`; kept) |
| `--force-update-metadata` | `--overwrite metadata` |
| `--download-ffmpeg` | `spotdl ffmpeg download` (operation → subcommand) |
| `--generate-config` | `spotdl config edit` |

### Obsolete no-ops (SOFT-DROP)

These flags became no-ops (their behavior is automatic in v5). They are stripped with a warning and execution continues.

| v4 flag | v5 form / pointer |
|---|---|
| `--config` | config is auto-loaded from `config.toml` in v5 — the flag is unnecessary and was ignored |
| `--preload` | downloads are queued and prefetched automatically in v5 — the flag was ignored |

### Removed flags (DROP)

These flags named behavior the client no longer performs. `spotdl` fails fast with a pointer to the replacement.

| v4 flag | v5 form / pointer |
|---|---|
| `--audio` | audio-source matching is server-side now; the server ranks providers and community voting refines matches |
| `--lyrics` | lyrics providers are server-side; use `--generate-lrc` for `.lrc`, and vote on lyrics in the TUI/web |
| `--genius-access-token` | lyrics are fetched server-side; no client token needed |
| `--client-id / --client-secret / --auth-token / --user-auth` | Spotify credentials are no longer client-side; the community server serves metadata (self-host: set operator creds on the server) |
| `--cache-path / --no-cache / --use-cache-file` | metadata caching is server-side (permanent snapshot cache) |
| `--headless / --max-retries` | Spotify auth/retry is a server concern now |
| `--search-query / --dont-filter-results / --only-verified-results / --album-type` | matching/search tuning is server-side (versioned matcher); community voting refines results |
| `--ytm-data` | metadata source selection is server-side |
| `--fetch-albums / --ignore-albums` | resolve albums explicitly (`spotdl download album:<name>` / album URL) |
| `--simple-tui` | the plain Rich progress is the default non-TTY renderer; there is no separate simple TUI |
| `--log-format` | custom logging formats were removed; use `--log-level` |
| `--profile / --check-for-updates` | removed (use your OS profiler / `pip install -U spotdl`) |
| `--web-gui-repo / --web-gui-location / --force-update-gui` | the web UI is bundled in the package now — no runtime GitHub fetch (spec §8) |
| `--keep-alive / --keep-sessions / --web-use-output-dir / --allowed-origins` | web-server session model changed; run `spotdl web` (embedded, single-user) or `spotdl server --mode selfhost` |
| `--enable-tls / --cert-file / --key-file / --ca-file` | terminate TLS at a reverse proxy (see the self-host deploy docs / `deploy/`) |

## `.spotdl` file auto-migration

v4's `.spotdl` save file was a bare JSON array of `Song.asdict`. v5 uses the structured **v2** format (`{version: 2, kind, name, source, created_at, matcher_version, songs: [...]}`). `spotdl` detects a v4 file by its top-level JSON type (a list ⇒ v4) and migrates it in memory on load; the migrated form is only written back to disk when a command emits a new `.spotdl` (then it is v2).

| v4 field | v5 (`.spotdl` v2) field | Notes |
|---|---|---|
| (top-level bare array) | `SaveFileV2.songs[]` | v4's `.spotdl` was a bare JSON array of `Song.asdict`; v5 wraps it in `{version: 2, ...}`. |
| `name` | `SaveFileSong.name` | Track title, copied through. |
| `artists` | `SaveFileSong.artists` | Artist list, copied through. |
| `duration` | `SaveFileSong.duration` | v4 stored **seconds**; v5 stores **milliseconds** (s → ms). |
| `download_url` | `SaveFileSong.match.url` | Moved under the per-track `match`; audio-target URL. |
| `list_name` / `album_name` | `SaveFileV2.kind` + `.name` | Used to infer `kind` (`playlist`/`album`/`single`) and the collection `name`. |
| (audio host of `download_url`) | `SaveFileSong.match.provider` | Inferred from the URL host (`youtu.be`→`youtube`, `music.youtube.com`→`youtube-music`, `soundcloud.com`→`soundcloud`, `*.bandcamp.com`→`bandcamp`, unknown→`youtube`) — never a validation failure. |
| (file mtime) | `SaveFileV2.created_at` | v4 files carry no timestamp; the loader uses the file mtime (ISO-8601). |
| (none) | `SaveFileV2.matcher_version` | `null` for migrated v4 files (no matcher provenance existed). |
| (none) | `SaveFileV2.source` | `null` — v4 files record no originating URL. |
