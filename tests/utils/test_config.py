from spotdl.utils.config import *
from types import SimpleNamespace
from pathlib import Path

import pytest
import os


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda *_: tmp_path)
    data = SimpleNamespace()
    data.directory = tmp_path
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


def test_get_config_not_created():
    """
    Tests if exception is raised if config file does not exist.
    """

    with pytest.raises(ConfigError):
        get_config()
