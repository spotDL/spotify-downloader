FROM python:3-alpine

# Install ffmpeg and g++
RUN apk add --no-cache ffmpeg g++

# Create project directory
WORKDIR /app/spotdl

# Add source code files to WORKDIR
ADD . .

# Upgrade pip
RUN python -m pip install --upgrade --no-cache-dir pip

# Install spotdl
RUN pip install --no-cache-dir .

# Create data directory
RUN mkdir -p /data/spotdl
WORKDIR /data/spotdl

# Environment variables
ENV SPOTDL_SONG="" SPOTDL_OUTPUT_FORMAT="mp3"

# Container start command
CMD spotdl $SPOTDL_SONG --output-format $SPOTDL_OUTPUT_FORMAT --m3u
