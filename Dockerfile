FROM python:3.6-alpine

RUN apk add --no-cache \
    ffmpeg

ADD requirements.txt /app/
RUN cd /app && pip install -U -r requirements.txt

ADD spotdl.py /app/
ADD core/ /app/core

WORKDIR /app

ENTRYPOINT ["python3", "spotdl.py", "-f", "."]
