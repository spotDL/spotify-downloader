FROM python:3.14-slim-bookworm

LABEL maintainer="Tzur Soffer"

# Allow customizing the user/group IDs
# Default to 1000
ARG UID=1000
ARG GID=1000

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    ffmpeg \
    openssl \
    aria2 \
    g++ \
    git \
    libffi-dev \
    zlib1g-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv and update pip/wheel
RUN pip install --no-cache-dir --upgrade pip uv wheel spotipy

# Create spotdl user and group
RUN groupadd -g $GID spotdl && \
    useradd -m -u $UID -g $GID spotdl

# Set workdir
WORKDIR /app

# Copy requirements files
COPY . .

# Install spotdl requirements
RUN uv sync --no-dev

# Fix permissions for the app dir
RUN chown -R spotdl:spotdl /app

# Pre-create the output directory so named volumes inherit writable ownership.
RUN mkdir -p /music && chown spotdl:spotdl /music

# Create a volume for the output directory
VOLUME /music

# Change Workdir to download location
WORKDIR /music

# Switch to non-root user
USER spotdl

# Download deno
RUN uv run --project /app --no-dev --frozen --no-sync spotdl --download-deno

# Entrypoint command
ENTRYPOINT ["uv", "run", "--project", "/app", "--no-dev", "--frozen", "--no-sync", "spotdl"]
