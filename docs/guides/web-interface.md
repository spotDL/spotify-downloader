# Web Interface Guide

The SpotDL web interface provides a browser-based way to search for music, manage downloads, and contribute to the community match database.

## Accessing the Interface

### Development

```bash
# Using Docker
docker compose up -d
# Access at http://localhost:3000

# Manual
cd frontend && pnpm dev
# Access at http://localhost:5173
```

### Production

Access your deployed instance at your configured domain (e.g., `https://spotdl.yourdomain.com`).

## Searching for Songs

### Text Search

1. Enter a search query in the search bar:
   - Song name: `Bohemian Rhapsody`
   - Artist and song: `Queen Bohemian Rhapsody`
   - Album name: `A Night at the Opera`

2. Press `Enter` or click the search button

3. Results appear in a list showing:
   - Song title
   - Artist name(s)
   - Album name
   - Duration
   - Source platform

### URL Search

Paste a URL directly into the search bar:

- Spotify tracks, albums, playlists
- Apple Music tracks, albums
- Deezer tracks, albums
- SoundCloud tracks
- YouTube videos

The system automatically detects the platform and fetches the content.

### Search Filters

Use filters to narrow results:

- **Platform**: Filter by source platform
- **Type**: Tracks, albums, or playlists
- **Duration**: Filter by song length

## Viewing Song Details

Click on a song to view its details:

### Song Information

- **Title**: Full song name
- **Artists**: All credited artists
- **Album**: Album name and artwork
- **Duration**: Song length
- **ISRC**: International Standard Recording Code (if available)
- **Release Date**: When the song was released

### Available Matches

The matches section shows potential audio sources:

```
YouTube Music                    Score: 95.2    +42  -3
https://music.youtube.com/...

YouTube                          Score: 87.5    +28  -1
https://youtube.com/...

SoundCloud                       Score: 82.1    +15  -0
https://soundcloud.com/...
```

Each match displays:
- **Platform**: Where the audio is from
- **Score**: Match confidence (0-100)
- **Votes**: Upvotes and downvotes
- **URL**: Link to the audio source

### Match Quality Indicators

| Score | Quality |
|-------|---------|
| 90-100 | Excellent match |
| 80-89 | Good match |
| 70-79 | Acceptable |
| Below 70 | May be incorrect |

## Download Queue

### Adding to Queue

1. Click on a song in search results
2. View available matches
3. Click "Download" on your preferred match
4. Or click "Download Best" to use the top match

### Queue Management

The queue panel shows:

- **Pending**: Waiting to start
- **Active**: Currently downloading
- **Completed**: Successfully downloaded
- **Failed**: Errors encountered

### Queue Actions

| Action | Description |
|--------|-------------|
| Pause | Pause all downloads |
| Resume | Resume paused downloads |
| Clear Completed | Remove finished items |
| Retry Failed | Retry failed downloads |
| Cancel | Cancel a pending/active download |

### Download Progress

Active downloads show:
- Progress bar
- Percentage complete
- Download speed
- Estimated time remaining

## Voting on Matches

Help improve match quality by voting.

### How Voting Works

- **Upvote**: The match sounds correct
- **Downvote**: The match is wrong or low quality

### Voting Guidelines

**Upvote when:**
- The audio matches the song
- Audio quality is acceptable
- No significant issues

**Downvote when:**
- Wrong song entirely
- Cover version when original expected
- Poor audio quality (distortion, cuts)
- Missing parts of the song
- Wrong language/version

### Voting Impact

Votes affect match ranking:
- Higher voted matches appear first
- Matches with many downvotes are deprioritized
- Community voting improves results for everyone

## Submitting Matches

If you find a better match, you can submit it.

### Submitting a New Match

1. View song details
2. Click "Submit Match"
3. Enter the URL of the audio source
4. Select the platform
5. Add optional notes
6. Click "Submit"

### Supported Platforms for Submission

- YouTube
- YouTube Music
- SoundCloud
- Bandcamp

### Submission Guidelines

- Ensure the audio is correct
- Prefer official uploads when available
- Check audio quality before submitting
- Avoid live versions unless specified

## User Features

### Registration (Optional)

Create an account to:
- Track your voting history
- Submit matches
- View your contributions
- Maintain reputation

### User Dashboard

View your activity:
- Submitted matches
- Voting history
- Contribution statistics

## Interface Customization

### Theme

Toggle between light and dark themes using the theme button.

### Display Options

- **Compact View**: Show more results per page
- **Detailed View**: Show more information per result

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search bar |
| `Escape` | Clear search / Close modal |
| `Enter` | Submit search |
| `j` / `Down` | Next result |
| `k` / `Up` | Previous result |
| `Enter` | Select result |
| `d` | Toggle downloads panel |

## Mobile Support

The web interface is responsive and works on mobile devices:

- Touch-friendly buttons
- Swipe gestures for navigation
- Optimized layout for small screens

## API Access

The web interface communicates with the backend API at `/api/v1/`.

### Available Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/songs/search` - Search songs
- `GET /api/v1/matches/{url}` - Get matches for URL
- `POST /api/v1/votes` - Submit a vote
- `POST /api/v1/matches` - Submit a match

See the [API Documentation](../api/) for complete details.

## Troubleshooting

### Search Not Working

1. Check if the backend is running
2. Verify the API URL in browser console
3. Check for CORS errors

### No Matches Found

1. Try a different search query
2. Check if the song exists on supported platforms
3. Submit a match if you find one

### Downloads Not Starting

1. Check the queue panel for errors
2. Verify network connectivity
3. Check browser console for errors

### Voting Not Saving

1. Ensure you're logged in (if required)
2. Check network connectivity
3. Try refreshing the page

## See Also

- [Quick Start Guide](../getting-started/quickstart.md)
- [CLI Usage Guide](./cli-usage.md)
- [Self-Hosting Guide](./self-hosting.md)
