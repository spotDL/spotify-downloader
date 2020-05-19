# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

The release dates mentioned follow the format `DD-MM-YYYY`.

## [Unreleased]

## [2.0.4] - 19-05-2020
### Fixed
- Do not remove the currently downloading track from file on `KeyboardInterrupt`
  when `--list` is passed. ([@ritiek](https://github.com/ritiek/spotify-downloader)) (#722)
- Failure on invoking spotdl if FFmpeg isn't found. It should now warn about missing
  FFmpeg and move ahead without encoding. ([@ritiek](https://github.com/ritiek))
  (debe7ee9024e2ec65eed9935460c62f4eecd03ea)

## [2.0.3] (Hotfix Release) - 18-05-2020
### Fixed
- Genius would sometimes return invalid lyrics. Retry a few times in such a case.
  ([@ritiek](https://github.com/ritiek)) (29b1f31a2622f749df83c3072c4cbb22615bff95)

## [2.0.2] (Hotfix Release) - 18-05-2020
### Fixed
- Skipping tracks with `-m` would crash. ([@ritiek](https://github.com/ritiek))
  (bbe43da191093302726ddc9a48f0fa0a55be6fb6)

## [2.0.1] (Hotfix Release) - 18-05-2020
### Fixed
- `-o m4a` would always fail. ([@ritiek](https://github.com/ritiek))
  (cd5f224e379f3feefc95e338ec50674f976e2e89)

## [2.0.0] - 18-05-2020
### Migrating from v1.2.6 to v2.0.0
For v2.0.0 to work correctly, you need to remove your previous `config.yml` due to
breaking changes in v2.0.0 (marked as **[Breaking]** in the below sections), new options being
added, and old ones being removed. You may want to first backup your old configuration for
reference.  You can then install spotdl v2.0.0 and remove your current configuration by
running:
```
$ spotdl --remove-config
```
spotdl will automatically generate a new configuration file on the next run. You can
then replace the appropriate fields in the newly generated configuration file by
referring to your old configuration file.

All the below changes were made as a part of #690.

### Added
- `-i` now accepts `automatic` which would automatically select the best available stream
  irrespective of the format.
- Added parameter `-q` (`--quality {best,worst}`) to select best (default) or worst audio quality.
- Added `-ne` (`--no-encode`) to disable encoding.
- Output to STDOUT with `-f -`.
- Output to STDOUT with `--write-to -`.
- Read tracks from STDIN in `-s` parameter.
- Display a combined *download & encode* progress bar.

### Changed
- **[Breaking]** Tracks are now downloaded in the current working directory (instead of
  user's Music directory) by default.
- **[Breaking]** Short for `--album` is now `-a` instead of `-b`.
- **[Breaking]** Short for `--all-albums` is now `-aa` instead of `-ab`.
- Allow "&" character in filenames.
- **[Breaking]** Merge parameters `-ff` and `-f` to `-f` (`--output-file`).
- **[Breaking]** Do not prefix formats with a dot when specifying `-i` and `-o` parameters
  Such as `-o .mp3` is now written as `-o mp3`.
- **[Breaking]** Search format now uses hyphen for word break instead of underscore. Such as
  `-sf "{artist} - {track_name}"` is now written as `-sf "{artist} - {track-name}"`.
- **[Breaking]** `--write-successful` and `--skip` is renamed to `--write-successful-file` and
  `--skip-file` respectively.
- Partial re-write and internal API refactor.
- Enhance debug log output readability.
- Internally adapt to latest changes made in Spotipy library.
- Switch to `logging` + `coloredlogs` instead of `logzero`. Our loggers weren't being
  setup properly with `logzero`.
- Simplify checking for an downloaded already track. Previously it also analyzed metadata
  for the already downloaded track to determine whether to overwrite the already downloaded
  track, which caused unexpected behvaiours at times.
- Codebase is now more modular making it easier to use spotdl in python scripts.
- `config.yml` now uses underscores for separating between argument words instead of
  hyphens for better compatibility with `argparse`.

### Optimized
- Track download and encoding now happen parallely instead of sequentially making spotdl
  faster.
- Lyrics and albumart are now downloaded in the background while the track is being downloaded
  instead of in the end. This reduces additional delays if we are to download them while applying
  metadata.
- `--write-m3u` now only scrapes YouTube for required metadata making it much faster.
  Previously, it was also required to parse it via an external YouTube parsing library
  which was slow.
- Switch to PyTube from Pafy. PyTube is faster and relies only on scraping.

### Removed
- **[Breaking]** Removed Avconv support. Only FFmpeg is supported now.
- **[Breaking]** Removed `--no-fallback-metadata` parameter since not many people seem to find it useful.
- **[Breaking]** Removed apparently misleading `--download-only-metadata` parameter.
- **[Breaking]** Removed ability to set YouTube API key since we now use PyTube instead of Pafy, and
  PyTube does not require an API key.
- **[Breaking]** As a side effect of above, `--music-videos-only` is also removed as this feature worked only
  with YouTube API.

## [1.2.6] (Hotfix Release) - 2020-03-02
### Fixed
- Embed release date metadata only when available (follow up of #672) ([@ritiek](https://github.com/ritiek)) (#674)

## [1.2.5] - 2020-03-02
### Fixed
- Skip crash when accessing YouTube-API-only fields in scrape mode ([@ritiek](https://github.com/ritiek)) (#672)

### Changed
- Changed FFMPEG args to convert to 48k quality audio instead of the current 44k audio. ([@AvinashReddy3108](https://github.com/AvinashReddy3108)) (#667)

## [1.2.4] - 2020-01-10
### Fixed
- Fixed a crash occuring when lyrics for a track are not yet released
  on Genius ([@ritiek](https://github.com/ritiek)) (#654)
- Fixed a regression where a track would fail to download if it isn't
  found on Spotify ([@ritiek](https://github.com/ritiek)) (#653)

## [1.2.3] - 2019-12-20
### Added
- Added `--no-remove-original-file` ([@NightMachinary](https://github.com/NightMachinary)) (#580)
- Added leading Zeros in `track_number` for correct sorting ([@Dsujan](https://github.com/Dsujan)) (#592)
- Added `track_id` key for `--file-format` parameter ([@kadaliao](https://github.com/kadaliao)) (#568)

### Fixed
- Some tracks randomly fail to download with Pafy v0.5.5 ([@ritiek](https://github.com/ritiek)) (#638)
- Generate list error --write-m3u ([@arthurlutz](https://github.com/arthurlutz)) (#559)

### Changed
- Fetch lyrics from Genius and fallback to LyricWikia if not found ([@ritiek](https://github.com/ritiek)) (#585)

## [1.2.2] - 2019-06-03
### Fixed
- Patch bug in Pafy to prefer secure HTTPS ([@ritiek](https://github.com/ritiek)) (#558)

## [1.2.1] - 2019-04-28
### Fixed
- Patch bug in Pafy when fetching audiostreams with latest youtube-dl ([@ritiek](https://github.com/ritiek)) (#539)

### Changed
- Removed duplicate debug log entry from `internals.trim_song` ([@ritiek](https://github.com/ritiek)) (#519)
- Fix YAMLLoadWarning ([@cyberboysumanjay](https://github.com/cyberboysumanjay)) (#517)

## [1.2.0] - 2019-03-01
### Added
- `--write-to` parameter for setting custom file to write Spotify track URLs to ([@ritiek](https://github.com/ritiek)) (#507)
- Set custom Spotify Client ID and Client Secret via config.yml ([@ManveerBasra](https://github.com/ManveerBasra)) (#502)
- Use YouTube as fallback metadata if track not found on Spotify. Also added `--no-fallback-metadata`
  to preserve old behaviour ([@ritiek](https://github.com/ritiek)) (#457)

### Fixed
- Fix already downloaded prompt when using "/" in `--file-format` to create sub-directories ([@ritiek](https://github.com/ritiek)) (#503)
- Fix writing playlist tracks to file ([@ritiek](https://github.com/ritiek)) (#506)

## [1.1.2] - 2019-02-10
### Changed
- Fetch all artist albums by default instead of only fetching the "album" type ([@ritiek](https://github.com/ritiek)) (#493)
- Option `-f` (`--folder`) is used when exporting text files using `-p` (`--playlist`) for playlists or `-b` (`--album`) for albums ([@Silverfeelin](https://github.com/Silverfeelin)) (#476)
- Use first artist from album object for album artist ([@tillhainbach](https://github.com/tillhainbach))

### Fixed
- Fix renaming files when encoder is not found ([@ritiek](https://github.com/ritiek)) (#475)
- Add missing `import time` ([@ifduyue](https://github.com/ifduyue)) (#465)

## [1.1.1] - 2019-01-03
### Added
- Output informative message in case of no result found in YouTube search ([@Amit-L](https://github.com/Amit-L)) (#452)
- Ability to pass multiple tracks with `-s` option ([@ritiek](https://github.com/ritiek)) (#442)

### Changed
- Allowed to fetch metadata from Spotify upon searching Spotify-URL and  `--no-metadata` to gather YouTube custom-search fields ([@Amit-L](https://github.com/Amit-L)) (#452)
- Change FFmpeg to use the built-in encoder `aac` instead of 3rd party `libfdk-aac` which does not
  ship with the apt package ([@ritiek](https://github.com/ritiek)) (#448)
- Monkeypatch ever-changing network-relying tests ([@ritiek](https://github.com/ritiek)) (#448)
- Correct `.m4a` container before writing metadata so metadata fields shows up properly in
  media players (especially iTunes) ([@ritiek](https://github.com/ritiek) with thanks to [@Amit-L](https://github.com/Amit-L)!) (#453)
- Refactored core downloading module ([@ritiek](https://github.com/ritiek)) (#410)

### Fixed
- Workaround conversion conflicts when input and output filename are same ([@ritiek](https://github.com/ritiek)) (#459)
- Applied a check on result in case of search using Spotify-URL  `--no-metadata` option ([@Amit-L](https://github.com/Amit-L)) (#452)
- Included a missing `import spotipy` in downloader.py ([@ritiek](https://github.com/ritiek)) (#440)

## [1.1.0] - 2018-11-13
### Added
- Output error details when track download fails from list file ([@ManveerBasra](https://github.com/ManveerBasra)) (#406)
- Add support for `.m3u` playlists ([@ritiek](https://github.com/ritiek)) (#401)
- Introduce usage of black (code formatter) ([@linusg](https://github.com/linusg)) (#393)
- Added command line option for getting all artist's songs ([@AlfredoSequeida](https://github.com/AlfredoSequeida)) (#389)
- Added command line options for skipping tracks file and successful downloads file and
  place newline before track URL when appending to track file ([@linusg](https://github.com/linusg)) (#386)
- Overwrite track file with unique tracks ([@ritiek](https://github.com/ritiek)) (#380)
- Embed comment metadata in `.m4a` ([@ritiek](https://github.com/ritiek)) (#379)
- Added check for publisher tag before adding publisher id3 tag to audio file ([@gnodar01](https://github.com/gnodar01)) (#377)

### Changed
- `--list` flag accepts only text files using mimetypes ([@ManveerBasra](https://github.com/ManveerBasra)) (#414)
- Refactored Spotify token refresh ([@ManveerBasra](https://github.com/ManveerBasra)) (#408)
- Don't search song on Spotify if `--no-metadata` is passed ([@ManveerBasra](https://github.com/ManveerBasra)) (#404)
- Changed test track to one whose lyrics are found ([@ManveerBasra](https://github.com/ManveerBasra)) (#400)
- Windows - 'My Music' folder won't be assumed to be on C drive but looked up in Registry ([@SillySam](https://github.com/SillySam)) (#387)
- Updated `setup.py` (fix PyPI URL, add Python 3.7 modifier) ([@linusg](https://github.com/linusg)) (#383)
- Updated dependencies to their newest versions (as of 2018-10-02) ([@linusg](https://github.com/linusg)) (#382)
- Remove duplicates from track file while preserving order ([@ritiek](https://github.com/ritiek)) (#369)
- Moved a lot of content from `README.md` to the [repository's GitHub wiki](https://github.com/ritiek/spotify-downloader/wiki) ([@sdhutchins](https://github.com/sdhutchins), [@ritiek](https://github.com/ritiek)) (#361)
- Refactored internal use of logging ([@arryon](https://github.com/arryon)) (#358)

### Fixed
- Check and replace slashes with dashes to avoid directory creation error ([@ManveerBasra](https://github.com/ManveerBasra)) (#402)
- Filter unwanted text from Spotify URLs when extracting information ([@ritiek](https://github.com/ritiek)) (#394)
- Correctly embed metadata in `.m4a` ([@arryon](https://github.com/arryon)) (#372)
- Slugify will not ignore the `'` character (single quotation mark) anymore ([@jimangel2001](https://github.com/jimangel2001)) (#357)

## [1.0.0] - 2018-09-09
### Added
- Initial complete release, recommended way to install is now from PyPI

## 1.0.0-beta.1 - 2018-02-02
### Added
- Initial release, prepare for 1.0.0

[Unreleased]: https://github.com/ritiek/spotify-downloader/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/ritiek/spotify-downloader/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ritiek/spotify-downloader/compare/v1.0.0-beta.1...v1.0.0
