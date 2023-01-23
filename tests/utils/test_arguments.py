import pytest

from spotdl.utils.arguments import parse_arguments


def test_parse_arguments():
    vars(parse_arguments())
