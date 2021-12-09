FROM python:3-alpine

# Install ffmpeg and g++
RUN apk add --no-cache ffmpeg g++

# Create project directory
WORKDIR /app

# Add source code files to WORKDIR
ADD . .

# Upgrade pip
RUN python -m pip install --upgrade --no-cache-dir pip

# Install spotdl
RUN pip install --no-cache-dir .

# Create music directory
RUN mkdir /music
WORKDIR /music

# Entrypoint command
ENTRYPOINT [ "spotdl" ]
