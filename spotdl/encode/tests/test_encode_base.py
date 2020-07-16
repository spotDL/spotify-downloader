from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import EncoderNotFoundError

import pytest

class TestAbstractBaseClass:
    def test_error_abstract_base_class_encoderbase(self):
        encoder_path = "ffmpeg"
        _loglevel = "-hide_banner -nostats -v panic"
        _additional_arguments = ["-vn"]

        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            EncoderBase(encoder_path, _loglevel, _additional_arguments)


    def test_inherit_abstract_base_class_encoderbase(self):
        class EncoderKid(EncoderBase):
            def __init__(self, encoder_path, _loglevel, _additional_arguments):
                super().__init__(encoder_path, _loglevel, _additional_arguments)

            def _generate_encode_command(self):
                pass

            def _generate_encoding_arguments(self):
                pass

            def re_encode(self):
                pass

            def set_debuglog(self):
                pass


        encoder_path = "ffmpeg"
        _loglevel = "-hide_banner -nostats -v panic"
        _additional_arguments = ["-vn"]

        EncoderKid(encoder_path, _loglevel, _additional_arguments)


class TestMethods:
    class EncoderKid(EncoderBase):
        def __init__(self, encoder_path, _loglevel, _additional_arguments):
            super().__init__(encoder_path, _loglevel, _additional_arguments)

        def _generate_encode_command(self, input_path, target_path, quality):
            pass

        def _generate_encoding_arguments(self, input_encoding, target_encoding, quality):
            pass

        def re_encode(self, input_encoding, target_encoding, quality):
            pass

        def set_debuglog(self):
            pass


    @pytest.fixture(scope="module")
    def encoderkid(self):
        encoder_path = "ffmpeg"
        _loglevel = "-hide_banner -nostats -v panic"
        _additional_arguments = []

        encoderkid = self.EncoderKid(encoder_path, _loglevel, _additional_arguments)
        return encoderkid

    def test_set_argument(self, encoderkid):
        encoderkid.set_argument("-parameter argument")
        assert encoderkid._additional_arguments == [
            "-parameter",
            "argument",
        ]

    @pytest.mark.parametrize("filename, encoding", [
        ("example.m4a", "m4a"),
        ("exampley.mp3", "mp3"),
        ("flakey.flac", "flac"),
        ("example.oga", "oga"),
        ("test 123.ogg", "ogg"),
    ])
    def test_get_encoding(self, encoderkid, filename, encoding):
        assert encoderkid.get_encoding(filename) == encoding

    def test_encoder_not_found_error(self):
        with pytest.raises(EncoderNotFoundError):
            self.EncoderKid("/a/nonexistent/path", "0", [])

    @pytest.mark.parametrize("encoding, target_format", [
        ("m4a", "mp4"),
        ("mp3", "mp3"),
        ("flac", "flac"),
        ("oga", "oga"),
        ("ogg", "ogg"),
    ])
    def test_target_format_from_encoding(self, encoderkid, encoding, target_format):
        assert encoderkid.target_format_from_encoding(encoding) == target_format
