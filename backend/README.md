# SpotDL Backend

Multi-platform music matching and download API.

## Features

- Multi-platform song resolution (Spotify, Deezer, Apple Music, Tidal, YouTube Music)
- Audio source matching (YouTube, YouTube Music, SoundCloud, Bandcamp)
- User match submissions and voting
- RESTful API with FastAPI
- WebSocket support for real-time progress

## Development

```bash
# Install dependencies
uv sync --dev

# Run development server
uv run uvicorn spotdl.main:app --reload

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
uv run mypy src
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
