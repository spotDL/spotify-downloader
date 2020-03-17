from spotdl.encode.exceptions import EncoderNotFoundError
from spotdl.encode.exceptions import FFmpegNotFoundError
from spotdl.encode.exceptions import AvconvNotFoundError

import pytest


class TestEncoderNotFoundSubclass:
    def test_encoder_not_found_subclass(self):
        assert issubclass(FFmpegNotFoundError, Exception)

    def test_ffmpeg_not_found_subclass(self):
        assert issubclass(FFmpegNotFoundError, EncoderNotFoundError)

    def test_avconv_not_found_subclass(self):
        assert issubclass(AvconvNotFoundError, EncoderNotFoundError)

