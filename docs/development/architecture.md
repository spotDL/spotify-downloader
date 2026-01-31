# Architecture Overview

This document describes the high-level architecture of SpotDL v5, including system design, component interaction, database schema, and caching strategy.

## System Design

SpotDL v5 follows a modular architecture with clear separation of concerns:

```
                                    +------------------+
                                    |    Frontend      |
                                    |  (React + Vite)  |
                                    +--------+---------+
                                             |
                                             | HTTP/WebSocket
                                             v
+------------------+              +----------+-----------+
|     CLI          |  HTTP/JSON   |      Backend         |
| (Textual TUI)    +------------->|    (FastAPI)         |
+--------+---------+              +----------+-----------+
         |                                   |
         |                                   |
         v                                   v
+--------+---------+              +----------+-----------+
|    Core Library  |              |     Database         |
| (Providers +     |              |   (PostgreSQL/       |
|  Matching)       |              |    SQLite)           |
+------------------+              +----------+-----------+
                                             |
                                             v
                                  +----------+-----------+
                                  |      Redis           |
                                  |    (Cache)           |
                                  +----------------------+
```

## Component Overview

### Core Library (`spotdl-core`)

The shared library containing platform-agnostic code:

```
core/src/spotdl_core/
+-- __init__.py          # Public API exports
+-- types/               # Shared type definitions
|   +-- song.py         # Song, SongList, Result
|   +-- platform.py     # Platform enums
+-- providers/           # Platform integrations
|   +-- source/         # Source providers (Spotify, Apple, etc.)
|   +-- target/         # Target providers (YouTube, SoundCloud, etc.)
|   +-- metadata/       # Metadata enrichment (MusicBrainz, Discogs)
+-- matching/            # Matching algorithms
    +-- matcher.py      # Core matching logic
    +-- scoring.py      # Score calculation
```

**Key Responsibilities:**
- Platform URL detection and validation
- Song metadata fetching from source platforms
- Audio source searching on target platforms
- Match scoring and ranking
- Metadata enrichment

### Backend (`spotdl-backend`)

FastAPI-based REST API server:

```
backend/src/spotdl/
+-- __init__.py
+-- main.py              # Application entry point
+-- config.py            # Settings management
+-- api/
|   +-- v1/
|       +-- __init__.py  # Router aggregation
|       +-- health.py    # Health check endpoints
|       +-- songs.py     # Song search endpoints
|       +-- matches.py   # Match CRUD endpoints
|       +-- votes.py     # Voting endpoints
+-- core/                # Business logic
|   +-- matching.py      # Match orchestration
+-- db/
|   +-- database.py      # Connection management
|   +-- models/          # SQLAlchemy models
|   +-- repositories/    # Data access layer
+-- cache/
|   +-- redis.py         # Redis integration
+-- providers/           # Backend-specific providers
```

**Key Responsibilities:**
- RESTful API for web and CLI clients
- Match database management
- Vote aggregation
- Caching layer
- Authentication and authorization

### CLI (`spotdl-cli`)

Terminal user interface built with Textual:

```
cli/src/spotdl_cli/
+-- __init__.py
+-- __main__.py          # Entry point
+-- app.py               # Main Textual application
+-- app.tcss             # Textual CSS styles
+-- config.py            # CLI settings
+-- core/
|   +-- api_client.py    # Backend HTTP client
|   +-- download.py      # Download manager
|   +-- queue.py         # Download queue
|   +-- offline.py       # Offline mode logic
+-- screens/
|   +-- main.py          # Search screen
|   +-- queue.py         # Download queue screen
|   +-- settings.py      # Settings screen
|   +-- onboarding.py    # First-run wizard
+-- widgets/             # Reusable UI components
```

**Key Responsibilities:**
- Interactive search interface
- Download queue management
- Audio downloading via yt-dlp
- Metadata embedding with mutagen
- Local caching

### Frontend (`spotdl-frontend`)

React single-page application:

