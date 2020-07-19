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
        parser = spotdl.command_line.arguments.get_arguments()
        args = parser.parse_args().__dict__
        argument_handler = spotdl.command_line.arguments.ArgumentHandler(args)
        with pytest.raises(ArgumentError):
            argument_handler.run_errands()
        sys.argv[1:] = previous_argv[1:]

    def test_write_to_error(self):
        previous_argv = sys.argv
        sys.argv[1:] = ["-s", "sekai all i had", "--write-to", "output.txt"]
        parser = spotdl.command_line.arguments.get_arguments()
        args = parser.parse_args().__dict__
        argument_handler = spotdl.command_line.arguments.ArgumentHandler(args)
        with pytest.raises(ArgumentError):
            argument_handler.run_errands()
        sys.argv[1:] = previous_argv[1:]


class TestArguments:
    def test_general_arguments(self):
        previous_argv = sys.argv
        sys.argv[1:] = ["-s", "elena coats - one last song"]
        parser = spotdl.command_line.arguments.get_arguments()
        args = parser.parse_args().__dict__

        expect_args = {
            'song': ['elena coats - one last song'],
            'list': None,
            'playlist': None,
            'album': None,
            'all_albums': None,
            'username': None,
            'write_m3u': False,
            'manual': False,
            'no_metadata': False,
            'no_encode': False,
            'overwrite': 'prompt',
            'quality': 'automatic',
            'input_ext': 'automatic',
            'output_ext': 'mp3',
            'write_to': None,
            'output_file': '{artist} - {track-name}.{output-ext}',
            'trim_silence': False,
            'search_format': '{artist} - {track-name} lyrics',
            'dry_run': False,
            'processor': 'synchronous',
            'no_spaces': False,
            'skip_file': None,
            'write_successful_file': None,
            'spotify_client_id': '4fe3fecfe5334023a1472516cc99d805',
            'spotify_client_secret': '0f02b7c483c04257984695007a4a8d5c',
            'log_level': 'INFO',
            'remove_config': False
        }

        assert args == expect_args

    def test_grouped_arguments(self):
        previous_argv = sys.argv
        sys.argv[1:] = []
        parser = spotdl.command_line.arguments.get_arguments()
        with pytest.raises(SystemExit):
            parser.parse_args()
        sys.argv[1:] = previous_argv[1:]

