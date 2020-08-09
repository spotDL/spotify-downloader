import tqdm

import urllib.request
import subprocess
import sys

from spotdl.encode.encoders import EncoderFFmpeg
from spotdl.metadata.embedders import EmbedderDefault
from spotdl.metadata import BadMediaFileError

import spotdl.util

import logging
logger = logging.getLogger(__name__)

CHUNK_SIZE = 16 * 1024

class Track:
    """
    This class allows for various operations on provided track
    metadata.

    Parameters
    ----------
    metadata: `dict`
        Track metadata in standardized form.

    cache_albumart: `bool`
        Whether or not to cache albumart data by making network request
        to the given URL. This caching is done as soon as a
        :class:`Track` object is created.

    Examples
    --------
    + Downloading the audio track *"NCS - Spectre"* in opus format from
      YouTube while simultaneously encoding it to an mp3 format:

        >>> from spotdl.metadata_search import MetadataSearch
        >>> provider = MetadataSearch("ncs spectre")
        >>> metadata = provider.on_youtube()
        # The same metadata can also be retrived using `ProviderYouTube`:
        >>> # from spotdl.metadata.providers import ProviderYouTube
        >>> # provider = ProviderYouTube()
        >>> # metadata = provider.from_query("ncs spectre")
        # However, it is recommended to use `MetadataSearch` whenever
        # possible as it provides a higher level API.
        >>>
        >>> from spotdl.track import Track
        >>> track = Track(metadata)
        >>> stream = metadata["streams"].get(
        ...     quality="best",
        ...     preftype="opus",
        ... )
        >>>
        >>> import spotdl.metadata
        >>> filename = spotdl.metadata.format_string(
        ...     "{artist} - {track-name}.{output-ext}",
        ...     metadata,
        ...     output_extension="mp3",
        ... )
        >>>
        >>> filename
        'NoCopyrightSounds - Alan Walker - Spectre [NCS Release].mp3'
        >>> track.download_while_re_encoding(stream, filename)
    """

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
        """
        Determines the total number of chunks.

        Parameters
        ----------
        filesize: `int`
            Total size of file in bytes.

        Returns
        -------
        chunks: `int`
            Total number of chunks based on the file size and chunk
            size.
        """

        chunks = (filesize // self._chunksize) + 1
        return chunks

    def _make_progress_bar(self, iterations):
        """
        Creates a progress bar using :class:`tqdm`.

        Parameters
        ----------
        iterations: `int`
            Number of iterations to be performed.

        Returns
        -------
        progress_bar: :class:`tqdm.std.tqdm`
            An iterator object.
        """

        progress_bar = tqdm.trange(
            iterations,
            unit_scale=(self._chunksize // 1024),
            unit="KiB",
            dynamic_ncols=True,
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}KiB '
                '[{elapsed}<{remaining}, {rate_fmt}{postfix}]',
        )
        return progress_bar

    def download_while_re_encoding(self, stream, target_path, target_encoding=None,
                                   encoder=EncoderFFmpeg(must_exist=False), show_progress=True):
        """
        Downloads a stream while simuntaneously encoding it to a
        given target format.

        Parameters
        ----------
        stream: `dict`
            A `dict` containing stream information in the keys:
            `encoding`, `filesize`, `connection`.

        target_path: `str`
            Path to file to write the target stream to.

        target_encoding: `str`, `None`
            Specify a target encoding. If ``None``, the target encoding
            is automatically determined from the ``target_path``.

        encoder: :class:`spotdl.encode.EncoderBase` object
            A :class:`spotdl.encode.EncoderBase` object to use for encoding.

        show_progress: `bool`
            Whether or not to display a progress bar.
        """

        total_chunks = self._calculate_total_chunks(stream["filesize"])
        process = encoder.re_encode_from_stdin(
            stream["encoding"],
            target_path,
            target_encoding=target_encoding
        )
        response = stream["connection"]

        progress_bar = self._make_progress_bar(total_chunks)
        for _ in progress_bar:
            chunk = response.read(self._chunksize)
            process.stdin.write(chunk)

        process.stdin.close()
        process.wait()

    def download(self, stream, target_path, show_progress=True):
        """
        Downloads a stream.

        Parameters
        ----------
        stream: `dict`
            A `dict` containing stream information in the keys:
            `filesize`, `connection`.

        target_path: `str`
            Path to file to write the downloaded stream to.

        show_progress: `bool`
            Whether or not to display a progress bar.
        """

        total_chunks = self._calculate_total_chunks(stream["filesize"])
        progress_bar = self._make_progress_bar(total_chunks)
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
        """
        Encodes an already downloaded stream.

        Parameters
        ----------
        input_path: `str`
            Path to input file.

        target_path: `str`
            Path to target file.

        target_encoding: `str`
            Encoding to encode the input file to. If ``None``, the
            target encoding is determined from ``target_path``.

        encoder: :class:`spotdl.encode.EncoderBase` object
            A :class:`spotdl.encode.EncoderBase` object to use for encoding.

        show_progress: `bool`
            Whether or not to display a progress bar.
        """
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
        """
        Applies metadata on the audio file.

        Parameters
        ----------
        input_path: `str`
            Path to audio file to apply metadata to.

        encoding: `str`
            Encoding of the input audio file. If ``None``, the target
            encoding is determined from ``input_path``.

        embedder: :class:`spotdl.metadata.embedders.EmbedderDefault`
            An object of :class:`spotdl.metadata.embedders.EmbedderDefault`
            which depicts the metadata embedding strategy to use.
        """
        if self._cache_albumart:
            albumart = self._albumart_thread.join()
        else:
            albumart = None

        try:
            embedder.apply_metadata(
                input_path,
                self.metadata,
                cached_albumart=albumart,
                encoding=encoding,
            )
        except BadMediaFileError as e:
            msg = ("{} Such problems should be fixed "
                  "with FFmpeg set as the encoder.").format(e.args[0])
            logger.warning(msg)

