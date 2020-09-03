# Spotify-Downloader

<!-- Badges & Stuff -->
[![PyPi](https://img.shields.io/pypi/v/spotdl.svg)](https://pypi.org/project/spotdl)
[![Docs Build Status](https://readthedocs.org/projects/spotdl/badge/?version=latest)](https://spotdl.readthedocs.io/en/latest/home.html)
[![Build Status](https://travis-ci.org/ritiek/spotify-downloader.svg?branch=master)](https://travis-ci.org/ritiek/spotify-downloader)
[![Coverage Status](https://codecov.io/gh/ritiek/spotify-downloader/branch/master/graph/badge.svg)](https://codecov.io/gh/ritiek/spotify-downloader)
[![Docker Build Status](https://img.shields.io/docker/build/ritiek/spotify-downloader.svg)](https://hub.docker.com/r/ritiek/spotify-downloader)
[![Code style: black](https://img.shields.io/badge/code-style-black-000000.svg)](https://github.com/ambv/black)
[![Gitter Chat](https://badges.gitter.im/ritiek/spotify-downloader/Lobby.svg)](https://gitter.im/spotify-downloader/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# Whats new in v3.0.0 ?

- Total ***rewrite of the whole code base***, it is now far more light weight, simple and easy to contribute to.

- ***~99% accuracy*** - We got fed-up with spotdl downloading the wrong stuff like, wayyyyy of mark (⊙_⊙;) so we fixed
it. spotdl now matches songs accurately even for the weirdest, obscure, obfuscated oddballs you throw at it
(i.e. as long as such a song exists on spotify and YouTube)

- ***x3 faster downloads***, your 60 song playlist take 1 Hour+ to download last time? Now it'll get done in in 20 mins
(we tried it on a 350kbps connection)

<br>

And finally, even though its not a code thing, I (@Mikhail-Zex) would like to drop a note of thanks to those who
helped:
- @rietiek, for creating spotdl and maintaining it for 4 solid years.
- @rocketinventor for figuring out just how to query YouTube Music.
- myself? (Ah, never mind...)

<br><br><br>

# What does spotdl do?

- Downloads songs from YouTube in an MP3 format by using Spotify's HTTP link.

- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).

- Automatically applies metadata to the downloaded song which includes:
    - `Title`, `Artist(s)`, `Album`, `Album art`, `Album artist(s)`, `Genre(s)`, `Track number` & `Release date`

- Works straight out of the box and does not require you to generate or mess with your API keys (already included).

Below is how your music library will look!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

## Installation

❗️ **This tool works only with Python 3.6+**

spotify-downloader works with all major distributions and even on low-powered devices such as a Raspberry Pi.

spotify-downloader can be installed via pip with:
```console
$ pip3 install spotdl
```

but be sure to check out the [Installation](https://spotdl.readthedocs.io/en/latest/installation.html) docs
for detailed OS-specific instructions to get it and other dependencies it relies on working on your system.

## Usage

For the most basic usage, downloading tracks, playlists or albums is as easy as

```console
$ spotdl https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ
$ spotdl https://open.spotify.com/playlist/37i9dQZF1DWXRqgorJj26U?si=z4w_tmGwTHGNgDiBJDiMkw
$ spotdl https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=Dv9qyCdjRvag9AGQl7MsFA
```

In case of playlists or albums, a ***.spotdlTrackingFile*** is automatically created in the directory
in which spotdl was executed with the name of the first song in the album/playlist being downloaded.
Resuming skipped or interrupted downloads is simple as

```console
$ spotdl 'my-fav-playlist.spotdlTrackingFile'
```

If your lazy and would like to download all your stuff in one go, you can do so by separating the all the
links and '.spotdlTrackingFiles' with spaces

```console
$ spotdl https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ https://open.spotify.com/playlist/37i9dQZF1DWXRqgorJj26U?si=z4w_tmGwTHGNgDiBJDiMkw https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=Dv9qyCdjRvag9AGQl7MsFA my-fav-playlist.spotdlTrackingFile
```

You really don't have to bother about duplicate tracks across multiple playlists, we take care of that for you. There are
no **commands** bundled with spotdl anymore (as of v3.0.0), they might be added back in at a later time.

## Disclaimer

Downloading copyright songs may be illegal in your country. This tool is for educational purposes only and was
created only to show how Spotify's API can be exploited to download music from YouTube Music (with a little filtering of
results). Please support the artists by buying their music (or streaming their music on Spotify).

## License

[![License](https://img.shields.io/github/license/ritiek/spotify-downloader.svg)](https://github.com/ritiek/spotify-downloader/blob/master/LICENSE)
