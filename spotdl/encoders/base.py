from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

import os

"""
  NOTE ON ENCODERS
  ================

* A comparision between FFmpeg, avconv, and libav:
  https://stackoverflow.com/questions/9477115

* FFmeg encoders sorted in descending order based
  on the quality of audio produced:
  libopus > libvorbis >= libfdk_aac > aac > libmp3lame

* libfdk_aac encoder, due to copyrights needs to be compiled
  by end user on MacOS brew install ffmpeg --with-fdk-aac
  will do just that. Other OS? See:
  https://trac.ffmpeg.org/wiki/Encode/AAC

"""

class EncoderBase(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, encoder_path, loglevel, additional_arguments):
        self.encoder_path = encoder_path
        self._loglevel = loglevel
        self._additional_arguments = additional_arguments

    @abstractmethod
    def set_argument(self, argument):
        self._additional_arguments += argument.split()

    @abstractmethod
    def get_encoding(self, filename):
        _, extension = os.path.splitext(filename)
        # Ignore the initial dot from file extension
        return extension[1:]

    @abstractmethod
    def set_debuglog(self):
        pass

    @abstractmethod
    def _generate_encode_command(self, input_file, output_file):
        pass

    @abstractmethod
    def _generate_encoding_arguments(self, input_encoding, output_encoding):
        pass

    @abstractmethod
    def re_encode(self, input_encoding, output_encoding):
        pass
