
<!--- mdformat-toc start --slug=github --->

<!---
!!! IF EDITING THE README, ENSURE TO COPY THE WHOLE FILE TO index.md in `/docs/` AND REMOVE THE REFERENCES TO ReadTheDocs THERE.
--->

<div align="center">

# spotDL v5

**spotDL** is a powerful Spotify music downloader with a modern web interface that finds songs from Spotify playlists on YouTube and downloads them with embedded album art, lyrics and metadata.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![PyPI version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)

> spotDL: The fastest, easiest and most accurate music downloader with a beautiful web interface.

## ✨ Features

- **🌐 Modern Web Interface**: Beautiful, responsive web UI with Spotify-inspired design
- **📱 Real-time Progress**: Live download progress with WebSocket updates
- **🎵 Individual Song Management**: Cancel individual songs, skip tracks, manage queue
- **🔍 Search**: Real Spotify API integration for accurate metadata
- **📁 Custom Download Paths**: Native folder selection dialog
- **🎨 Authentic Design**: Official Spotify color scheme and authentic spotDL branding
- **⚡ Background Processing**: Multi-threaded downloads with clean terminal output
</div>

## 🚀 Quick Start

### Web Interface (Recommended)

1. **Run the Web Interface**:
   ```bash
   python custom_web_interface.py
   ```

2. **Open your browser** to `http://localhost:8081`

3. **Enter a Spotify URL** (playlist, album, or track) and click "Search"

4. **Choose your download folder** using the "Change" button

5. **Start downloading** and watch the real-time progress.

### Installation Options

#### Option 1: Windows Executable (Easiest)
1. **Download** the latest `SpotDL-Web-Interface.exe` from releases
2. **Run** the executable - no installation needed!
3. **Open browser** to `http://localhost:8081`

#### Option 2: Python Installation
```bash
# Install dependencies
pip install -r requirements_web.txt

# Run the web interface
python custom_web_interface.py
```

#### Option 3: Build Your Own Executable
```bash
# Run the build script
build_web_executable.bat

# Executable will be in: dist/SpotDL-Web-Interface/
```

#### Option 4: Traditional Command Line  
- Install: `pip install spotdl`
- Use: `spotdl [spotify_url]`

<details>
    <summary style="font-size:1.25em"><strong>Advanced installation options</strong></summary>

- Prebuilt executable
  - You can download the latest version from the
    [Releases Tab](https://github.com/spotDL/spotify-downloader/releases)
- On Termux
  - `curl -L https://raw.githubusercontent.com/spotDL/spotify-downloader/master/scripts/termux.sh | sh`
- Arch
  - There is an [Arch User Repository (AUR) package](https://aur.archlinux.org/packages/spotdl/) for
    spotDL.
- Docker
  - Build image:

    ```bash
    docker build -t spotdl .
    ```

  - Launch container with spotDL parameters (see section below). You need to create mapped
    volume to access song files

    ```bash
    docker run --rm -v $(pwd):/music spotdl download [trackUrl]
    ```

  - Build from source

    ```bash
    git clone https://github.com/spotDL/spotify-downloader && cd spotify-downloader
    pip install uv
    uv sync
    uv run scripts/build.py
    ```

    An executable is created in `spotify-downloader/dist/`.

</details>

## 💻 System Requirements

### For Web Interface
- **Windows 10/11** (executable version)
- **Python 3.8+** (source version)  
- **4GB RAM** minimum (8GB recommended for large playlists)
- **Internet connection** for Spotify API and YouTube downloads
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

### FFmpeg Installation (Required)
The web interface will automatically handle FFmpeg installation, or you can:

- **Automatic**: `spotdl --download-ffmpeg` (recommended)
- **Windows**: [Download FFmpeg](https://windowsloop.com/install-ffmpeg-windows-10/)
- **macOS**: `brew install ffmpeg`  
- **Linux**: `sudo apt install ffmpeg`

## 📋 Usage

### Web Interface Features

- **🔐 One-Click Authentication**: Browser-based Spotify login (cached for convenience)
- **🎵 Song Detection**: Real Spotify metadata with album covers
- **📊 Live Progress Tracking**: See download progress for each song in real-time
- **❌ Individual Song Control**: Skip or cancel specific songs without stopping the entire download
- **📁 Custom Paths**: Native folder selection for your downloads
- **🎨 Beautiful UI**: Spotify-inspired dark theme with smooth animations

### Traditional Command Line Usage

```sh
# Download a playlist
spotdl https://open.spotify.com/playlist/your_playlist_id

# Download an album  
spotdl https://open.spotify.com/album/your_album_id

# Download a single track
spotdl https://open.spotify.com/track/your_track_id
```

### Backend Features

The web interface uses a backend (`simple_spotdl.py`) that provides:
- **Clean Terminal Output**: Structured progress display
- **Browser Authentication**: No API keys needed
- **JSON Progress Reporting**: Perfect sync between backend and frontend
- **Multiprocessing Support**: Efficient download management

## 🎯 What's New in This Version

### Web Interface Improvements
- **Complete UI Overhaul**: Modern, responsive design with Spotify's authentic color scheme
- **Real-time WebSocket Updates**: Instant progress synchronization between backend and frontend  
- **Advanced Queue Management**: Add, remove, and reorder songs before downloading
- **Progress Visualization**: Individual progress bars for each song with percentage tracking
- **Error Handling**: Graceful error recovery with user-friendly messages
- **Path Selection**: Native OS folder picker integration

### Backend Enhancements  
- **Browser Authentication**: Seamless Spotify login without API key configuration
- **Structured Logging**: Clean, parseable progress output for perfect UI sync
- **Multiprocessing Architecture**: Efficient handling of large playlists
- **Song Skip Logic**: Handling of cancelled/skipped tracks
- **Memory Management**: Optimized for large playlist downloads

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
