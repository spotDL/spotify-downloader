# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Interactive Terminal User Interface (TUI) based on Textual, launched via `spotdl interactive` or by invoking `spotdl` without arguments in a terminal.
- First-run setup wizard (`spotdl --setup` or within the TUI) with automatic dependency checking and installation for FFmpeg and Deno.
- Configurable data directory support via `get_configured_data_dir` and `set_configured_data_dir`.
- Real-time command generation in the CLI Command Builder with synchronized parameter updates.
- Live search filtering and column sorting in the Download History view.
- Single-click row selection and spacebar toggle in the tracklist download screen with custom checkbox icons.
- Download presets (Lightest, Efficient, Balanced, Studio) and 96 kbps bitrate quality option.
- Internationalization (i18n) support with on-the-fly language switching between English and Spanish across all screens, modals, and tables.
- Real-time search status callbacks in `get_simple_songs` and `QueryScreen` providing live feedback during metadata resolution.
- Multi-stage dynamic colored progress bars for per-song downloads reflecting real-time query, download, conversion, and metadata embedding stages.
- Card-based confirmation interface displaying organized options for audio formats, bitrates, providers, lyrics, and directory destinations.
- Cached track preservation when modifying download options to prevent redundant Spotify search queries.
- New `Song.duplicate_key` property to accurately differentiate track variants such as live, remaster, and studio versions during deduplication.
- Public keyless `Lrclib` lyrics provider fetching synced and plain lyrics without requiring API credentials.
- Default YouTube fallback in audio provider search chain when YouTube Music returns no candidate matches.
- Double-click Windows launcher batch file (`launch_tui.bat`) for command-free startup.
- Incremental archive persistence writing downloaded URLs immediately after each track finishes to prevent progress loss.
- Comprehensive user guide for the interactive terminal interface in `docs/TUI_USER_GUIDE.md`.
- Regression test suites covering TUI interactions, duplicate version handling, artist matching penalties, and M3U playlist generation.

### Changed
- Optimized Spotify search track resolution using `Song.from_track_dict` to construct track objects directly from search responses, eliminating redundant HTTP calls for track, artist, and album metadata.
- Optimized audio provider candidate search in `Downloader.search_all` to avoid secondary search requests when the primary query produces a valid match.
- Refactored main menu into a responsive action card grid layout inspired by Parabolic with short labels and detailed hover tooltips.
- Updated M3U generation to write track entries relative to the target playlist file using forward slashes for cross-platform portability.
- Enhanced M3U playlist file naming to dynamically resolve downloaded playlist names (with album and first track fallbacks) and replace generic filename placeholders automatically.
- Restructured artist matching calculation to evaluate primary artist ratio before applying multi-artist penalties.
- Refined duration matching curve in audio matching to gracefully handle slight music video intro/outro length variances without discarding valid releases.
- Reorganized TUI screen architecture into `download`, `help`, `home`, and `web` modules.
- Updated dependencies to include `textual>=8.0.0,<9`, `pyyaml>=6.0.0,<7`, `pyperclip>=1.8.2,<3`, and `rich>=14.2.0,<16`.

### Fixed
- Fixed real-time language switching not propagating to form labels, input placeholders, select dropdown options, confirmation screens, download progress tables, directory modals, and lyrics views.
- Fixed audio provider matching picking parodies or unrelated videos by adding `parody`, `amv`, `animatic`, `mashup`, and `parodia` to forbidden words penalties.
- Fixed YouTubeMusic audio provider language setting and duration seconds extraction to prevent false zero-duration match failures.
- Fixed YouTube audio provider missing artist attribute propagation on result objects.
- Fixed deduplication logic skipping different versions of the same song (such as live versus studio releases).
- Fixed `KeyError: 'label'` during album synchronization when Spotify API metadata omits label information.
- Fixed discarding of valid single-artist results when the Spotify track lists multiple artists.
- Fixed `spotdl interactive` argument parsing so it no longer treats the subcommand as a search query.
- Fixed type annotations in `spotdl/utils/metadata.py` cover art requests.
- Fixed YAML localization parsing where unquoted boolean keys caused confirmation screens to display raw translation identifiers.
- Fixed menu popover styling to ensure solid background rendering, opaque borders, and full-width buttons.
- Fixed LRC lyric file saving in the lyrics viewer defaulting to current working directory instead of the configured download output destination.
- Fixed AZLyrics provider redirect loops and added fast-fail detection on anti-bot challenge pages.
- Removed unused imports and redundant assignments across TUI screen modules.
