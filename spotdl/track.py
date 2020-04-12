import tqdm

import urllib.request
import subprocess

from spotdl.encode.encoders import EncoderFFmpeg
from spotdl.metadata.embedders import EmbedderDefault

import spotdl.util

CHUNK_SIZE= 16 * 1024

class Track:
    def __init__(self, metadata, cache_albumart=False):
        self.metadata = metadata
        self._chunksize = CHUNK_SIZE

        if cache_albumart:
            self._albumart_thread = self._cache_albumart()

        self._cache_albumart = cache_albumart

    def _cache_albumart(self):
        albumart_thread = spotdl.util.ThreadWithReturnValue(
            target=lambda url: urllib.request.urlopen(url).read(),
            args=(self.metadata["album"]["images"][0]["url"],)
        )
        albumart_thread.start()
        return albumart_thread

    def _calculate_total_chunks(self, filesize):
        return (filesize // self._chunksize) + 1

    def download_while_re_encoding(self, stream, target_path, target_encoding=None,
                                   encoder=EncoderFFmpeg(), show_progress=True):
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            target_path,
            target_encoding=target_encoding
        )
        response = stream["connection"]
        for _ in tqdm.trange(total_chunks):
            chunk = response.read(self._chunksize)
            process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def download(self, stream, target_path, show_progress=True):
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        response = stream["connection"]
        with open(target_path, "wb") as fout:
            for _ in tqdm.trange(total_chunks):
                chunk = response.read(self._chunksize)
                fout.write(chunk)

    def re_encode(self, input_path, target_path, target_encoding=None,
                  encoder=EncoderFFmpeg(), show_progress=True):
        stream = self.metadata["streams"].getbest()
        total_chunks = self._calculate_total_chunks(stream["filesize"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            target_path,
            target_encoding=target_encoding
        )
        with open(input_path, "rb") as fin:
            for _ in tqdm.trange(total_chunks):
                chunk = fin.read(self._chunksize)
                process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def apply_metadata(self, input_path, encoding=None, embedder=EmbedderDefault()):
        if self._cache_albumart:
            albumart = self._albumart_thread.join()
        else:
            albumart = None

        embedder.apply_metadata(
            input_path,
            self.metadata,
            cached_albumart=albumart,
            encoding=encoding,
        )

