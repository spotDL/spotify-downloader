# Pending Issues and Changelog

## Summary

This document tracks the open issues in the spotify-downloader repository and the changes I applied to resolve them. All changes are on the `ZFork` branch and `master` stays clean.

---

## Issues Resolved

### 1. Duplicate Songs Omitted (Live/Stream Versions)

Songs with the same base name but different versions (Live, Stream, Remaster) were deduplicated incorrectly because the key stripped version markers from the title and album.

- `spotdl/types/song.py`: new `duplicate_key` property that only normalizes whitespace and case, and preserves markers like "(Live)" or "(feat. ...)".
- `spotdl/types/artist.py`: artist song deduplication now uses `song.duplicate_key` instead of the broken slug comparison that never matched.
- `tests/types/test_artist.py`: added tests for live and album variants and for identical tracks.

### 2. M3U Playlist Naming and Portability

The default template `{list[0]}.m3u8` resolves to the Spotify playlist name through `song.list_name`, which is set in `spotdl/utils/search.py` from `song_list.name`.

- `tests/utils/test_m3u.py`: added `test_gen_m3u_files_default_template_uses_playlist_name`.
- `spotdl/utils/m3u.py`: `create_m3u_content` accepts the target m3u file path and writes song entries relative to it with forward slashes, so playlists stay portable across operating systems.

### 3. Issue #2767, Album Sync KeyError 'label'

`Album.get_metadata` crashed with `KeyError: 'label'` when the Spotify API omits the label field.

- `spotdl/types/album.py`: `album_metadata["label"]` is now `album_metadata.get("label", "")`.
- `tests/types/test_album.py`: added `test_album_get_metadata_missing_label` with a mocked client, no network.

### 4. Issue #2729, calc_main_artist_match Discards Correct Results

When the song has multiple artists but the result has one, which is common with YouTube Music, `calc_main_artist_match` returned 0.0 even when the main artists matched exactly, so verified results were discarded.

- `spotdl/utils/matching.py`: the main artist ratio is now always computed first, and the artist match is divided by 2 only when both the song and the result have more than one artist.
- `tests/utils/test_matching.py`: added `test_calc_main_artist_match_multiple_song_artists_single_result_artist` reproducing the exact scenario.

### 5. Issue #2737, Spotify URLs with the /intl-xx/ Locale Prefix

The Web UI rejected localized Spotify URLs such as `https://open.spotify.com/intl-pt/track/...`.

- `spotdl/utils/web.py`: `validate_search_term` normalizes the locale prefix with `re.sub(r"\/intl-\w+\/", "/", ...)`.
- `spotdl/web/routes.py`: `gen_download` normalizes the URL before fetching metadata.
- The CLI path in `spotdl/utils/search.py` already handled this.

### 6. Issue #2680, Web UI Does Not Support Playlist Downloads

The Web UI only handled single track URLs and failed for playlists, albums, and artists.

- `spotdl/web/routes.py`: new `gen_download_from_query` helper parses any Spotify URL type with `get_simple_songs` and downloads all songs through `download_multiple_songs`. The search handler now routes URLs to it.

### 7. Interactive TUI Works Again

`spotdl interactive` was not working on `master` and treated `interactive` as a download query.

- Restored the full TUI from the `ZFork` branch, which includes `spotdl/console/tui/` with 30 files.
- `spotdl/utils/arguments.py`: `interactive` is a valid operation and does not require a query.
- `spotdl/console/entry_point.py`: the auto launch when no arguments are given, the `-nogui` flag, and the `interactive` operation dispatch are all wired up.
- `pyproject.toml` and `uv.lock`: include `textual>=8.0.0,<9`, `pyyaml>=6.0.0,<7`, `pyperclip>=1.8.2,<3`, and `rich>=14.2.0,<16`.
- Verified that `uv run spotdl interactive` launches the TUI and no longer prints "Processing query: interactive".

### 8. Type Errors in Metadata Cover Art

`requests.get` received an optional value because `upgrade_cover_url` returns `Optional[str]`.

