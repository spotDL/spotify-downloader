
<div align="center">

# spotDL v5

**spotDL v5** finds songs from Spotify playlists on YouTube and downloads them - along with album art, lyrics and metadata. 

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![PyPI version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)

> spotDL: The fastest, easiest and most accurate command-line music downloader - now with a beautiful web interface.
</div>

______________________________________________________________________

## What's Different in v5?

This fork of spotDL v4 enhances the existing web interface with extra features.

- **Enhanced visual design** with Spotify-inspired styling
- **Real-time progress tracking** for each individual song  
- **One-click authentication** without dealing with API keys
- **Easy folder selection** with a proper file dialog
- **Better user experience** for less technical users

The original spotDL v4 is fantastic for command-line users, but I wanted something I could use without opening a terminal. Both versions do the exact same thing under the hood - they download music from YouTube based on Spotify metadata.

______________________________________________________________________

## Installation & Usage

### Quick Start (Recommended)

**Option 1: Simple Batch Launcher**
1. Download `SpotDL-Web.bat` from this repository
2. Double-click it to install dependencies and launch the interface
3. Your browser opens to `http://localhost:8807` automatically
4. Paste any Spotify URL and start downloading!

**Option 2: Manual Python Setup**
```bash
# Install dependencies  
pip install fastapi uvicorn websockets requests beautifulsoup4 spotipy python-multipart

# Install spotDL itself
pip install spotdl

# Run the web interface
python custom_web_interface.py
```

### Web Interface Features

- ** Just paste Spotify URLs**: Playlists, albums, or individual tracks
- ** Live progress tracking**: See each song downloading in real-time
- ** Choose your folder**: Click "Change" to pick where songs go
- ** No Login**: Browser authentication - no API keys needed
- ** Cancel individual songs**: Skip tracks you don't want
- ** Clean design**: Spotify-inspired interface

<details>
    <summary style="font-size:1.25em"><strong>Traditional command-line usage (same as v4)</strong></summary>

You can still use spotDL exactly like the original v4:

```sh
spotdl [urls]
```

You can run _spotDL_ as a package if running it as a script doesn't work:

```sh
python -m spotdl [urls]
```

General usage:

```sh
spotdl [operation] [options] QUERY
```

There are different **operations** spotDL can perform. The _default_ is `download`, which simply downloads the songs from YouTube and embeds metadata.

The **query** for spotDL is usually a list of Spotify URLs, but for some operations like **sync**, only a single link or file is required.
For a list of all **options** use ```spotdl -h```

**Supported operations:**
- `save`: Saves only the metadata from Spotify without downloading anything.
- `web`: Starts a web interface (differenet compared to the .bat version)
- `url`: Get direct download link for each song from the query.
- `sync`: Updates directories based on playlist changes.
- `meta`: Updates metadata for existing song files.

</details>

### Installing FFmpeg

FFmpeg is required for spotDL. If using FFmpeg only for spotDL, you can simply install FFmpeg to your spotDL installation directory:
`spotdl --download-ffmpeg`

We recommend the above option, but if you want to install FFmpeg system-wide:

- [Windows Tutorial](https://windowsloop.com/install-ffmpeg-windows-10/)
- OSX - `brew install ffmpeg`
- Linux - `sudo apt install ffmpeg` or use your distro's package manager

## Why I Made This

The original spotDL v4 is excellent, but I wanted to make it more accessible:

**What v4 gives you:**
- Powerful command-line interface
- All the core downloading functionality
- Perfect for technical users and automation

**What v5 adds:**
- **New Web interface** I simply like mine more
- **Real-time progress** - see exactly what's happening
- **Visual feedback** instead of just terminal output
- **Easy setup** with the batch launcher
- **Better error messages** when things go wrong
- **No terminal knowledge needed** for basic usage

Both versions use the same core spotDL engine, so you get identical audio quality and metadata. This is just a different way to interact with it.

## Music Sourcing and Audio Quality

spotDL uses YouTube as a source for music downloads. This method is used to avoid any issues related to downloading music from Spotify.

> **Note**
> Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

### Audio Quality

spotDL downloads music from YouTube and is designed to always download the highest possible bitrate; which is 128 kbps for regular users and 256 kbps for YouTube Music premium users.

Check the [Audio Formats](docs/usage.md#audio-formats-and-quality) page for more info.

## Contributing

Interested in contributing? Check out our [CONTRIBUTING.md](docs/CONTRIBUTING.md) to find
resources around contributing along with a guide on how to set up a development environment.

### Join our amazing community as a code contributor

<a href="https://github.com/spotDL/spotify-downloader/graphs/contributors">
  <img class="dark-light" src="https://contrib.rocks/image?repo=spotDL/spotify-downloader&anon=0&columns=25&max=100&r=true" />
</a>

## License

This project is Licensed under the [MIT](/LICENSE) License.
