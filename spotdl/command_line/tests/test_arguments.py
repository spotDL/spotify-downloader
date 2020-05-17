import spotdl.command_line.arguments
from spotdl.command_line.exceptions import ArgumentError

import logging
import sys
import pytest


def test_logging_levels():
    expect_logging_levels = {
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "DEBUG": logging.DEBUG,
        "ERROR": logging.ERROR,
    }
    assert spotdl.command_line.arguments._LOG_LEVELS == expect_logging_levels


class TestBadArguments:
    def test_error_m3u_without_list(self):
        previous_argv = sys.argv
        sys.argv[1:] = ["-s", "cool song", "--write-m3u"]
        argument_handler = spotdl.command_line.arguments.get_arguments()
        with pytest.raises(ArgumentError):
            argument_handler.run_errands()
        sys.argv[1:] = previous_argv[1:]

    def test_write_to_error(self):
        previous_argv = sys.argv
        sys.argv[1:] = ["-s", "sekai all i had", "--write-to", "output.txt"]
        argument_handler = spotdl.command_line.arguments.get_arguments()
        with pytest.raises(ArgumentError):
            argument_handler.run_errands()
        sys.argv[1:] = previous_argv[1:]


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
        previous_argv = sys.argv
        sys.argv[1:] = []
        with pytest.raises(SystemExit):
            argument_handler = spotdl.command_line.arguments.get_arguments()
        sys.argv[1:] = previous_argv[1:]

