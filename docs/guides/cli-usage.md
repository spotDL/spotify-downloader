# CLI Usage Guide

The SpotDL CLI provides an interactive terminal user interface (TUI) for searching and downloading music. Built with Textual, it offers a rich, keyboard-driven experience.

## Launching the CLI

```bash
# If installed globally
spotdl

# Using uv
cd cli && uv run spotdl

# Using Python module
cd cli && uv run python -m spotdl_cli
```

## TUI Navigation

### Global Keyboard Shortcuts

These shortcuts work from any screen:

| Key | Action |
|-----|--------|
| `Q` | Quit the application |
| `S` | Go to Search screen |
| `D` | Go to Downloads queue |
| `,` | Open Settings |
| `?` | Toggle help |
| `Escape` | Go back / Cancel |

### Screen-Specific Shortcuts

#### Search Screen

| Key | Action |
|-----|--------|
| `Enter` | Search / Select result |
| `Up/Down` | Navigate results |
| `Tab` | Move between panels |
| `Space` | Toggle selection |
| `A` | Select all |
| `Ctrl+A` | Add selected to queue |

#### Queue Screen

| Key | Action |
|-----|--------|
| `Up/Down` | Navigate queue items |
| `Delete` | Remove selected item |
| `P` | Pause/Resume download |
| `C` | Clear completed |
| `R` | Retry failed |

#### Settings Screen

| Key | Action |
|-----|--------|
| `Up/Down` | Navigate settings |
| `Enter` | Edit setting |
| `Tab` | Move between sections |
| `Escape` | Cancel edit |

## Search and Download

### Searching by Text

1. Press `S` to ensure you're on the search screen
2. Type your search query:
   - Song name: `Bohemian Rhapsody`
   - Artist and song: `Queen Bohemian Rhapsody`
   - Artist name: `Queen` (shows top songs)
3. Press `Enter` to search

### Searching by URL

Paste a URL directly into the search field:

**Spotify:**
```
https://open.spotify.com/track/4u7EnebtmKWzUH433cf5Qv
https://open.spotify.com/album/1GbtB4zTqAsyfZEsm1RZfx
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

**Apple Music:**
```
https://music.apple.com/us/album/song-name/123456789
```

**Deezer:**
```
https://www.deezer.com/track/123456789
```

**SoundCloud:**
```
https://soundcloud.com/artist/track-name
```

**YouTube/YouTube Music:**
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://music.youtube.com/watch?v=dQw4w9WgXcQ
```

### Understanding Search Results

Search results display:

```
Title                Artist              Album              Duration
-------------------------------------------------------------------------
Bohemian Rhapsody   Queen               A Night at the...  5:55
Bohemian Rhapsody   Queen               Greatest Hits      5:55
Bohemian Rhapsody   The Muppets         Muppets Most...    3:42
```

- **Bold text**: Exact matches
- **Match score**: Shows how well the result matches (when using backend)
- **Platform icon**: Indicates source platform

### Selecting Songs

**Single selection:**
- Navigate with arrow keys
- Press `Enter` to select

**Multiple selection:**
- Press `Space` to toggle selection on current item
- Press `A` to select all visible results
- Press `Ctrl+A` to add all selected to queue

## Queue Management

### Viewing the Queue

Press `D` to open the download queue screen.

Queue displays:
- **Pending**: Waiting to download
- **Downloading**: Currently in progress (with progress bar)
- **Completed**: Successfully downloaded
- **Failed**: Download errors

### Queue Item States

| Status | Description |
|--------|-------------|
| Pending | Queued, waiting for a download slot |
| Matching | Finding audio source |
| Downloading | Downloading audio |
| Processing | Converting/embedding metadata |
| Completed | Successfully finished |
| Failed | Error occurred |

### Managing Queue Items

**Remove items:**
- Select item and press `Delete`
- Or right-click for context menu

**Retry failed:**
- Select failed item
- Press `R` to retry

