from spotdl.encode import EncoderBase
from spotdl.encode.exceptions import FFmpegNotFoundError
from spotdl.encode.encoders import EncoderFFmpeg

import pytest


class TestEncoderFFmpeg:
    def test_subclass(self):
        assert issubclass(EncoderFFmpeg, EncoderBase)

    def test_ffmpeg_not_found_error(self):
        with pytest.raises(FFmpegNotFoundError):
            EncoderFFmpeg(encoder_path="/a/nonexistent/path")


class TestEncodingDefaults:
    def m4a_to_mp3_encoder(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:v', 'copy',
            '-codec:a', 'libmp3lame',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_webm_encoder(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:a', 'libopus',
            '-vbr', 'on',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_m4a_encoder(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-acodec', 'copy',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_flac_encoder(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:a', 'flac',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    @pytest.mark.parametrize("files, expected_command", [
        (("test.m4a", "test.mp3"), m4a_to_mp3_encoder("test.m4a", "test.mp3")),
        (("abc.m4a", "cba.webm"), m4a_to_webm_encoder("abc.m4a", "cba.webm")),
        (("bla bla.m4a", "ble ble.m4a"), m4a_to_m4a_encoder("bla bla.m4a", "ble ble.m4a")),
        (("😛.m4a", "• tongue.flac"), m4a_to_flac_encoder("😛.m4a", "• tongue.flac")),
    ])
    def test_generate_encode_command(self, files, expected_command):
        encoder = EncoderFFmpeg()
        assert encoder._generate_encode_command(*files) == expected_command


class TestEncodingInDebugMode:
    def m4a_to_mp3_encoder_with_debug(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-loglevel', 'debug',
            '-i', input_file,
            '-codec:v', 'copy',
            '-codec:a', 'libmp3lame',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_webm_encoder_with_debug(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-loglevel', 'debug',
            '-i', input_file,
            '-codec:a', 'libopus',
            '-vbr', 'on',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_m4a_encoder_with_debug(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-loglevel', 'debug',
            '-i', input_file,
            '-acodec', 'copy',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    def m4a_to_flac_encoder_with_debug(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-loglevel', 'debug',
            '-i', input_file,
            '-codec:a', 'flac',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn', output_file
        ]
        return command

    @pytest.mark.parametrize("files, expected_command", [
        (("test.m4a", "test.mp3"), m4a_to_mp3_encoder_with_debug("test.m4a", "test.mp3")),
        (("abc.m4a", "cba.webm"), m4a_to_webm_encoder_with_debug("abc.m4a", "cba.webm")),
        (("bla bla.m4a", "ble ble.m4a"), m4a_to_m4a_encoder_with_debug("bla bla.m4a", "ble ble.m4a")),
        (("😛.m4a", "• tongue.flac"), m4a_to_flac_encoder_with_debug("😛.m4a", "• tongue.flac")),
    ])
    def test_generate_encode_command_with_debug(self, files, expected_command):
        encoder = EncoderFFmpeg()
        encoder.set_debuglog()
        assert encoder._generate_encode_command(*files) == expected_command


class TestEncodingAndTrimSilence:
    def m4a_to_mp3_encoder_and_trim_silence(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:v', 'copy',
            '-codec:a', 'libmp3lame',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn',
            '-af', 'silenceremove=start_periods=1',
            output_file
        ]
        return command

    def m4a_to_webm_encoder_and_trim_silence(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:a', 'libopus',
            '-vbr', 'on',
            '-b:a', '192k',
            '-vn',
            '-af', 'silenceremove=start_periods=1',
            output_file
        ]
        return command

    def m4a_to_m4a_encoder_and_trim_silence(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-acodec', 'copy',
            '-b:a', '192k',
            '-vn',
            '-af', 'silenceremove=start_periods=1',
            output_file
        ]
        return command

    def m4a_to_flac_encoder_and_trim_silence(input_file, output_file):
        command = [
            'ffmpeg', '-y', '-nostdin', '-hide_banner', '-nostats', '-v', 'panic',
            '-i', input_file,
            '-codec:a', 'flac',
            '-ar', '48000',
            '-b:a', '192k',
            '-vn',
            '-af', 'silenceremove=start_periods=1',
            output_file
        ]
        return command

    @pytest.mark.parametrize("files, expected_command", [
        (("test.m4a", "test.mp3"), m4a_to_mp3_encoder_and_trim_silence("test.m4a", "test.mp3")),
        (("abc.m4a", "cba.webm"), m4a_to_webm_encoder_and_trim_silence("abc.m4a", "cba.webm")),
        (("bla bla.m4a", "ble ble.m4a"), m4a_to_m4a_encoder_and_trim_silence("bla bla.m4a", "ble ble.m4a")),
        (("😛.m4a", "• tongue.flac"), m4a_to_flac_encoder_and_trim_silence("😛.m4a", "• tongue.flac")),
    ])
    def test_generate_encode_command_and_trim_silence(self, files, expected_command):
        encoder = EncoderFFmpeg()
        encoder.set_trim_silence()
        assert encoder._generate_encode_command(*files) == expected_command
