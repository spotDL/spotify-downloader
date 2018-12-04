# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Ability to pass multiple tracks with `-s` option ([@ritiek](https://github.com/ritiek)) (#442)

### Changed
- Refactored core downloading module ([@ritiek](https://github.com/ritiek)) (#410)

### Fixed
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
