import re

import pytest

from spotdl.__main__ import __version__, console_entry_point


def test_check_version():
    """
    The version should be a string of numbers separated by dots
    """

    assert re.match(r"\d{1,2}\.\d{1,2}\.\d{1,3}", __version__) is not None
