# SpotDL CLI

Interactive TUI (Terminal User Interface) for downloading music from various platforms.

## Features

- **Full Offline Support**: All functionality works without a backend server
  - Search YouTube and YouTube Music directly via yt-dlp
  - Local matching engine for song-to-video matching
  - Download and convert audio locally
- **Interactive Search**: Search for songs by query or paste URLs
- **Download Queue**: Manage and monitor downloads with progress tracking
- **Concurrent Downloads**: Download multiple songs simultaneously
- **Metadata Embedding**: Automatically embed metadata and cover art (MP3, M4A, FLAC, OGG)
- **Hybrid Mode**: Uses backend API when available, falls back to offline seamlessly
- **SoundCloud OAuth**: CLI-only SoundCloud authentication support

## How Offline Mode Works

The CLI includes a complete local matching engine:

1. **Search**: Searches YouTube and YouTube Music using yt-dlp
2. **Match**: Uses a multi-stage scoring algorithm (artist, name, duration, album)
3. **Download**: Downloads audio via yt-dlp with format conversion
4. **Embed**: Adds metadata and cover art using mutagen

No backend server required for basic functionality.

## Installation

```bash
pip install spotdl-cli
```

Or with uv:

```bash
uv add spotdl-cli
```

## Usage

Run the CLI:

```bash
spotdl
```

### Keyboard Shortcuts

- `s` - Open search screen
- `d` - Open downloads screen
- `,` - Open settings
- `q` - Quit
- `?` - Help

### Search Screen

- Enter a URL or search query in the input field
- Press Enter or click Search to find songs
- Select songs with arrow keys
- Press `a` to add all songs to queue
- Press Enter to add selected song

### Queue Screen

- `Space` - Start/pause downloads
- `Delete` - Remove selected item
- `c` - Clear completed downloads
- `r` - Retry failed downloads

## Configuration

Settings are stored in your platform's config directory:

- Linux: `~/.config/spotdl/`
- macOS: `~/Library/Application Support/spotdl/`
- Windows: `%APPDATA%\spotdl\`

### Environment Variables

- `SPOTDL_API_URL` - Backend API URL (default: http://localhost:8000)
- `SPOTDL_OFFLINE_MODE` - Enable offline mode (default: false)
- `SPOTDL_OUTPUT_DIR` - Download directory
- `SPOTDL_AUDIO_FORMAT` - Audio format (mp3, m4a, flac, opus, ogg, wav)
- `SPOTDL_AUDIO_QUALITY` - Audio quality (best, 320k, 256k, 192k, 128k)
- `SPOTDL_THREADS` - Concurrent downloads (1-16)

### SoundCloud Authentication

For downloading SoundCloud tracks that require authentication:

```bash
export SPOTDL_SOUNDCLOUD_CLIENT_ID="your_client_id"
export SPOTDL_SOUNDCLOUD_AUTH_TOKEN="your_auth_token"
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run CLI in dev mode
uv run textual run --dev spotdl_cli.app:SpotDLApp

# Run tests
uv run pytest

# Type checking
uv run mypy src

# Linting
uv run ruff check src
```

## License

MIT
