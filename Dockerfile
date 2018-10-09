FROM python:3.6-alpine

RUN apk add --no-cache \
    ffmpeg

ADD spotdl/ /spotify-downloader/spotdl
ADD setup.py /spotify-downloader/setup.py
ADD README.md /spotify-downloader/README.md

WORKDIR /spotify-downloader
RUN pip install .

RUN mkdir /music
WORKDIR /music

ENTRYPOINT ["spotdl", "-f", "/music"]
