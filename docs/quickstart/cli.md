# Quickstart: CLI

The `spotdl` command downloads tracks, albums and playlists, keeps local folders
in sync, and re-tags existing files. Metadata and matching come from the server
(the community instance by default); audio is downloaded and tagged on your
machine.

## Download

```bash
# A track, album, playlist or artist URL
spotdl "https://open.spotify.com/track/..."

# A free-text search (resolved to the best match)
spotdl "deadmau5 strobe"

# Several at once
spotdl "https://open.spotify.com/album/..." "https://open.spotify.com/playlist/..."
```

Bare `spotdl <query>` (no sub-command) is shorthand for `spotdl download <query>`.

Common options:

```bash
spotdl "<url>" --output "{artist}/{album}/{title}.{output-ext}"
spotdl "<url>" --format opus --bitrate 320k
spotdl "<url>" --threads 8
```

## Search

```bash
spotdl search "artist - title"
```

Prints a table of candidate results.

## Sync a folder

`sync` keeps a local folder matched to a source (playlist/album). It downloads
what is missing and, by default, prunes local files whose tracks are no longer
in the source.

```bash
# First run: create the save file and download
spotdl sync "https://open.spotify.com/playlist/..." --save-file mymusic.spotdl

# Later runs: refresh from the save file
spotdl sync mymusic.spotdl
```

Use `--no-delete` to keep files that left the source, and `--remove-lrc` to also
delete orphaned `.lrc` lyric files.

## Re-tag existing files

```bash
spotdl meta ./Music/**/*.mp3
```

Resolves metadata for local audio files and rewrites their tags and album art.

## The TUI

Running `spotdl` with **no arguments in a terminal** launches the interactive
TUI. You can also start it explicitly:

```bash
spotdl tui
```

## Choosing where matching happens

By default the CLI uses the community server at `https://api.spotdl.dev`. You can
override this:

```bash
# Force the in-process (embedded) server — fully offline, no network to spotdl.dev
spotdl --offline "<url>"

# Point at your own self-hosted server
spotdl --api-url https://spotdl.example.com "<url>"
```

Precedence is `--api-url` > environment (`SPOTDL_API_URL`) > config file >
built-in default. Downloads always run locally regardless of which server does
the matching. See [Community server usage](../community/usage.md) and its
[etiquette](../community/etiquette.md) for when to self-host instead.

## Coming from v4?

Most v4 commands work unchanged, and the CLI auto-translates the rest. See
[Migrating from v4](../migration/v4-to-v5.md).
