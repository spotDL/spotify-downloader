# SpotDL Backend Dockerfile
FROM python:3.13-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Install shared core package into the backend venv.
# Railway currently builds this service from /backend root, so we pull core as a package.
RUN uv pip install --python /app/.venv/bin/python \
    "git+https://github.com/xnetcat/spotify-downloader.git@xnetcat-rewrite#subdirectory=core"

# Production image
FROM python:3.13-slim

# Install curl for healthcheck and ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r spotdl && useradd -r -g spotdl spotdl

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy backend app
COPY src/spotdl/ src/spotdl/
COPY alembic/ alembic/
COPY alembic.ini .

# Create data and static directories
RUN mkdir -p /app/data /app/static && chown -R spotdl:spotdl /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER spotdl

# Expose port
EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "spotdl.main:app", "--host", "0.0.0.0", "--port", "8000"]
