import pytest

from spotdl.utils.arguments import parse_arguments


def test_parse_arguments():
    with pytest.raises(SystemExit):
        vars(parse_arguments())