**Clear completed:**
- Press `C` to clear all completed items

**Pause/Resume:**
- Press `P` to pause active downloads
- Press `P` again to resume

### Download Progress

Each downloading item shows:
- Song title and artist
- Progress bar with percentage
- Download speed
- Estimated time remaining

```
Downloading: Queen - Bohemian Rhapsody
[===================>        ] 75% | 2.3 MB/s | ETA: 0:15
```

## Settings

Press `,` to open the settings screen.

### Download Settings

| Setting | Description |
|---------|-------------|
| Output Directory | Where downloads are saved |
| Audio Format | mp3, m4a, flac, opus, ogg, wav |
| Audio Quality | best, 320k, 256k, 192k, 128k |
| Concurrent Downloads | Number of parallel downloads (1-16) |
| Overwrite | Replace existing files |

### Output Template

Customize how files are named:

```
{artist} - {title}                    -> Queen - Bohemian Rhapsody.mp3
{artist}/{album}/{title}              -> Queen/A Night.../Bohemian Rhapsody.mp3
{artist}/{album}/{track_number}. {title} -> Queen/A Night.../1. Bohemian Rhapsody.mp3
```

### Metadata Settings

| Setting | Description |
|---------|-------------|
| Embed Metadata | Add ID3 tags |
| Embed Lyrics | Include lyrics if available |
| Embed Cover | Include album artwork |

### Connection Settings

| Setting | Description |
|---------|-------------|
| API URL | Backend server URL |
| API Timeout | Request timeout in seconds |
| Offline Mode | Use local matching only |

## Onboarding

First-time users see an onboarding wizard that helps configure:

1. **Output directory** - Where to save downloads
2. **Audio preferences** - Format and quality
3. **API connection** - Backend URL (or offline mode)
4. **Spotify credentials** - Optional, for private playlists

Complete the wizard or press `Escape` to use defaults.

## Connection Modes

### Online Mode (Default)

When connected to the backend API:
- Uses community-verified matches
- Access to voting system
- Better match accuracy
- Larger match database

The header shows: `SpotDL - Connected`

### Offline Mode

When the backend is unavailable or offline mode is enabled:
- Uses local matching algorithms
- No community features
- Matches are cached locally
- Works without internet (for cached content)

The header shows: `SpotDL - Offline Mode`

## Keyboard Reference

### Navigation

| Key | Action |
|-----|--------|
| `Up` / `k` | Move up |
| `Down` / `j` | Move down |
| `Page Up` | Page up |
| `Page Down` | Page down |
| `Home` | Go to top |
| `End` | Go to bottom |
| `Tab` | Next panel |
| `Shift+Tab` | Previous panel |

### Selection

| Key | Action |
|-----|--------|
| `Enter` | Confirm / Select |
| `Space` | Toggle selection |
| `Escape` | Cancel / Back |

### Text Input

| Key | Action |
|-----|--------|
| `Ctrl+A` | Select all text |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+U` | Clear line |
| `Backspace` | Delete character |

## Tips and Tricks

### Batch Downloads

1. Search for an album or playlist URL
2. All tracks appear in results
3. Press `A` to select all
4. Press `Ctrl+A` to add all to queue

### Finding Better Matches

If a download sounds wrong:
1. Delete the file
2. Search again
3. Look for alternative matches
4. Vote on matches in the web interface

### Handling Errors

Common errors and solutions:

| Error | Solution |
|-------|----------|
| "No matches found" | Try a different search query |
| "Download failed" | Check internet connection, retry |
| "Rate limited" | Wait a few minutes |
| "API unavailable" | Check backend status or use offline mode |

### Performance Tips

- Adjust concurrent downloads based on your connection
- Use mp3 format for faster processing
- Close other bandwidth-heavy applications
- Use a local backend for best performance

## See Also

- [Quick Start Guide](../getting-started/quickstart.md)
- [Configuration Reference](../getting-started/configuration.md)
- [Web Interface Guide](./web-interface.md)
