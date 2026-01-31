# SpotDL CLI Dockerfile
# Builds the TUI application for running spotdl in a container
#
# Build from project root (not from cli/):
#   docker build -t spotdl-cli -f cli/Dockerfile .
#   docker run -it -v ~/Music:/downloads spotdl-cli

FROM python:3.13-slim AS builder

# Install build dependencies and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy core library first (CLI depends on it)
COPY core/pyproject.toml core/uv.lock* ./core/
COPY core/src/ ./core/src/

# Copy CLI dependency files
COPY cli/pyproject.toml cli/uv.lock* ./cli/

WORKDIR /app/cli

# Install dependencies (with local core)
RUN uv sync --frozen --no-dev --no-install-project

# Production image
FROM python:3.13-slim

# Install ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r spotdl && useradd -r -g spotdl -m spotdl

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/cli/.venv /app/.venv

# Copy core library source
COPY core/src/ /app/core/src/

# Copy CLI application code
COPY cli/src/ /app/src/

# Create downloads directory
RUN mkdir -p /downloads && chown -R spotdl:spotdl /downloads /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/core/src"
ENV PYTHONUNBUFFERED=1
# Default download directory
ENV SPOTDL_OUTPUT_DIR=/downloads

# Switch to non-root user
USER spotdl

# Set working directory to downloads
WORKDIR /downloads

# Run the TUI application
ENTRYPOINT ["python", "-m", "spotdl_cli"]
