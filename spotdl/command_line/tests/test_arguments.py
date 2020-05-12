import spotdl.command_line.arguments

import sys
import pytest


def test_log_str_to_int():
    expect_levels = [20, 30, 40, 10]
    levels = [spotdl.command_line.arguments.log_leveller(level)
              for level in spotdl.command_line.arguments._LOG_LEVELS_STR]
    assert levels == expect_levels


class TestBadArguments:
    def test_error_m3u_without_list(self):
        with pytest.raises(SystemExit):
            spotdl.command_line.arguments.get_arguments(argv=("-t cool song", "--write-m3u"))

    def test_write_to_error(self):
        with pytest.raises(SystemExit):
            spotdl.command_line.arguments.get_arguments(argv=("-t", "sekai all i had", "--write-to", "output.txt"))


class TestArguments:
    @pytest.mark.xfail
    def test_general_arguments(self):
        arguments = spotdl.command_line.arguments.get_arguments(argv=("-t", "elena coats - one last song"))
        arguments = arguments.__dict__

        assert isinstance(arguments["spotify_client_id"], str)
        assert isinstance(arguments["spotify_client_secret"], str)

        arguments["spotify_client_id"] = None
        arguments["spotify_client_secret"] = None

        expect_arguments = {
            "song": ["elena coats - one last song"],
            "song": None,
            "list": None,
            "playlist": None,
            "album": None,
            "all_albums": None,
            "username": None,
            "write_m3u": False,
            "manual": False,
            "no_remove_original": False,
            "no_metadata": False,
            "no_fallback_metadata": False,
            "directory": "/home/ritiek/Music",
            "overwrite": "prompt",
            "input_ext": ".m4a",
            "output_ext": ".mp3",
            "write_to": None,
            "file_format": "{artist} - {track_name}",
            "trim_silence": False,
            "search_format": "{artist} - {track_name} lyrics",
            "download_only_metadata": False,
            "dry_run": False,
            "music_videos_only": False,
            "no_spaces": False,
            "log_level": 20,
            "skip": None,
            "write_successful": None,
            "spotify_client_id": None,
            "spotify_client_secret": None,
            "config": None
        }

        assert arguments == expect_arguments

    def test_grouped_arguments(self):
        with pytest.raises(SystemExit):
            spotdl.command_line.arguments.get_arguments()

