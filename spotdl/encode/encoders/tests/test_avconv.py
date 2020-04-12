from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import AvconvNotFoundError
from spotdl.encode.encoders import EncoderAvconv

import pytest


class TestEncoderAvconv:
    def test_subclass(self):
        assert issubclass(EncoderAvconv, EncoderBase)

    def test_avconv_not_found_error(self):
        with pytest.raises(AvconvNotFoundError):
            EncoderAvconv(encoder_path="/a/nonexistent/path")


class TestEncodingDefaults:
    def encode_command(input_file, target_file):
        command = [
            'avconv', '-y', '-loglevel', '0',
            '-i', input_file,
            '-ab', '192k',
            target_file,
        ]
        return command

    @pytest.mark.parametrize("files, expected_command", [
        (("test.m4a", "test.mp3"), encode_command("test.m4a", "test.mp3")),
        (("abc.m4a", "cba.opus"), encode_command("abc.m4a", "cba.opus")),
        (("bla bla.m4a", "ble ble.m4a"), encode_command("bla bla.m4a", "ble ble.m4a")),
        (("😛.m4a", "• tongue.flac"), encode_command("😛.m4a", "• tongue.flac")),
    ])
    def test_generate_encode_command(self, files, expected_command):
        encoder = EncoderAvconv()
        assert encoder._generate_encode_command(*files) == expected_command


class TestEncodingInDebugMode:
    def debug_encode_command(input_file, target_file):
        command = [
            'avconv', '-y', '-loglevel', 'debug',
            '-i', input_file,
            '-ab', '192k',
            target_file,
        ]
        return command

    @pytest.mark.parametrize("files, expected_command", [
        (("test.m4a", "test.mp3"), debug_encode_command("test.m4a", "test.mp3")),
        (("abc.m4a", "cba.opus"), debug_encode_command("abc.m4a", "cba.opus")),
        (("bla bla.m4a", "ble ble.m4a"), debug_encode_command("bla bla.m4a", "ble ble.m4a")),
        (("😛.m4a", "• tongue.flac"), debug_encode_command("😛.m4a", "• tongue.flac")),
    ])
    def test_generate_encode_command_with_debug(self, files, expected_command):
        encoder = EncoderAvconv()
        encoder.set_debuglog()
        assert encoder._generate_encode_command(*files) == expected_command

