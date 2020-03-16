from spotdl.encode import EncoderBase

import pytest

def test_abstract_base_class_encoderbase():
    encoder_path = "ffmpeg"
    _loglevel = "-hide_banner -nostats -v panic"
    _additional_arguments = ["-b:a", "192k", "-vn"]

    with pytest.raises(TypeError):
        # This abstract base class must be inherited from
        # for instantiation
        EncoderBase(encoder_path, _loglevel, _additional_arguments)
