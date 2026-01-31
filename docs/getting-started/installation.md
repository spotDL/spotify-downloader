# Installation

This guide covers the different ways to install and run SpotDL v5.

## Prerequisites

Before installing SpotDL, ensure you have the following:

- **Python 3.13+** (required for backend and CLI)
- **Node.js 22+** (required for frontend)
- **pnpm** (recommended package manager for frontend)
- **uv** (recommended Python package manager)
- **Docker** (optional, for containerized deployment)

## Docker Installation (Recommended)

Docker is the easiest way to get SpotDL running with all components.

### Quick Start with Docker Compose

1. Clone the repository:

```bash
git clone https://github.com/spotDL/spotify-downloader.git
cd spotify-downloader
```

2. Copy the environment file and configure it:

```bash
cp .env.example .env
```

3. Start the development stack:

```bash
docker compose up -d
```

This starts:
- **API** on `http://localhost:8000`
- **Frontend** on `http://localhost:3000`

### Production Deployment

For production, use the production Docker Compose file with PostgreSQL and Redis:

```bash
# Set required environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export DB_PASSWORD=your-secure-password

# Start production stack
docker compose -f docker-compose.prod.yml up -d
```

See the [Self-Hosting Guide](../guides/self-hosting.md) for detailed production setup.

## Manual Installation

### Backend

The backend is a FastAPI application that provides the matching API.

1. Navigate to the backend directory:

```bash
cd backend
```

2. Install dependencies with uv:

```bash
uv sync
```

3. For development dependencies:

```bash
uv sync --dev
```

4. Run the backend server:

```bash
uv run uvicorn spotdl.main:app --reload --host 0.0.0.0 --port 8000
```

### CLI

The CLI is a Textual-based TUI for downloading music.

1. Navigate to the CLI directory:

```bash
cd cli
```

2. Install dependencies:

```bash
uv sync
```

3. Run the CLI:

```bash
uv run python -m spotdl_cli
```

Or use the installed command:

```bash
uv run spotdl
```

### Frontend

The frontend is a React application using TanStack Router and Tailwind CSS.

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
pnpm install
```

3. Start the development server:

```bash
pnpm dev
```

The frontend will be available at `http://localhost:5173`.

### Core Library

The core library contains shared providers and matching logic. It's automatically installed as a dependency of the CLI.

```bash
cd core
uv sync
```

## Using the Makefile

SpotDL includes a Makefile for common operations:

```bash
# Install all dependencies
make install

# Install development dependencies
make install-dev

# Start development servers
make dev

# Start only backend
make dev-backend

# Start only frontend
make dev-frontend

# Start CLI in dev mode
make dev-cli

# Run all tests
make test

# Format and lint code
make lint
make format

# Run type checking
make typecheck
```

## Verifying Installation

### Backend Health Check

```bash
curl http://localhost:8000/api/v1/health
```

You should receive a JSON response indicating the API is running.

### CLI Verification

```bash
spotdl --help
```

Or if running with uv:

```bash
cd cli && uv run spotdl
```

The TUI should launch with the main search screen.

## Troubleshooting

### Python Version Issues

Ensure you have Python 3.13 or later:

```bash
python --version
```

If you have multiple Python versions, specify the version when creating the virtual environment:

```bash
uv venv --python 3.13
```

### Node.js Version Issues

Ensure you have Node.js 22 or later:

```bash
node --version
```

Consider using a version manager like `nvm` or `fnm`.

### Port Conflicts

If ports 8000 or 3000 are in use, modify the port in the respective configuration:

- Backend: Set `PORT` environment variable or modify `config.py`
- Frontend: Modify `vite.config.ts`

### Database Issues

For SQLite (development), ensure the `data` directory exists:

```bash
mkdir -p data
```

For PostgreSQL issues, verify the database is running and credentials are correct.

## Next Steps

- [Quick Start Guide](./quickstart.md) - Get up and running quickly
- [Configuration Reference](./configuration.md) - Configure SpotDL for your needs
- [CLI Usage Guide](../guides/cli-usage.md) - Learn to use the CLI
