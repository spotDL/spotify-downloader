<div align="center">

# spotDL v4

**spotDL** finds songs from Spotify playlists on YouTube and downloads them along with album art, lyrics and metadata.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![PyPI version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![GitHub Repo stars](https://img.shields.io/github/stars/spotDL/spotify-downloader)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)

> spotDL: The fastest, easiest and most accurate music downloader.
</div>

______________________________________________________________________
**[Read the full documentation on ReadTheDocs!](https://spotdl.readthedocs.io)**
______________________________________________________________________

## User Guides & Documentation

- [Interactive TUI User Guide](docs/TUI_USER_GUIDE.md): Complete guide for installing, configuring dependencies, and using the interactive terminal interface.
- [Changelog](docs/CHANGELOG.md): Detailed history of releases and recent changes following Keep a Changelog v1.1.0.
- [Installation Guide](docs/installation.md): Upstream installation reference across different platforms.
- [Contributing Guide](docs/CONTRIBUTING.md): Guidelines for development and contributing code.

## Quick Start & Installation

### Option 1: Interactive TUI & Automated Setup (Recommended)

The interactive Terminal User Interface (TUI) provides a modern visual experience with presets, interactive track selection, download history, and an automated dependency setup wizard.

1. Clone the repository and navigate into the folder:
   ```bash
   git clone https://github.com/spotDL/spotify-downloader.git
   cd spotify-downloader
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv

   # On Windows:
   .\.venv\Scripts\activate

   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

4. Run the automated dependency wizard to install local FFmpeg and Deno:
   ```bash
   spotdl --setup
   ```

5. Launch the interactive interface:
   ```bash
   spotdl interactive
   ```
   *(Running `spotdl` without arguments in an interactive terminal also launches the TUI automatically).*

For detailed usage, shortcuts, and features, see the [Interactive TUI User Guide](docs/TUI_USER_GUIDE.md).

### Option 2: Standard Command-Line Installation (Upstream Method)

Install spotDL globally via `pip`:

```bash
pip install spotdl
```

> On some systems you might have to use `pip3` instead of `pip`.

To update spotDL run:
```bash
pip install --upgrade spotdl
```

<details>
    <summary style="font-size:1.25em"><strong>Other installation options</strong></summary>

- Prebuilt executable
  - Download the latest standalone build from the [Releases Tab](https://github.com/spotDL/spotify-downloader/releases).
- On Termux
  - `curl -L https://raw.githubusercontent.com/spotDL/spotify-downloader/master/scripts/termux.sh | sh`
- Arch Linux
  - Available via the [Arch User Repository (AUR)](https://aur.archlinux.org/packages/spotdl/).
- Docker
  - Build image:
    ```bash
    docker build -t spotdl .
    ```
  - Launch container:
    ```bash
    docker run --rm -v $(pwd):/music spotdl download [trackUrl]
    ```

</details>

### External Dependencies (FFmpeg & Deno)

- **FFmpeg**: Required for audio extraction and conversion.
  - Install locally via spotDL: `spotdl --download-ffmpeg` (or use `spotdl --setup`).
  - Or install system-wide via package managers (`brew install ffmpeg`, `sudo apt install ffmpeg`).
- **Deno**: Strongly recommended for YouTube stream extraction and videos marked as "made for kids".
  - Install locally via spotDL: `spotdl --download-deno` (or use `spotdl --setup`).
  - Or install system-wide via the [official Deno guide](https://docs.deno.com/runtime/getting_started/installation/).

## Usage

### Interactive TUI

Launch the interactive visual interface:
```bash
spotdl interactive
```

### Command-Line Usage

Basic download without additional flags:
```bash
spotdl [urls]
```

Run as a Python module if needed:
```bash
python -m spotdl [urls]
```

General CLI syntax:
```bash
spotdl [operation] [options] QUERY
```

<details>
<summary style="font-size:1em"><strong>Supported operations</strong></summary>

- `interactive`: Starts the interactive Terminal User Interface (TUI) with responsive action cards, track selection, presets, and history.
- `download` (default): Downloads tracks from YouTube and embeds Spotify metadata and cover art.
- `save`: Saves only metadata to a `.spotdl` archive file without downloading audio.
    - Usage: `spotdl save [query] --save-file {filename}.spotdl`
- `web`: Starts a web interface in your browser.
- `url`: Generates user-friendly source URLs for queries.
    - Usage: `spotdl url [query]`
- `sync`: Synchronizes directories by comparing local files against an online playlist.
    - Usage: `spotdl sync [query] --save-file {filename}.spotdl`
- `meta`: Updates and embeds metadata for existing audio files.

</details>

## Music Sourcing and Audio Quality

spotDL uses YouTube and YouTube Music as sources for audio downloads to ensure reliable access.

> **Note**
> Users are responsible for their actions and potential legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

### Audio Quality

spotDL downloads audio and preserves the highest possible bitrate available from the source (128 kbps standard, 256 kbps for YouTube Music premium users, and supports FLAC/OPUS/M4A encoding presets).

Check the [Audio Formats](docs/usage.md#audio-formats-and-quality) page for more details.

## Contributing

Interested in contributing? Check out our [CONTRIBUTING.md](docs/CONTRIBUTING.md) to set up a development environment.

## License

This project is licensed under the [MIT](/LICENSE) License.
