# Quick Start Guide

Get up and running with SpotDL in minutes.

## First Download Using CLI

### 1. Launch the CLI

If installed via pip or uv:

```bash
spotdl
```

Or run directly:

```bash
cd cli && uv run spotdl
```

### 2. Navigate the TUI

When the CLI launches, you'll see the main search screen:

- Press **S** to focus the search input
- Press **D** to view the download queue
- Press **,** (comma) to open settings
- Press **?** for help
- Press **Q** to quit

### 3. Search for Music

1. Type a song name, artist, or paste a URL in the search field
2. Press **Enter** to search
3. Use arrow keys to navigate results
4. Press **Enter** to select a song for download

### 4. Manage Downloads

- Press **D** to view the download queue
- Monitor progress of active downloads
- Completed downloads appear in your Music folder by default

### Supported URL Types

SpotDL supports URLs from multiple platforms:

**Source Platforms (where you get songs from):**
- Spotify tracks, albums, playlists
- Apple Music tracks, albums, playlists
- Deezer tracks, albums, playlists
- Tidal tracks, albums, playlists
- SoundCloud tracks, sets
- Bandcamp tracks, albums

**Target Platforms (where audio is downloaded from):**
- YouTube Music
- YouTube
- SoundCloud
- Bandcamp
- Piped instances

## Using the Web Interface

### 1. Start the Services

Using Docker:

```bash
docker compose up -d
```

Or manually start the backend and frontend:

```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn spotdl.main:app --reload

# Terminal 2 - Frontend
cd frontend && pnpm dev
```

### 2. Access the Interface

Open your browser and navigate to:

- **Development:** `http://localhost:5173` (Vite) or `http://localhost:3000` (Docker)
- **Production:** Your configured domain

### 3. Search and Download

1. Enter a song name or URL in the search bar
2. Browse the search results
3. Click on a song to see available matches
4. Click the download button to start downloading

### 4. Vote on Matches

Help improve match quality:

1. When viewing matches for a song, you'll see vote buttons
2. **Upvote** good matches that sound correct
3. **Downvote** incorrect or low-quality matches
4. Submit better matches if you find them

## Basic Configuration

### CLI Configuration

The CLI reads settings from environment variables with the `SPOTDL_` prefix:

```bash
# Set output directory
export SPOTDL_OUTPUT_DIR="$HOME/Music/SpotDL"

# Set audio format
export SPOTDL_AUDIO_FORMAT="mp3"

# Set audio quality
export SPOTDL_AUDIO_QUALITY="best"

# Connect to backend API
export SPOTDL_API_URL="http://localhost:8000"
```

Or create a `.env` file in the CLI directory:

```ini
SPOTDL_OUTPUT_DIR=/path/to/music
SPOTDL_AUDIO_FORMAT=mp3
SPOTDL_AUDIO_QUALITY=best
```

### Backend Configuration

Configure the backend via environment variables:

```bash
# Database (SQLite for development)
export DATABASE_URL="sqlite+aiosqlite:///./data/spotdl.db"

# For production (PostgreSQL)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/spotdl"

# Redis for caching (optional)
export REDIS_URL="redis://localhost:6379"

# Security
export SECRET_KEY="your-secret-key"
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

## Output Templates

Customize how downloaded files are named:

```bash
# Default: Artist - Title
export SPOTDL_OUTPUT_TEMPLATE="{artist} - {title}"

# Include album
export SPOTDL_OUTPUT_TEMPLATE="{artist}/{album}/{title}"

# Include track number
export SPOTDL_OUTPUT_TEMPLATE="{artist}/{album}/{track_number}. {title}"
```

Available placeholders:
- `{title}` - Song title
- `{artist}` - Primary artist
- `{artists}` - All artists
- `{album}` - Album name
- `{track_number}` - Track number
- `{year}` - Release year
- `{isrc}` - ISRC code

## Audio Formats

SpotDL supports multiple audio formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| MP3 | .mp3 | Best compatibility |
| M4A | .m4a | AAC audio, good quality |
| FLAC | .flac | Lossless, larger files |
| Opus | .opus | Modern, efficient |
| OGG | .ogg | Open format |
| WAV | .wav | Uncompressed |

Set the format:

```bash
export SPOTDL_AUDIO_FORMAT="flac"
```

## Audio Quality

Available quality presets:

| Quality | Bitrate | Description |
|---------|---------|-------------|
| best | Variable | Highest available |
| 320k | 320 kbps | CD-like quality |
| 256k | 256 kbps | High quality |
| 192k | 192 kbps | Good quality |
| 128k | 128 kbps | Smaller files |

Set the quality:

```bash
export SPOTDL_AUDIO_QUALITY="320k"
```

## Offline Mode

The CLI can operate in offline mode when the backend is unavailable:

```bash
export SPOTDL_OFFLINE_MODE=true
```

In offline mode:
- Matching uses local algorithms
- Previously cached matches are available
- No voting or community features

## Common Workflows

### Download a Spotify Playlist

```bash
# Launch CLI
spotdl

# Paste playlist URL in search
# Select all songs
# Press Enter to download
```

### Download a Single Song

```bash
# Launch CLI
spotdl

# Search by name: "Artist - Song Name"
# Or paste: https://open.spotify.com/track/...
```

### Batch Download from URLs

Create a file with URLs (one per line) and use the CLI to process them.

## Next Steps

- [Configuration Reference](./configuration.md) - All configuration options
- [CLI Usage Guide](../guides/cli-usage.md) - Detailed CLI documentation
- [Web Interface Guide](../guides/web-interface.md) - Using the web UI
