FROM python:3-alpine

LABEL maintainer="xnetcat (Jakub)"

# Allow customizing the user/group IDs
# Default to 1000
ARG UID=1000
ARG GID=1000

# Install dependencies
RUN apk add --no-cache \
    ca-certificates \
    ffmpeg \
    openssl \
    aria2 \
    g++ \
    git \
    py3-cffi \
    libffi-dev \
    zlib-dev

# Install uv and update pip/wheel
RUN pip install --upgrade pip uv wheel spotipy

# Create spotdl user and group
RUN addgroup -g $GID spotdl && \
    adduser -D -u $UID -G spotdl spotdl

# Set workdir
WORKDIR /app

# Copy requirements files
COPY . .

# Install spotdl requirements
RUN uv sync

# Fix permissions for the app dir
RUN chown -R spotdl:spotdl /app

# Create a volume for the output directory
VOLUME /music

# Change Workdir to download location
WORKDIR /music

# Fix permissions for music directory
RUN chown spotdl:spotdl /music

# Switch to not root user
USER spotdl

# Entrypoint command
ENTRYPOINT ["uv", "run", "--project", "/app", "spotdl"]