- `spotdl/utils/metadata.py`: both cover art requests now fall back to an empty string, which mypy accepts and the existing None guards prevent from being reached.

### 9. First-Run Setup and Configurable Data Directory

A fresh install had no directory for ffmpeg, Deno, config, cache, and history, and the TUI could not run without them.

- `spotdl/utils/setup.py`: new `run_setup` command, wired as `--setup`, that picks one directory for all data and installs or updates ffmpeg and Deno there. It runs interactively or takes a PATH argument.
- `spotdl/utils/config.py`: `get_configured_data_dir` and `set_configured_data_dir` store the chosen directory in a pointer file in the user home, and `get_spotdl_path` returns it when present.
- `spotdl/console/tui/setup_app.py`: Textual setup screen used when the TUI starts without ffmpeg or Deno installed.
- `spotdl/console/tui/app.py`: `run_interactive` triggers the first-run setup automatically when needed, unless `SPOTDL_SKIP_AUTO_SETUP` is set.
- `spotdl/console/tui/screens`: reorganized into `download`, `help`, `home`, and `web` packages, and a new footer bar was added.

---

## Pending Open Issues

### External API or User Configuration

| Issue | Title | Notes |
|-------|-------|-------|
| #2741 | MusixMatch lyrics provider broken with HTTP 403 | TLS fingerprint blocking by MusixMatch, requires an API change or alternative provider |
| #2668 | Genius lyrics searching failing | Genius API change, needs investigation of the search endpoint |
| #2712 | Baseclienterror: could not get session auth tokens | User auth and config specific, cannot reproduce |
| #2766 | Invalid Client | Likely user credentials, needs the user's configuration |
| #2690 | Termux OSError, libpthread.so.0 not found | Platform specific to Termux |
| #2702 | spotdl 4.5.0 not downloading singles | Needs a specific failing case, may be provider specific |

### Feature Requests

| Issue | Title | Notes |
|-------|-------|-------|
| #2768 | Return code 0 for success and non-zero for failure | Exit code handling |
| #2761 | Special handling for explicit songs | Explicit content filtering |
| #2577 | Start a playlist download at a specific point | Offset and range support for large playlists |
| #1937 | Show more than 10 results per page in the Web UI | Pagination improvement |

---

## Changelog

### Added

- `spotdl interactive` command with the full Textual TUI.
- Auto launch of the TUI when running `spotdl` without arguments in a TTY.
- First-run setup that installs ffmpeg and Deno into a chosen data directory, available through `--setup` and through the TUI.
- Configurable data directory through `get_configured_data_dir` and `set_configured_data_dir`.
- `Song.duplicate_key` property for duplicate detection.
- `gen_download_from_query` in the Web UI for playlists, albums, and artists.
- Regression tests for M3U naming, missing album label, artist matching, and duplicate keys.

### Fixed

- Live, studio, and other versions of the same song are no longer merged during deduplication.
- `KeyError: 'label'` during album sync when the label field is missing.
- `calc_main_artist_match` no longer discards valid single-artist results.
- Web UI accepts and downloads Spotify URLs with the `/intl-xx/` locale prefix.
- Web UI downloads playlists, albums, and artists instead of failing on non-track URLs.
- `spotdl interactive` launches the TUI instead of being treated as a download query.
- Two mypy errors in `spotdl/utils/metadata.py` cover art requests.

### Changed

- Artist deduplication uses the normalized title, album, and artist key.
- Artist match division only applies when both the song and the result have multiple artists.
- M3U entries are written relative to the playlist file with forward slashes for portability.
- TUI screens reorganized into `download`, `help`, `home`, and `web` packages.
- Dependencies updated for the TUI: `rich>=14.2.0,<16`, `textual>=8.0.0,<9`, `pyyaml>=6.0.0,<7`, `pyperclip>=1.8.2,<3`.

---

## Quality Gates

| Check | Status |
|-------|--------|
| Unit tests (mocked, no network) | 13 passing |
| mypy | Clean on 89 source files |
| pylint | 10.00/10 |
| black | Clean |
| isort | Clean |