# Spotify-Downloader

[![Build Status](https://travis-ci.org/ritiek/spotify-downloader.svg?branch=master)](https://travis-ci.org/ritiek/spotify-downloader)
[![Coverage Status](https://codecov.io/gh/ritiek/spotify-downloader/branch/master/graph/badge.svg)](https://codecov.io/gh/ritiek/spotify-downloader)
[![Docker Build Status](https://img.shields.io/docker/build/ritiek/spotify-downloader.svg)](https://hub.docker.com/r/ritiek/spotify-downloader)
[![Gitter Chat](https://badges.gitter.im/ritiek/spotify-downloader/Lobby.svg)](https://gitter.im/spotify-downloader/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

- Downloads songs from YouTube in an MP3 format by using Spotify's HTTP link.
- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).
- Automatically applies metadata to the downloaded song which include:

  - Title
  - Artist
  - Album
  - Album art
  - Lyrics (if found on http://lyrics.wikia.com)
  - Album artist
  - Genre
  - Track number
  - Disc number
  - Release date
  - And more...

- Works straight out of the box and does not require to generate or mess with your API keys (already included).

That's how your music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

## Installation

**This tool works only with Python 3.**

Python 2 compatibility was dropped because of the way it deals with unicode (2020 is coming soon too).
If you still need to use Python 2 - check out the (outdated)
[python2](https://github.com/ritiek/spotify-downloader/tree/python2) branch.

spotify-downloader works with all major distributions and even on low-powered devices such as a Raspberry Pi.

Check out the [Installation](https://github.com/ritiek/spotify-downloader/wiki/Installation) wiki page
for OS-specific instructions to get spotify-downloader working on your system.

## Usage

For the most basic usage, downloading tracks is as easy as

```
$ python3 spotdl.py --song https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ
$ python3 spotdl.py --song "ncs - spectre"
```

For downloading playlist and albums, you need to first load all the tracks into text file and then pass
this text file to `--list` argument. Here is how you would do it for a playlist

```
$ python3 spotdl.py --playlist https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD
INFO: Writing 62 tracks to ncs-releases.txt
$ python3 spotdl.py --list ncs-releases.txt
```

Run `python3 spotdl.py --help` to get a list of all available options in spotify-downloader.

Check out the [Available options](https://github.com/ritiek/spotify-downloader/wiki/Available-options)
wiki page for the list of currently available options with their description.

The wiki page [Instructions for Downloading Songs](https://github.com/ritiek/spotify-downloader/wiki/Instructions-for-Downloading-Songs)
contains detailed information about different available ways to download tracks.

## FAQ

- [
How to specify a custom folder where tracks should be downloaded?](https://github.com/ritiek/spotify-downloader/wiki/FAQ#how-to-specify-a-custom-folder-where-tracks-should-be-downloaded)

Check out our [FAQ wiki page](https://github.com/ritiek/spotify-downloader/wiki/FAQ)
for more info.

## Contributing

Check out [CONTRIBUTING.md](CONTRIBUTING.md) for more info.

## Running Tests

```
$ python3 -m pytest test
```

Obviously this requires the `pytest` module to be installed.

## Disclaimer

Downloading copyright songs may be illegal in your country.
This tool is for educational purposes only and was created only to show
how Spotify's API can be exploited to download music from YouTube.
Please support the artists by buying their music.

## License

[![License](https://img.shields.io/github/license/ritiek/spotify-downloader.svg)](https://github.com/ritiek/spotify-downloader/blob/master/LICENSE)
