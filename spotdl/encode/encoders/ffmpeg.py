import subprocess
import os
from logzero import logger as log

from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import EncoderNotFoundError
from spotdl.encode.exceptions import FFmpegNotFoundError

RULES = {
    "m4a": {
        "mp3": "-codec:v copy -codec:a libmp3lame -ar 48000",
        "webm": "-codec:a libopus -vbr on",
        "m4a": "-acodec copy",
        "flac": "-codec:a flac -ar 48000",
    },
    "opus": {
        "mp3": "-codec:a libmp3lame -ar 48000",
        "m4a": "-cutoff 20000 -codec:a aac -ar 48000",
        "flac": "-codec:a flac -ar 48000",
    },
}


class EncoderFFmpeg(EncoderBase):
    def __init__(self, encoder_path="ffmpeg"):
        _loglevel = "-hide_banner -nostats -v panic"
        _additional_arguments = ["-b:a", "192k", "-vn"]
        try:
            super().__init__(encoder_path, _loglevel, _additional_arguments)
        except EncoderNotFoundError as e:
            raise FFmpegNotFoundError(e.args[0])
        self._rules = RULES

    def set_argument(self, argument):
        super().set_argument(argument)

    def set_trim_silence(self):
        self.set_argument("-af silenceremove=start_periods=1")

    def get_encoding(self, filename):
        return super().get_encoding(filename)

    def _generate_encoding_arguments(self, input_encoding, output_encoding):
        initial_arguments = self._rules.get(input_encoding)
        if initial_arguments is None:
            raise TypeError(
                'The input format ("{}") is not supported.'.format(
                input_encoding,
            )
        )
        arguments = initial_arguments.get(output_encoding)
        if arguments is None:
            raise TypeError(
                'The output format ("{}") is not supported.'.format(
                output_encoding,
            )
        )
        return arguments

    def set_debuglog(self):
        self._loglevel = "-loglevel debug"

    def _generate_encode_command(self, input_file, output_file,
                                 input_encoding=None, output_encoding=None):
        if input_encoding is None:
            input_encoding = self.get_encoding(input_file)
        if output_encoding is None:
            output_encoding = self.get_encoding(output_file)
        arguments = self._generate_encoding_arguments(
            input_encoding,
            output_encoding
        )
        command = [self.encoder_path] \
            + ["-y", "-nostdin"] \
            + self._loglevel.split() \
            + ["-i", input_file] \
            + arguments.split() \
            + self._additional_arguments \
            + [output_file]

        return command

    def re_encode(self, input_file, output_file, delete_original=False):
        encode_command = self._generate_encode_command(
            input_file,
            output_file
        )
        process = subprocess.Popen(encode_command)
        process.wait()
        encode_successful = process.returncode == 0
        if encode_successful and delete_original:
            os.remove(input_file)
        return process

    def re_encode_from_stdin(self, input_encoding, output_file):
        output_encoding = self.get_encoding(output_file)
        encode_command = self._generate_encode_command(
            "-",
            output_file,
            input_encoding=input_encoding,
        )
        process = subprocess.Popen(encode_command, stdin=subprocess.PIPE)
        return process

