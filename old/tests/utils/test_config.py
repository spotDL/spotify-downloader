import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from spotdl.utils.config import *


@pytest.fixture()
def setup(tmpdir, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda *_: tmpdir)
    data = SimpleNamespace()
    data.directory = tmpdir
    yield data


def test_get_spotdl_path(setup):
    """
    Tests that the spotdl path is created if it does not exist.
    """

    assert get_spotdl_path() == Path(setup.directory, ".spotdl")
    assert os.path.exists(os.path.join(setup.directory, ".spotdl"))


def test_get_config_path(setup):
    """
    Tests if the path to config file is correct.
    """

    assert get_config_file() == Path(setup.directory, ".spotdl", "config.json")


def test_get_cache_path(setup):
    """
    Tests if the path to the cache file is correct.
    """

    assert get_cache_path() == Path(setup.directory, ".spotdl", ".spotipy")


def test_get_temp_path(setup):
    """
    Tests if the path to the temp folder is correct.
    """

    assert get_temp_path() == Path(setup.directory, ".spotdl", "temp")


def test_get_config_not_created(setup):
    """
    Tests if exception is raised if config file does not exist.
    """

    with pytest.raises(ConfigError):
        get_config()
