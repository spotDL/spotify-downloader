FROM python:3.6-alpine

RUN apk add --no-cache \
    ffmpeg

ADD requirements.txt /spotify-downloader/
RUN cd /spotify-downloader && pip install -U -r requirements.txt

ADD spotdl.py /spotify-downloader/
ADD core/ /spotify-downloader/core

ENTRYPOINT ["python3", "/spotify-downloader/spotdl.py", "-f", "/spotify-downloader"]
