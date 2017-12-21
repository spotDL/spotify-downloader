FROM python:3.6-alpine

RUN apk add --no-cache \
    ffmpeg

ADD requirements.txt /spotify-downloader/
RUN pip install -r /spotify-downloader/requirements.txt
RUN rm /spotify-downloader/requirements.txt

ADD spotdl.py /spotify-downloader/
ADD core/ /spotify-downloader/core

RUN mkdir /music
WORKDIR /music

ENTRYPOINT ["python3", "/spotify-downloader/spotdl.py", "-f", "/music"]
