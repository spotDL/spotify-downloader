import shutil
import os

from abc import ABC
from abc import abstractmethod

from spotdl.encode.exceptions import EncoderNotFoundError

"""
  NOTE ON ENCODERS
  ================

* FFmeg encoders sorted in descending order based
  on the quality of audio produced:
  libopus > libvorbis >= libfdk_aac > aac > libmp3lame

* libfdk_aac encoder, due to copyrights needs to be compiled
  by end user on MacOS brew install ffmpeg --with-fdk-aac
  will do just that. Other OS? See:
  https://trac.ffmpeg.org/wiki/Encode/AAC

"""

_TARGET_FORMATS_FROM_ENCODING = {
    "m4a": "mp4",
    "mp3": "mp3",
    "opus": "opus",
    "flac": "flac"
}


class EncoderBase(ABC):
    """
    Defined encoders must inherit from this abstract base class
    and implement their own functionality for the below defined
    methods.
    """

    @abstractmethod
    def __init__(self, encoder_path, must_exist, loglevel, additional_arguments=[]):
        """
        This method must make sure whether specified encoder
        is available under PATH.
        """
        if must_exist and shutil.which(encoder_path) is None:
            raise EncoderNotFoundError(
                "{} executable does not exist or was not found in PATH.".format(
                    encoder_path
                )
            )
        self.encoder_path = encoder_path
        self._loglevel = loglevel
        self._additional_arguments = additional_arguments
        self._target_formats_from_encoding = _TARGET_FORMATS_FROM_ENCODING

    def set_argument(self, argument):
        """
        This method must be used to set any custom functionality
        for the encoder by passing arguments to it.
        """
        self._additional_arguments += argument.split()

    def get_encoding(self, path):
        """
        This method must determine the encoding for a local
        audio file. Such as "mp3", "wav", "m4a", etc.
        """
        _, extension = os.path.splitext(path)
        # Ignore the initial dot from file extension
        return extension[1:]

    @abstractmethod
    def set_debuglog(self):
        """
        This method must enable verbose logging in the defined
        encoder.
        """
        pass

    @abstractmethod
    def _generate_encode_command(self, input_path, target_path):
        """
        This method must the complete command for that would be
        used to invoke the encoder and perform the encoding.
        """
        pass

    @abstractmethod
    def _generate_encoding_arguments(self, input_encoding, target_encoding):
        """
        This method must return the core arguments for the defined
        encoder such as defining the sample rate, audio bitrate,
        etc.
        """
        pass

    @abstractmethod
    def re_encode(self, input_path, target_path):
        """
        This method must invoke the encoder to encode a given input
        file to a specified output file.
        """
        pass

    def target_format_from_encoding(self, encoding):
        """
        This method generates the target stream format from given
        input encoding.
        """
        target_format = self._target_formats_from_encoding[encoding]
        return target_format

    def re_encode_from_stdin(self, input_encoding, target_path):
        """
        This method must invoke the encoder to encode stdin to a
        specified output file.
        """
        raise NotImplementedError

