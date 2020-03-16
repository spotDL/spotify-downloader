import subprocess
import os
from logzero import logger as log
from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import EncoderNotFoundError
from spotdl.encode.exceptions import AvconvNotFoundError

class EncoderAvconv(EncoderBase):
    def __init__(self, encoder_path="avconv"):
        print("Using EncoderAvconv is deprecated and will be removed"
              "in future versions. Use EncoderFFmpeg instead.")
        encoder_path = encoder_path
        _loglevel = "-loglevel 0"
        _additional_arguments = ["-ab", "192k"]

        try:
            super().__init__(encoder_path, _loglevel, _additional_arguments)
        except EncoderNotFoundError as e:
            raise AvconvNotFoundError(e.args[0])

    def set_argument(self, argument):
        super().set_argument(argument)

    def get_encoding(self, filename):
        return super().get_encoding(filename)

    def _generate_encoding_arguments(self, input_encoding, output_encoding):
        initial_arguments = self._rules.get(input_encoding)
        if initial_arguments is None:
            raise TypeError(
                'The input format ("{}") is not supported.'.format(
                input_extension,
            )
        )

        arguments = initial_arguments.get(output_encoding)
        if arguments is None:
            raise TypeError(
                'The output format ("{}") is not supported.'.format(
                output_extension,
            )
        )

        return arguments

    def _generate_encoding_arguments(self, input_encoding, output_encoding):
        return ""

    def set_debuglog(self):
        self._loglevel = "-loglevel debug"

    def _generate_encode_command(self, input_file, output_file):
        input_encoding = self.get_encoding(input_file)
        output_encoding = self.get_encoding(output_file)

        arguments = self._generate_encoding_arguments(
            input_encoding,
            output_encoding
        )

        command = [self.encoder_path] \
            + ["-y"] \
            + self._loglevel.split() \
            + ["-i", input_file] \
            + self._additional_arguments \
            + [output_file]

        return command

    def re_encode(self, input_file, output_file, delete_original=False):
        encode_command = self._generate_encode_command(
            input_file,
            output_file
        )

        returncode = subprocess.call(encode_command)
        encode_successful = returncode == 0

        if encode_successful and delete_original:
            os.remove(input_file)

        return returncode
