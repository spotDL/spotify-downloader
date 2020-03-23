import subprocess
import threading


def download(url, path=".", progress_bar=True, ):
    command = ("ffmpeg", "-y", "-i", "-", "output.wav")

    content = pytube.YouTube("https://www.youtube.com/watch?v=SE0nYFJ0ZvQ")
    stream = content.streams[0]
    response = urllib.request.urlopen(stream.url)

    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    while True:
        chunk = response.read(16 * 1024)
        if not chunk:
            break
        process.stdin.write(chunk)

    process.stdin.close()
