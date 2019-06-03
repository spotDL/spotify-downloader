# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
-

### Fixed
-

### Changed
-

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