```
frontend/src/
+-- main.tsx             # React entry point
+-- index.css            # Global styles (Tailwind)
+-- api/                 # API client layer
|   +-- client.ts        # Axios instance
|   +-- songs.ts         # Song API hooks
|   +-- matches.ts       # Match API hooks
|   +-- votes.ts         # Vote API hooks
+-- components/          # Reusable UI components
|   +-- SearchBar.tsx
|   +-- SongCard.tsx
|   +-- MatchList.tsx
|   +-- VoteButtons.tsx
+-- routes/              # TanStack Router pages
|   +-- __root.tsx       # Root layout
|   +-- index.tsx        # Home page
|   +-- search.tsx       # Search page
+-- stores/              # Zustand state stores
|   +-- queue.ts         # Download queue state
|   +-- settings.ts      # User settings
+-- types/               # TypeScript types
```

**Key Responsibilities:**
- Web-based search interface
- Match visualization
- Voting interface
- Real-time queue updates

## Component Interaction

### Search Flow

```
1. User enters query in CLI or Frontend
2. Client sends request to Backend API
3. Backend checks cache for existing results
4. If not cached:
   a. Query source provider (Spotify, Apple, etc.)
   b. Store song metadata in database
   c. Cache results in Redis
5. Return results to client
```

### Match Flow

```
1. User requests matches for a song
2. Backend checks for existing matches in database
3. If no matches or matches are stale:
   a. Query target providers (YouTube, SoundCloud, etc.)
   b. Score each potential match
   c. Store new matches in database
4. Sort matches by score and votes
5. Return ranked matches to client
```

### Download Flow (CLI)

```
1. User adds song to download queue
2. Queue manager assigns download slot
3. API client fetches best match
4. yt-dlp downloads audio from target URL
5. Mutagen embeds metadata and artwork
6. File saved to output directory
7. Queue updated with completion status
```

### Voting Flow

```
1. User votes on a match (upvote/downvote)
2. Client sends vote to Backend API
3. Backend validates vote (one vote per user per match)
4. Database updates vote counts
5. Match ranking recalculated
6. Updated data returned to client
```

## Database Schema

### Entity Relationship Diagram

```
+---------------+       +---------------+       +---------------+
|    songs      |       |    matches    |       |    votes      |
+---------------+       +---------------+       +---------------+
| id (UUID)     |<---+  | id (UUID)     |<---+  | id (UUID)     |
| platform      |    |  | source_song_id|----+  | match_id      |----+
| platform_id   |    |  | source_url    |       | user_id       |----+
| platform_url  |    |  | target_platform|      | vote_type     |    |
| name          |    |  | target_url    |       | created_at    |    |
| artists       |    |  | match_type    |       +---------------+    |
| album_name    |    |  | match_score   |                            |
| duration_secs |    |  | upvotes       |                            |
| isrc          |    |  | downvotes     |       +---------------+    |
| metadata_json |    |  | submitted_by  |----+  |    users      |    |
| created_at    |    |  | verified_by   |----+  +---------------+    |
| updated_at    |    |  | created_at    |    +--| id (UUID)     |<---+
+---------------+    |  | updated_at    |       | username      |
                     |  +---------------+       | email         |
                     |                          | password_hash |
                     +--------------------------| created_at    |
                                                +---------------+
```

### Table Definitions

#### songs

Caches song metadata from source platforms.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| platform | VARCHAR(50) | Source platform (spotify, apple, etc.) |
| platform_id | VARCHAR(255) | Platform-specific ID |
| platform_url | TEXT | Original URL |
| name | VARCHAR(500) | Song title |
| artists | JSONB | Array of artist names |
| album_name | VARCHAR(500) | Album title |
| duration_seconds | INTEGER | Song duration |
| isrc | VARCHAR(20) | ISRC code (if available) |
| metadata_json | JSONB | Additional platform-specific data |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

#### matches

