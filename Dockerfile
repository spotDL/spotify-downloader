FROM python:3-alpine

# Install ffmpeg and g++
RUN apk add --no-cache ffmpeg g++ git

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

# Create a volume for the output directory
VOLUME /music

# Change CWD to /music
WORKDIR /music

# Entrypoint command
ENTRYPOINT [ "spotdl" ]
