<!--- mdformat-toc start --slug=github --->

<div align="center">

# spotDL v4

Download your Spotify playlists and songs along with album art and metadata

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?style=flat-square&color=44CC11)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![pypi version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![GitHub commits since latest release (by date)](https://img.shields.io/github/commits-since/spotDL/spotify-downloader/latest?color=44CC11&style=flat-square)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)


</div>

> A new and improved version of spotDL: still the fastest, easiest and most accurate command-line music downloader

---

**[Read the documentation on ReadTheDocs!](https://spotdl.readthedocs.io/projects/spotify-downloader/en/latest/)**

---

## Prerequisites

- Python 3.7 or above (added to PATH)
- FFmpeg 4.2 or above (added to PATH)
- Visual C++ 2019 redistributable (on Windows)

> **_YouTube Music must be available in your country for spotDL to work. This is because we use YouTube Music to filter search results. You can check if YouTube Music is available in your country, by visiting [YouTube Music](https://music.youtube.com)._**

## Installation

- Python
    - _spotDL_ can be installed by running `pip install spotdl`.
- Prebuilt Executable
    - You can download the latest version from from the [Releases Tab](https://github.com/spotDL/spotify-downloader/releases)
- On Termux
    - `curl -L https://raw.githubusercontent.com/spotDL/spotify-downloader/master/termux/setup_spotdl.sh | sh`
- Arch
    - There is an Arch User Repository (AUR) package for [spotDL](https://aur.archlinux.org/packages/python-spotdl/).
- Docker
    - Build image:
    ```bash
    docker build --rm -t spotdl .
    ```
    - Launch container with spotDL parameters (see section below). You need to create mapped volume to access song files
    ```bash
    docker run --rm -v ~/music-spotdl:/music --name spotdl spotdl [trackUrl]
    ```

### Installing FFmpeg

- [Windows Tutorial](https://windowsloop.com/install-ffmpeg-windows-10/)
- OSX - `brew install ffmpeg`
- Linux - `sudo apt install ffmpeg` or use your distros package manager
- Using spotDL - `spotdl --download-ffmpeg` - this will download FFmpeg to spotdl directory.

## Usage

To get started right away:

```sh
spotdl download [urls]
```

To start Web UI:
```
spotdl web
```

You can run _spotDL_ as a package if running it as a script doesn't work:

```sh
python -m spotdl [urls]
```

---

### Further information can be found in our docs:

- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Code of Conduct](docs/CODE_OF_CONDUCT.md)
- [Troubleshooting / FAQ Guide](docs/troubleshooting.md)


## Contributing

Interested in contributing? Check out our [CONTRIBUTING.md](docs/CONTRIBUTING.md) to find
resources around contributing along with a guide on how to set up a development environment.

## License

This project is Licensed under the [MIT](/LICENSE) License.
