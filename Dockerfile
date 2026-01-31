# SpotDL Unified Dockerfile
# Builds both frontend and backend, serves frontend as static files from backend
# Perfect for self-hosting: docker build -t spotdl . && docker run -p 8000:8000 spotdl

# ========================================
# Stage 1: Build Frontend
# ========================================
FROM node:22-alpine AS frontend-builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /frontend

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY frontend/ .

# Build the application
RUN pnpm build

# ========================================
# Stage 2: Build Backend Dependencies
# ========================================
FROM python:3.13-slim AS backend-builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# ========================================
# Stage 3: Production Image
# ========================================
FROM python:3.13-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r spotdl && useradd -r -g spotdl spotdl

WORKDIR /app

# Copy virtual environment from builder
COPY --from=backend-builder /app/.venv /app/.venv

# Copy backend application code
COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .

# Copy frontend build to static directory (served by FastAPI)
COPY --from=frontend-builder /frontend/dist /app/static

# Create data directory
RUN mkdir -p /app/data && chown -R spotdl:spotdl /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
# Default to SQLite for self-hosting
ENV DATABASE_URL=sqlite+aiosqlite:///./data/spotdl.db
ENV ENVIRONMENT=production
ENV DEBUG=false

# Switch to non-root user
USER spotdl

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "spotdl.main:app", "--host", "0.0.0.0", "--port", "8000"]
