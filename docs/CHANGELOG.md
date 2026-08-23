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
- Internationalization (i18n) support with on-the-fly language switching between English and Spanish.
- Support for playlist, album, and artist downloads in the Web UI via `gen_download_from_query`.
- New `Song.duplicate_key` property to accurately differentiate track variants such as live, remaster, and studio versions during deduplication.
- Comprehensive user guide for the interactive terminal interface in `docs/TUI_USER_GUIDE.md`.
- Regression test suites covering TUI interactions, duplicate version handling, artist matching penalties, and M3U playlist generation.

### Changed
- Refactored main menu into a responsive action card grid layout inspired by Parabolic with short labels and detailed hover tooltips.
- Updated M3U generation to write track entries relative to the target playlist file using forward slashes for cross-platform portability.
- Enhanced M3U playlist file naming to dynamically resolve downloaded playlist names (with album and first track fallbacks) and replace generic filename placeholders automatically.
- Restructured artist matching calculation to evaluate primary artist ratio before applying multi-artist penalties.
- Refined duration matching curve in audio matching to gracefully handle slight music video intro/outro length variances without discarding valid releases.
- Reorganized TUI screen architecture into `download`, `help`, `home`, and `web` modules.
- Updated dependencies to include `textual>=8.0.0,<9`, `pyyaml>=6.0.0,<7`, `pyperclip>=1.8.2,<3`, and `rich>=14.2.0,<16`.

### Fixed
- Fixed audio provider matching picking parodies or unrelated videos by adding `parody`, `amv`, `animatic`, `mashup`, and `parodia` to forbidden words penalties.
- Fixed YouTubeMusic audio provider language setting and duration seconds extraction to prevent false zero-duration match failures.
- Fixed YouTube audio provider missing artist attribute propagation on result objects.
- Fixed deduplication logic skipping different versions of the same song (such as live versus studio releases).
- Fixed `KeyError: 'label'` during album synchronization when Spotify API metadata omits label information.
- Fixed discarding of valid single-artist results when the Spotify track lists multiple artists.
- Fixed Web UI rejection of Spotify URLs containing localized `/intl-xx/` path prefixes.
- Fixed `spotdl interactive` argument parsing so it no longer treats the subcommand as a search query.
- Fixed type annotations in `spotdl/utils/metadata.py` cover art requests.
- Fixed YAML localization parsing where unquoted boolean keys caused confirmation screens to display raw translation identifiers.
- Fixed menu popover styling to ensure solid background rendering, opaque borders, and full-width buttons.
