import tqdm

import subprocess
import urllib.request

from spotdl.encode.encoders import EncoderFFmpeg

CHUNK_SIZE= 16 * 1024
HEADERS = [('Range', 'bytes=0-'),]

class Track:
    def __init__(self, metadata):
        self.metadata = metadata
        self.network_headers = HEADERS
        self._chunksize = CHUNK_SIZE

    def _make_request(self, url):
        request = urllib.request.Request(url)
        for header in self.network_headers:
            request.add_header(*header)
        return urllib.request.urlopen(request)

    def _calculate_total_chunks(self, filesize):
        return (filesize // self._chunksize) + 1

    def download_while_re_encoding(self, path, encoder=EncoderFFmpeg(), show_progress=True):
        stream = self.metadata["streams"].getbest()
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        response = self._make_request(stream["download_url"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            path
        )
        for _ in tqdm.trange(total_chunks):
            chunk = response.read(self._chunksize)
            process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def download(self, path, show_progress=True):
        stream = self.metadata["streams"].getbest()
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        response = self._make_request(stream["download_url"])
        with open(path, "wb") as fout:
            for _ in tqdm.trange(total_chunks):
                chunk = response.read(self._chunksize)
                fout.write(chunk)

    def re_encode(self, input_path, target_path, encoder=EncoderFFmpeg(), show_progress=True):
        stream = self.metadata["streams"].getbest()
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            target_path
        )
        with open(input_path, "rb") as fin:
            for _ in tqdm.trange(total_chunks):
                chunk = fin.read(self._chunksize)
                process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def apply_metadata(path):
        pass
