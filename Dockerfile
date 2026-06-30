FROM python:3.14-slim-bookworm

LABEL maintainer="Tzur Soffer"

# Allow customizing the user/group IDs
# Default to 1000
ARG UID=1000
ARG GID=1000

# Install uv from its official image (no pip install needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Deno is required by yt-dlp for some YouTube "made for kids" downloads
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

# Runtime dependencies. build-essential/libffi-dev are only needed to compile
# native wheels during `uv sync`, so we purge them in the same layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        openssl \
        aria2 \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create spotdl user and group
RUN groupadd -g "$GID" spotdl \
    && useradd -u "$UID" -g spotdl -m spotdl

# Set workdir
WORKDIR /app

# Copy ONLY what the build needs (nothing host-specific like .venv/config.json).
# Listing files explicitly keeps the build reproducible from a clean git clone.
COPY pyproject.toml uv.lock README.md ./
COPY spotdl/ ./spotdl/

# Install dependencies + project into /app/.venv, then drop the build toolchain
RUN uv sync --no-dev --frozen \
    && apt-get purge -y build-essential libffi-dev \
    && apt-get autoremove -y

# Put the venv on PATH so `spotdl` runs directly (no `uv run` needed)
ENV PATH="/app/.venv/bin:$PATH"

# Pre-create the music output dir AND the spotdl config dir, owned by spotdl.
# Pre-creating ~/.config/spotdl is important: it lets users bind-mount a single
# config.json file into it without Docker creating the parent dir as root
# (which would block spotdl from writing temp/, errors/, .spotipy at runtime).
RUN mkdir -p /music /home/spotdl/.config/spotdl \
    && chown -R spotdl:spotdl /app /music /home/spotdl

# Create a volume for the output directory
VOLUME /music

# Change Workdir to download location
WORKDIR /music

# Switch to non-root user
USER spotdl

# Entrypoint to run spotdl
ENTRYPOINT ["spotdl"]
