# SpotDL

Multi-platform music matching and download system. Match songs from any streaming platform to downloadable audio sources.

## Features

- **Multi-Platform Support**: Resolve songs from Spotify, Apple Music, Deezer, Tidal, YouTube Music, SoundCloud, and Bandcamp
- **Smart Matching**: Advanced matching algorithm to find the best audio source on YouTube, YouTube Music, SoundCloud, Bandcamp, and Piped
- **Community Voting**: Users can submit and vote on match quality to improve results
- **Multiple Interfaces**: Interactive CLI (TUI), self-hosted web interface, or API
- **Offline Mode**: CLI works completely offline without a backend server

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/spotDL/spotify-downloader.git
cd spotify-downloader

# Start with Docker Compose
docker compose up -d

# Access the web interface at http://localhost:3000
# API available at http://localhost:8000
```

### CLI Only

```bash
# Install the CLI
pip install spotdl-cli

# Run the interactive TUI
spotdl
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
├──────────────────────┬──────────────────────────────────────────┤
│   CLI (Textual)      │         React Frontend                   │
│   - Download songs   │         - Search/download                │
│   - Queue mgmt       │         - Vote on matches                │
│   - Offline mode     │         - Submit user matches            │
└──────────┬───────────┴─────────────────┬────────────────────────┘
           │                             │
           ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
├─────────────────────────────────────────────────────────────────┤
│  REST API          │  WebSocket         │  Matching Engine       │
│  - /api/v1/*       │  - Progress        │  - Multi-stage scoring │
├─────────────────────────────────────────────────────────────────┤
│                    PROVIDERS                                     │
│  Sources: Spotify, Apple Music, Deezer, Tidal, YTM, SC, BC      │
│  Targets: YouTube, YouTube Music, SoundCloud, Bandcamp, Piped   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Description | Directory |
|-----------|-------------|-----------|
| **Backend** | FastAPI server with matching engine and API | [`backend/`](./backend/) |
| **CLI** | Interactive terminal interface with Textual | [`cli/`](./cli/) |
| **Frontend** | React web interface | [`frontend/`](./frontend/) |
| **Core** | Shared library with providers and types | [`core/`](./core/) |

## Development

### Prerequisites

- Python 3.13+
- Node.js 22+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)

### Setup

```bash
# Install all dependencies
make install-dev

# Start development servers
make dev

# Run all tests
make test

# Run linting and type checking
make lint
make typecheck
```

### Running Individual Components

```bash
# Backend only
make dev-backend

# Frontend only
make dev-frontend

# CLI in development mode
make dev-cli
```

### Testing

```bash
# Run all tests with coverage
make coverage

# Run specific component tests
make test-backend
make test-frontend
make test-cli
```

## Deployment

### Self-Hosting (Simple)

```bash
# Uses SQLite, no external dependencies
docker compose up -d
```

### Production

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start production stack (PostgreSQL + Redis + Nginx)
docker compose -f docker-compose.prod.yml up -d
```

See [Self-Hosting Guide](./docs/guides/self-hosting.md) for detailed instructions.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required in production |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/spotdl.db` |
| `REDIS_URL` | Redis connection (optional) | None |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

### CLI Configuration

Settings are stored in your platform's config directory:
- Linux: `~/.config/spotdl/`
- macOS: `~/Library/Application Support/spotdl/`
- Windows: `%APPDATA%\spotdl\`

## API Documentation

When running the backend, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/songs/resolve?url=...` | Resolve any platform URL to song metadata |
| `POST /api/v1/matches/find` | Find audio matches for a song |
| `POST /api/v1/matches/submit` | Submit a user-discovered match |
| `POST /api/v1/votes` | Vote on match quality |

## Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/development/contributing.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`make test`)
5. Submit a Pull Request

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Audio downloading
- [mutagen](https://mutagen.readthedocs.io/) - Metadata embedding
- [rapidfuzz](https://github.com/maxbachmann/RapidFuzz) - Fuzzy string matching
- [Textual](https://textual.textualize.io/) - Terminal UI framework
