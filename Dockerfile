FROM python:3.9-alpine

RUN apk add --no-cache ffmpeg g++
RUN python -m pip install --upgrade --no-cache-dir pip wheel

WORKDIR /spotdl
ADD . .

RUN pip install -e --no-cache-dir .

RUN mkdir /music
WORKDIR /music

ENTRYPOINT ["spotdl"]
