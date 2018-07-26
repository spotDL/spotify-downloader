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

- Works straight out of the box and does not require to generate or mess with your API keys.

That's how your music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

## Installation

- **This tool supports only Python 3**, Python 2 compatibility was dropped
because of the way it deals with unicode.
If you need to use Python 2 though, check out the (old) `python2` branch.

- Note: `play` and `lyrics` commands have been deprecated in the current branch
since they were not of much use and created unnecessary clutter.
You can still get them back by using `old` branch though.

### Debian-like GNU/Linux & macOS

```
$ cd
$ git clone https://github.com/ritiek/spotify-downloader
$ cd spotify-downloader
$ pip install -U -r requirements.txt
```

**Important:** if you have installed both Python 2 and 3, the `pip` command
could invoke an installation for Python 2. To see which Python version `pip`
refers to, try `pip -V`. If it turns out `pip` is your Python 2 pip, try
`pip3 install -U -r requirements.txt` instead.

You'll also need to install FFmpeg for conversion
(use `--avconv` if you'd like to use that instead):

Debian-like GNU/Linux:

```
$ sudo apt-get install ffmpeg
```

macOS:

```
$ brew install ffmpeg --with-libmp3lame --with-libass --with-opus --with-fdk-aac
```

If it does not install correctly, you may have to build it from source.
For more info see https://trac.ffmpeg.org/wiki/CompilationGuide.

### Windows

Assuming you have Python 3
([preferably v3.6 or above to stay away from Unicode errors](https://stackoverflow.com/questions/30539882/whats-the-deal-with-python-3-4-unicode-different-languages-and-windows)) already installed and in PATH.

- Download and extract the [zip file](https://github.com/ritiek/spotify-downloader/archive/master.zip)
from master branch.

- Download FFmpeg for Windows from [here](http://ffmpeg.zeranoe.com/builds/).
Copy `ffmpeg.exe` from `ffmpeg-xxx-winxx-static\bin\ffmpeg.exe` to PATH
(usually C:\Windows\System32\) or just place it in the root directory extracted
from the above step.

- Open `cmd` and type `pip install -U -r requirements.txt` to install dependencies.
The same note about `pip` as for Debian, Ubuntu, Linux & Mac applies.

## Usage

**Important:** as like with `pip`, there might be no `python3` command.
This is most likely the case when you have only Python 3 but not 2 installed.
In this case try the `python` command instead of `python3`,
but make sure `python -V` gives you a `Python 3.x.x`!

- For all available options, run `python3 spotdl.py --help`.

Check out the [Available options](https://github.com/ritiek/spotify-downloader/wiki/Available-options)
wiki page for the list of currently available options with their description.

## FAQ

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

