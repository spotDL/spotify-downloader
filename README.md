
<!--- mdformat-toc start --slug=github --->

<!---
!!! IF EDITING THE README, ENSURE TO COPY THE WHOLE FILE TO index.md in `/docs/` AND REMOVE THE REFERENCES TO ReadTheDocs THERE.
--->

<div align="center">

# spotDL v4

**spotDL** finds songs from Spotify playlists on YouTube and downloads them - along with album art, lyrics and metadata.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![PyPI version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)

> spotDL: The fastest, easiest and most accurate command-line music downloader.
</div>

______________________________________________________________________
**[Read the documentation on ReadTheDocs!](https://spotdl.readthedocs.io)**
______________________________________________________________________

## Installation

Refer to our [Installation Guide](docs/installation.md) for more details.

### Python (Recommended Method)

- _spotDL_ can be installed by running `pip install spotdl`.
- To update spotDL run `pip install --upgrade spotdl`

  > On some systems you might have to change `pip` to `pip3`.

<details>
    <summary style="font-size:1.25em"><strong>Other options</strong></summary>

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

### Installing FFmpeg

FFmpeg is required for spotDL. If using FFmpeg only for spotDL, you can simply install FFmpeg to your spotDL installation directory:
`spotdl --download-ffmpeg`

We recommend the above option, but if you want to install FFmpeg system-wide,
follow these instructions

- [Windows Tutorial](https://windowsloop.com/install-ffmpeg-windows-10/)
- OSX - `brew install ffmpeg`
- Linux - `sudo apt install ffmpeg` or use your distro's package manager

## Usage

Using SpotDL without options:

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

<details>
<summary style="font-size:1em"><strong>Supported operations</strong></summary>

- `save`: Saves only the metadata from Spotify without downloading anything.
    - Usage:
        `spotdl save [query] --save-file {filename}.spotdl`

- `web`: Starts a web interface instead of using the command line. However, it has limited features and only supports downloading individual songs.

- `url`: Get user-friendly URL for each song from the query.
    - Usage:
        `spotdl url [query]`

- `sync`: Updates directories. Compares the directory with the current state of the playlist. Newly added songs will be downloaded and removed songs will be deleted. No other songs will be downloaded and no other files will be deleted.

    - Usage:
        `spotdl sync [query] --save-file {filename}.spotdl`

        This creates a new **sync** file. To update the directory in the future, use:

        `spotdl sync {filename}.spotdl`

- `meta`: Updates metadata for the provided song files.

</details>


## 🚀 Advanced Usage Examples

### Custom Output Formatting

Organize your downloads by artist and album:
```bash
# Create artist/album folder structure
spotdl https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M \
  --output "{artist}/{album}/{title}.{output-ext}"

# Add track numbers to filenames
spotdl https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M \
  --output "{list-position} - {artist} - {title}.{output-ext}"

# Use playlist numbering
spotdl https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M --playlist-numbering
```

Available format variables:
- `{artist}` - Artist name
- `{album}` - Album name
- `{title}` - Song title
- `{list-position}` - Position in playlist
- `{output-ext}` - File extension (mp3, flac, etc.)

### Using Cookies for Better Quality

For YouTube Music Premium users, export cookies to access higher quality audio:
```bash
# Using browser cookies for authentication
spotdl https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT \
  --cookie-file cookies.txt \
  --format m4a \
  --bitrate disable
```

**How to get cookies:**
1. Install a browser extension like "Get cookies.txt" (Chrome/Firefox)
2. Visit YouTube Music and log in
3. Export cookies using the extension
4. Save as `cookies.txt`

### Syncing Playlists

Keep your local library synchronized with Spotify playlists:
```bash
# Create a sync file (first time)
spotdl sync https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M \
  --save-file my_playlist.spotdl

# Update later - downloads new songs, removes deleted ones
spotdl sync my_playlist.spotdl
```

This is perfect for keeping a local backup of your favorite playlists that automatically updates!

### Audio Format and Quality Options
```bash
# High quality FLAC (lossless)
spotdl https://open.spotify.com/track/TRACK_ID --format flac

# M4A with specific bitrate
spotdl https://open.spotify.com/track/TRACK_ID --format m4a --bitrate 256k

# OPUS format (best size-to-quality ratio)
spotdl https://open.spotify.com/track/TRACK_ID --format opus --bitrate 128k

# Disable bitrate limiting (use source quality)
spotdl https://open.spotify.com/track/TRACK_ID --bitrate disable
```

### Batch Downloads
```bash
# Download multiple URLs at once
spotdl https://open.spotify.com/playlist/PLAYLIST_1 \
        https://open.spotify.com/album/ALBUM_1 \
        "The Weeknd - Blinding Lights"

# Download from a text file (one URL per line)
spotdl --download-from-file urls.txt
```

### Using Custom Spotify API Credentials

Avoid rate limiting by using your own Spotify API credentials:
```bash
spotdl https://open.spotify.com/playlist/PLAYLIST_ID \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

**Get your credentials:**
1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account
3. Click "Create an App"
4. Copy the Client ID and Client Secret

---

## 🔧 Troubleshooting Common Issues

### Rate Limiting Errors

**Problem:** Getting rate limited by Spotify or YouTube

**Solutions:**
```bash
# Solution 1: Use your own Spotify API credentials
spotdl https://open.spotify.com/playlist/PLAYLIST_ID \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# Solution 2: Use cookies for YouTube authentication
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --cookie-file cookies.txt

# Solution 3: Reduce thread count
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --threads 1
```

### Download Failures

**Problem:** Songs failing to download or being skipped

**Solutions:**
```bash
# Skip already downloaded files
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --overwrite skip

# Force re-download all files
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --overwrite force

# Use debug logging to see detailed errors
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --log-level DEBUG

# Try different audio providers
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --audio-provider youtube
```

### FFmpeg Not Found Error

**Problem:** `FFmpeg not found` error when trying to download

**Solution:**
```bash
# Ubuntu/Debian/Linux Mint
sudo apt update
sudo apt install ffmpeg -y

# Verify installation
ffmpeg -version

# If still not working, check PATH
which ffmpeg
```

### Metadata/Tags Issues

**Problem:** Downloaded songs have incorrect or missing metadata

**Solutions:**
```bash
# Force metadata refresh
spotdl https://open.spotify.com/track/TRACK_ID --force-update-metadata

# Use Spotify metadata explicitly
spotdl https://open.spotify.com/track/TRACK_ID --lyrics-provider musixmatch

# Download with embedded lyrics
spotdl https://open.spotify.com/track/TRACK_ID --generate-lrc
```

### Slow Download Speeds

**Problem:** Downloads are very slow

**Solutions:**
```bash
# Increase thread count (default is 4)
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --threads 8

# Use different audio provider
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --audio-provider youtube-music

# Skip time-consuming features
spotdl https://open.spotify.com/playlist/PLAYLIST_ID --skip-explicit
```

### Permission Denied Errors

**Problem:** Cannot write to output directory

**Solution:**
```bash
# Specify output directory you have permissions for
spotdl https://open.spotify.com/track/TRACK_ID --output ~/Music/{title}.{output-ext}

# Or change directory permissions
sudo chmod 755 /path/to/output/directory
```

---

## 💡 Pro Tips

### Create a Config File

Instead of typing the same options every time, create a config file:

**Linux:** `~/.config/spotdl/config.json`
```json
{
  "format": "mp3",
  "bitrate": "320k",
  "output": "{artist}/{album}/{title}.{output-ext}",
  "threads": 4,
  "lyrics_providers": ["genius", "musixmatch"],
  "log_level": "INFO"
}
```

Then simply run:
```bash
spotdl https://open.spotify.com/playlist/PLAYLIST_ID
```

All settings from config.json will be applied automatically!

### Best Quality Settings

For the absolute best audio quality:
```bash
spotdl https://open.spotify.com/playlist/PLAYLIST_ID \
  --format flac \
  --bitrate disable \
  --cookie-file cookies.txt \
  --audio-provider youtube-music
```

### Smallest File Sizes

For minimal disk space usage while maintaining good quality:
```bash
spotdl https://open.spotify.com/playlist/PLAYLIST_ID \
  --format opus \
  --bitrate 96k
```

### Archive Entire Artists

Download complete discographies:
```bash
# Download all albums from an artist
spotdl https://open.spotify.com/artist/ARTIST_ID \
  --output "{artist}/{album}/{track-number} - {title}.{output-ext}"
```

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
