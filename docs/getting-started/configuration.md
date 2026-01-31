# Configuration Reference

SpotDL uses environment variables and settings files for configuration. This document covers all available options.

## Environment Variables

### Backend (API) Configuration

The backend reads configuration from environment variables. These can be set directly or via a `.env` file in the project root.

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `SpotDL API` | Application name |
| `APP_VERSION` | `5.0.0` | Application version |
| `DEBUG` | `false` | Enable debug mode |
| `ENVIRONMENT` | `development` | Environment: `development`, `staging`, `production` |

#### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `1` | Number of worker processes |
| `RELOAD` | `false` | Enable auto-reload (development) |

#### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/spotdl.db` | Database connection URL |
| `DATABASE_ECHO` | `false` | Echo SQL queries (debugging) |

**SQLite (Development):**
```bash
DATABASE_URL=sqlite+aiosqlite:///./data/spotdl.db
```

**PostgreSQL (Production):**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

#### Redis Settings (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `null` | Redis connection URL |
| `CACHE_TTL` | `3600` | Cache time-to-live in seconds |

```bash
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
```

#### Authentication Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required in production) | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token expiration |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiration |
| `ALGORITHM` | `HS256` | JWT algorithm |

Generate a secure secret key:
```bash
openssl rand -hex 32
```

#### CORS Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials |
| `CORS_ALLOW_METHODS` | `*` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `*` | Allowed headers |

#### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_REQUESTS` | `100` | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window size in seconds |

#### Matching Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MATCH_SCORE_THRESHOLD` | `80.0` | Minimum match score (0-100) |
| `ISRC_MATCH_THRESHOLD` | `80.0` | ISRC match threshold |

#### External Services

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTIFY_CLIENT_ID` | `null` | Spotify API client ID |
| `SPOTIFY_CLIENT_SECRET` | `null` | Spotify API client secret |

### CLI Configuration

The CLI uses environment variables with the `SPOTDL_` prefix.

#### Directory Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_CONFIG_DIR` | Platform-specific | Configuration directory |
| `SPOTDL_DATA_DIR` | Platform-specific | Data directory |
| `SPOTDL_CACHE_DIR` | Platform-specific | Cache directory |
| `SPOTDL_OUTPUT_DIR` | `~/Music/SpotDL` | Download output directory |

Default directories by platform:
- **macOS:** `~/Library/Application Support/spotdl`
- **Linux:** `~/.config/spotdl`
- **Windows:** `%APPDATA%\spotdl`

#### API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_API_URL` | `http://localhost:8000` | Backend API URL |
| `SPOTDL_API_TIMEOUT` | `30.0` | API request timeout (seconds) |
| `SPOTDL_OFFLINE_MODE` | `false` | Enable offline mode |

#### Download Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_AUDIO_FORMAT` | `mp3` | Audio format |
| `SPOTDL_AUDIO_QUALITY` | `best` | Audio quality preset |
| `SPOTDL_THREADS` | `4` | Concurrent download threads |
| `SPOTDL_OVERWRITE` | `false` | Overwrite existing files |

**Audio Formats:** `mp3`, `m4a`, `flac`, `opus`, `ogg`, `wav`

**Quality Presets:** `best`, `320k`, `256k`, `192k`, `128k`

#### Output Template

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_OUTPUT_TEMPLATE` | `{artist} - {title}` | Output filename template |

Available placeholders:
- `{title}` - Song title
- `{artist}` - Primary artist
- `{artists}` - All artists joined
- `{album}` - Album name
- `{track_number}` - Track number
- `{disc_number}` - Disc number
- `{year}` - Release year
- `{genre}` - Genre
- `{isrc}` - ISRC code

Example templates:
```bash
# Simple
SPOTDL_OUTPUT_TEMPLATE="{artist} - {title}"

# Organized by artist and album
SPOTDL_OUTPUT_TEMPLATE="{artist}/{album}/{track_number}. {title}"

# Include year
SPOTDL_OUTPUT_TEMPLATE="{artist} - {title} ({year})"
```

#### Metadata Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_EMBED_METADATA` | `true` | Embed ID3/metadata tags |
| `SPOTDL_EMBED_LYRICS` | `true` | Embed lyrics if available |
| `SPOTDL_EMBED_COVER` | `true` | Embed album artwork |

#### Spotify Credentials

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_SPOTIFY_CLIENT_ID` | `null` | Spotify client ID |
| `SPOTDL_SPOTIFY_CLIENT_SECRET` | `null` | Spotify client secret |
| `SPOTDL_SPOTIFY_USER_AUTH` | `false` | Enable OAuth for private playlists |

#### SoundCloud Credentials (CLI only)

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_SOUNDCLOUD_CLIENT_ID` | `null` | SoundCloud client ID |
| `SPOTDL_SOUNDCLOUD_AUTH_TOKEN` | `null` | SoundCloud auth token |

#### Matching Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `SPOTDL_NAME_MATCH_THRESHOLD` | `60.0` | Song name match threshold |
| `SPOTDL_ARTIST_MATCH_THRESHOLD` | `70.0` | Artist match threshold |
| `SPOTDL_TIME_MATCH_THRESHOLD` | `25.0` | Duration match threshold |

## Settings File Locations

### Backend

The backend reads from a `.env` file in the project root:

```
spotify-downloader/
  .env              # Environment variables
  backend/
    src/
      spotdl/
        config.py   # Settings class definition
```

### CLI

The CLI looks for configuration in these locations (in order):

1. Environment variables
2. `.env` file in current directory
3. `.env` file in config directory

```
~/.config/spotdl/   # Linux
~/Library/Application Support/spotdl/   # macOS
%APPDATA%\spotdl\   # Windows
```

Files in config directory:
- `settings.json` - Persistent settings
- `cookies.txt` - Browser cookies for authentication
- `cache.db` - Local cache database

### Docker

For Docker deployments, configure via environment variables in `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379
```

Or use an `.env` file:

```bash
# .env
SECRET_KEY=your-secret-key
DB_PASSWORD=your-password
```

## Example Configurations

### Development Setup

```bash
# .env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./data/spotdl.db
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Production Setup

```bash
# .env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://spotdl:password@db:5432/spotdl
REDIS_URL=redis://redis:6379
SECRET_KEY=your-generated-secret-key
CORS_ORIGINS=https://spotdl.yourdomain.com
```

### CLI Power User

```bash
# ~/.config/spotdl/.env
SPOTDL_OUTPUT_DIR=/mnt/music/SpotDL
SPOTDL_AUDIO_FORMAT=flac
SPOTDL_AUDIO_QUALITY=best
SPOTDL_THREADS=8
SPOTDL_OUTPUT_TEMPLATE={artist}/{album}/{track_number}. {title}
SPOTDL_EMBED_METADATA=true
SPOTDL_EMBED_LYRICS=true
SPOTDL_EMBED_COVER=true
SPOTDL_API_URL=https://spotdl.yourdomain.com
```

## Validation

Settings are validated using Pydantic. Invalid values will raise clear error messages at startup.

Common validation errors:
- Invalid database URL format
- Missing required secrets in production
- Invalid enum values (format, quality, environment)
- Port numbers out of range
- Thread count outside allowed range (1-16)

## See Also

- [Installation Guide](./installation.md)
- [Quick Start Guide](./quickstart.md)
- [Self-Hosting Guide](../guides/self-hosting.md)
