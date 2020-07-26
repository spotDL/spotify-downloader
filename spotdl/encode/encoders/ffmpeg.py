import subprocess
import os

from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import EncoderNotFoundError
from spotdl.encode.exceptions import FFmpegNotFoundError

import logging
logger = logging.getLogger(__name__)


# Key: from format
# Subkey: to format
RULES = {
    "m4a": {
        "mp3": "-codec:v copy -codec:a libmp3lame -q:a",
        "m4a": "-acodec copy -b:a",
        "flac": "-codec:a flac -compression_level",
        "oga": "-codec:a libvorbis -q:a",
        "ogg": "-codec:a libopus -b:a",
        "opus": "-codec:a libopus -b:a",
    },
    "opus": {
        "mp3": "-codec:a libmp3lame -q:a",
        "m4a": "-cutoff 20000 -codec:a aac -b:a",
        "flac": "-codec:a flac -compression_level",
        "oga": "-codec:a libvorbis -q:a",
        "ogg": "-acodec copy -b:a",
        "opus": "-acodec copy -b:a",
    },
}
QARGS = {
    "mp3": ["0", "1", "2", "4", "5", "6"],
    "m4a": ["256k", "224k", "192k", "160k", "128k", "96k"],
    "flac": ["0", "3", "5", "7", "10", "12"],
    "oga": ["7", "6", "5", "4", "2", "0"],
    "ogg": ["192k", "160k", "128k", "96k", "80k", "64k"],
    "opus": ["192k", "160k", "128k", "96k", "80k", "64k"],
}


class EncoderFFmpeg(EncoderBase):
    """
    A class for encoding media files using FFmpeg.

    Parameters
    ----------
    encoder_path: `str`
        Path to FFmpeg.

    must_exist: `bool`
        Error out immediately if the encoder isn't found in
        ``encoder_path``.

    Examples
    --------
    + Re-encode an OPUS stream from STDIN to an MP3:

        >>> import os
        >>> input_path = "audio.opus"
        >>> target_path = "audio.mp3"
        >>> input_path_size = os.path.getsize(input_path)
        >>>
        >>> from spotdl.encode.encoders import EncoderFFmpeg
        >>> ffmpeg = EncoderFFmpeg()
        >>> process = ffmpeg.re_encode_from_stdin(
        ...     input_encoding="opus",
        ...     target_path=target_path
        ... )
        >>>
        >>> chunk_size = 4096
        >>> total_chunks = (input_path_size // chunk_size) + 1
        >>>
        >>> with open(input_path, "rb") as fin:
        ...     for chunk_number in range(1, total_chunks+1):
        ...         chunk = fin.read(chunk_size)
        ...         process.stdin.write(chunk)
        ...         print("chunks encoded: {}/{}".format(
        ...             chunk_number,
        ...             total_chunks,
        ...         ))
        >>>
        >>> process.stdin.close()
        >>> process.wait()
    """

    def __init__(self, encoder_path="ffmpeg", must_exist=True):
        _loglevel = "-hide_banner -nostats -v warning"
        _additional_arguments = ["-vn"]
        try:
            super().__init__(encoder_path, must_exist, _loglevel, _additional_arguments)
        except EncoderNotFoundError as e:
            raise FFmpegNotFoundError(e.args[0])
        self._rules = RULES
        self._qargs = QARGS
        self._defualt_quality = 3

    def set_trim_silence(self):
        self.set_argument("-af silenceremove=start_periods=1")

    def get_encoding(self, path):
        return super().get_encoding(path)

    def _generate_encoding_arguments(self, input_encoding, target_encoding, quality):
        initial_arguments = self._rules.get(input_encoding)
        if initial_arguments is None:
            raise TypeError(
                'The input format ("{}") is not supported.'.format(
                input_encoding,
            ))
        arguments = initial_arguments.get(target_encoding) + " " + self._qargs.get(target_encoding)[int(quality)-1]
        if arguments is None:
            raise TypeError(
                'The output format ("{}") is not supported.'.format(
                target_encoding,
            ))
        return arguments

    def set_debuglog(self):
        self._loglevel = "-loglevel debug"

    def _generate_encode_command(self, input_path, target_path,
                                 input_encoding=None, target_encoding=None, quality=None):
        if input_encoding is None:
            input_encoding = self.get_encoding(input_path)
        if target_encoding is None:
            target_encoding = self.get_encoding(target_path)
        if quality is None or quality == "automatic":
            quality = self._defualt_quality

        arguments = self._generate_encoding_arguments(
            input_encoding,
            target_encoding,
            quality=quality
        )
        command = [self.encoder_path] \
            + ["-y", "-nostdin"] \
            + self._loglevel.split() \
            + ["-i", input_path] \
            + arguments.split() \
            + self._additional_arguments \
            + ["-f", self.target_format_from_encoding(target_encoding)] \
            + [target_path]

        return command

    def re_encode(self, input_path, target_path, target_encoding=None, quality=None, delete_original=False):
        encode_command = self._generate_encode_command(
            input_path,
            target_path,
            target_encoding=target_encoding,
            quality=quality
        )
        logger.debug("Calling FFmpeg with:\n{command}".format(
            command=encode_command,
        ))
        process = subprocess.Popen(encode_command)
        process.wait()
        encode_successful = process.returncode == 0
        if encode_successful and delete_original:
            os.remove(input_path)
        return process

    def re_encode_from_stdin(self, input_encoding, target_path, target_encoding=None, quality=None):
        encode_command = self._generate_encode_command(
            "-",
            target_path,
            input_encoding=input_encoding,
            target_encoding=target_encoding,
            quality=quality
        )
        logger.debug("Calling FFmpeg with:\n{command}".format(
            command=encode_command,
        ))
        process = subprocess.Popen(encode_command, stdin=subprocess.PIPE)
        return process

    def set_default_quality(self, stream):
        bitrates = [160, 128, 70, 50]
        self._defualt_quality += bitrates.index(stream["bitrate"])

