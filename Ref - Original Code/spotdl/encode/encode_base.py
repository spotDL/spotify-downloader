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
    "flac": "flac",
    "ogg": "ogg",
}


class EncoderBase(ABC):
    """
    Defined encoders must inherit from this abstract base class
    and implement their own functionality for the below defined
    methods.
    """

    @abstractmethod
    def __init__(self, encoder_path, must_exist, loglevel, additional_arguments=[]):
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
        Set any arbitrary arguments which are passed when the encoder
        is invoked.

        Parameters
        ----------
        argument: `str`
        """
        self._additional_arguments += argument.split()

    def get_encoding(self, path):
        """
        Determine the encoding for a local audio file from its file
        extnension. Whether is it an "mp3", "wav", "m4a", etc.

        Parameters
        ----------
        path: `str`
            Path to media file.

        Returns
        -------
        encoding: `str`
        """
        _, extension = os.path.splitext(path)
        # Ignore the initial dot from file extension
        encoding = extension[1:]
        return encoding

    @abstractmethod
    def set_debuglog(self):
        """
        Enable verbose logging on the encoder.
        """
        pass

    @abstractmethod
    def _generate_encode_command(self, input_path, target_path):
        """
        This method must generate the complete command for that would
        be used to invoke the encoder and perform the encoding.
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
    def re_encode(self, input_path, target_path, target_encoding=None, delete_original=False):
        """
        Re-encode a given input file to a specified output file.

        Parameters
        ----------
        input_path: `str`
            Path to media file that needs re-encoding.

        target_path: `str`
            Path to output media file.

        target_encoding: `str`, `None`
            It maybe "mp3", "opus", etc. If ``None``, it is
            determined from the file extension passed in
            ``target_path``.

        delete_original: `bool`
            Whether or not to delete the original media file.
        """
        pass

    def target_format_from_encoding(self, encoding):
        """
        Determines the target stream format from given input encoding
        for use with encoder.

        Parameters
        ----------
        encoding: `str`

        Returns
        -------
        target_format: `str`
            Target format which can be accepted by most mainstream encoders.
        """
        target_format = self._target_formats_from_encoding[encoding]
        return target_format

    def re_encode_from_stdin(self, input_encoding, target_path, target_encoding=None):
        """
        Read a file from STDIN and re-encode it to a specified output
        file.

        Parameters
        ----------
        input_encoding: `str`
            Path to media file that needs re-encoding.

        target_path: `str`
            Path to output media file.

        target_encoding: `str`, `None`
            It maybe "mp3", "opus", etc. If ``None``, it is
            determined from the file extension passed in
            ``target_path``.
        """
        raise NotImplementedError

