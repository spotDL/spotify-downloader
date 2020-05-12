from spotdl.encode.exceptions import EncoderNotFoundError
from spotdl.encode.exceptions import FFmpegNotFoundError


class TestEncoderNotFoundSubclass:
    def test_encoder_not_found_subclass(self):
        assert issubclass(FFmpegNotFoundError, Exception)

    def test_ffmpeg_not_found_subclass(self):
        assert issubclass(FFmpegNotFoundError, EncoderNotFoundError)

