import tqdm

import urllib.request
import subprocess
import sys

from spotdl.encode.encoders import EncoderFFmpeg
from spotdl.metadata.embedders import EmbedderDefault

import spotdl.util

CHUNK_SIZE = 16 * 1024

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

    def calculate_total_chunks(self, filesize):
        return (filesize // self._chunksize) + 1

    def make_progress_bar(self, total_chunks):
        progress_bar = tqdm.trange(
            total_chunks,
            unit_scale=(self._chunksize // 1024),
            unit="KiB",
            dynamic_ncols=True,
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}KiB '
                '[{elapsed}<{remaining}, {rate_fmt}{postfix}]',
        )
        return progress_bar

    def download_while_re_encoding(self, stream, target_path, target_encoding=None,
                                   encoder=EncoderFFmpeg(must_exist=False), show_progress=True):
        total_chunks = self.calculate_total_chunks(stream["filesize"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            target_path,
            target_encoding=target_encoding
        )
        response = stream["connection"]

        progress_bar = self.make_progress_bar(total_chunks)
        for _ in progress_bar:
            chunk = response.read(self._chunksize)
            process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def download(self, stream, target_path, show_progress=True):
        total_chunks = self.calculate_total_chunks(stream["filesize"])
        progress_bar = self.make_progress_bar(total_chunks)
        response = stream["connection"]

        def writer(response, progress_bar, file_io):
            for _ in progress_bar:
                chunk = response.read(self._chunksize)
                file_io.write(chunk)

        write_to_stdout = target_path == "-"
        if write_to_stdout:
            file_io = sys.stdout.buffer
            writer(response, progress_bar, file_io)
        else:
            with open(target_path, "wb") as file_io:
                writer(response, progress_bar, file_io)

    def re_encode(self, input_path, target_path, target_encoding=None,
                  encoder=EncoderFFmpeg(must_exist=False), show_progress=True):
        stream = self.metadata["streams"].getbest()
        total_chunks = self.calculate_total_chunks(stream["filesize"])
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

