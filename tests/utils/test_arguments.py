import pytest

from spotdl.utils.arguments import parse_arguments, DEFAULT_CONFIG


def test_parse_arguments():
    with pytest.raises(SystemExit):
        vars(parse_arguments())
