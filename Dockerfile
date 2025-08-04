FROM python:3-alpine

LABEL maintainer="xnetcat (Jakub)"

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

# Set workdir
WORKDIR /app

# Copy requirements files
COPY . .

# Install spotdl requirements
RUN uv sync

# Create music directory
RUN mkdir /music

# Create a volume for the output directory
VOLUME /music

# Entrypoint command
ENTRYPOINT ["uv", "run", "spotdl"]