Stores song-to-audio-source mappings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| source_song_id | UUID | Foreign key to songs |
| source_platform | VARCHAR(50) | Source platform |
| source_url | TEXT | Source song URL |
| target_platform | VARCHAR(50) | Target platform |
| target_url | TEXT | Audio source URL |
| match_type | VARCHAR(20) | 'system' or 'user' |
| match_score | DECIMAL(5,2) | Algorithm confidence score |
| upvotes | INTEGER | Positive votes |
| downvotes | INTEGER | Negative votes |
| submitted_by | UUID | User who submitted (nullable) |
| verified_by | UUID | Verifying moderator (nullable) |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

#### votes

Tracks user votes on matches.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| match_id | UUID | Foreign key to matches |
| user_id | UUID | Foreign key to users |
| vote_type | VARCHAR(10) | 'up' or 'down' |
| created_at | TIMESTAMP | Vote time |

#### users

User accounts for voting and submissions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| username | VARCHAR(100) | Unique username |
| email | VARCHAR(255) | Unique email |
| password_hash | VARCHAR(255) | Bcrypt hash |
| is_active | BOOLEAN | Account status |
| is_superuser | BOOLEAN | Admin flag |
| created_at | TIMESTAMP | Registration time |

### Indexes

```sql
-- Song lookups
CREATE INDEX ix_songs_platform ON songs(platform);
CREATE INDEX ix_songs_platform_id ON songs(platform_id);
CREATE INDEX ix_songs_isrc ON songs(isrc);
CREATE UNIQUE INDEX uq_songs_platform_id ON songs(platform, platform_id);

-- Match lookups
CREATE INDEX ix_matches_source_url ON matches(source_url);
CREATE INDEX ix_matches_source_platform ON matches(source_platform);
CREATE INDEX ix_matches_target_platform ON matches(target_platform);
CREATE UNIQUE INDEX uq_matches_source_target ON matches(source_url, target_platform, target_url);

-- Vote constraints
CREATE UNIQUE INDEX uq_votes_match_user ON votes(match_id, user_id);
```

## Caching Strategy

### Cache Layers

1. **Redis Cache** (Backend)
   - Song search results: 1 hour TTL
   - Match results: 24 hour TTL
   - Rate limiting counters: 1 minute TTL

2. **In-Memory Cache** (CLI)
   - Recent searches: Session duration
   - Downloaded metadata: Persistent SQLite

3. **HTTP Cache** (Frontend)
   - React Query cache: 5 minute stale time
   - Browser cache: Static assets

### Cache Keys

```
# Song search results
songs:search:{platform}:{query_hash}

# Matches for a source URL
matches:{url_hash}

# Rate limiting
ratelimit:{ip}:{endpoint}
```

### Cache Invalidation

- **Time-based**: TTL expiration
- **Event-based**:
  - New match submitted: Invalidate match cache
  - Vote cast: Update cached vote counts
- **Manual**: Admin flush endpoints

### Redis Configuration

```python
# Cache settings in config.py
redis_url: RedisDsn | None = None
cache_ttl: int = 3600  # 1 hour default

# Cache usage
async def get_cached_matches(url: str) -> list[Match] | None:
    cache_key = f"matches:{hash_url(url)}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

async def set_cached_matches(url: str, matches: list[Match]) -> None:
    cache_key = f"matches:{hash_url(url)}"
    await redis.setex(cache_key, settings.cache_ttl, json.dumps(matches))
```

## Error Handling

### Backend Errors

```python
# Custom exception hierarchy
class SpotDLError(Exception): pass
class ProviderError(SpotDLError): pass
class MatchNotFoundError(SpotDLError): pass
class RateLimitError(SpotDLError): pass
```

### API Error Responses

```json
{
  "detail": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

## Security Model

### Authentication

- JWT tokens for API authentication
- Refresh tokens for session extension
- Password hashing with bcrypt

### Authorization

- Public endpoints: Search, view matches
- Authenticated: Vote, submit matches
- Admin: User management, data moderation

### Rate Limiting

- API: 10 requests/second per IP
- Search: 5 requests/second per IP
- Voting: 1 vote/second per user

## See Also

- [Contributing Guide](./contributing.md)
- [Self-Hosting Guide](../guides/self-hosting.md)
- [Configuration Reference](../getting-started/configuration.md)
