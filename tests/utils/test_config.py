import os
import platform
from pathlib import Path
from types import SimpleNamespace

import pytest

from spotdl.utils.config import *


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    data = SimpleNamespace()
    # Linux follows XDG (~/.config/spotdl), other platforms use ~/.spotdl
    if platform.system() == "Linux":
        data.spotdl_path = Path(tmp_path, ".config", "spotdl")
    else:
        data.spotdl_path = Path(tmp_path, ".spotdl")
    yield data


def test_get_spotdl_path(setup):
    """
    Tests that the spotdl path is created if it does not exist.
    """

    assert get_spotdl_path() == setup.spotdl_path
    assert setup.spotdl_path.is_dir()


def test_get_config_path(setup):
    """
    Tests if the path to config file is correct.
    """

    assert get_config_file() == Path(setup.spotdl_path, "config.json")


def test_get_cache_path(setup):
    """
    Tests if the path to the cache file is correct.
    """

    assert get_cache_path() == Path(setup.spotdl_path, ".spotipy")


def test_get_temp_path(setup):
    """
    Tests if the path to the temp folder is correct.
    """

    assert get_temp_path() == Path(setup.spotdl_path, "temp")


def test_get_config_not_created(setup):
    """
    Tests if exception is raised if config file does not exist.
    """

    with pytest.raises(ConfigError):
        get_config()


def test_use_official_api_default():
    """
    Tests that the official API client is opt-in.
    """

    settings = create_settings_type(SimpleNamespace(), {}, SPOTIFY_OPTIONS)

    assert settings["use_official_api"] is False


def test_use_official_api_from_config():
    """
    Tests that config can enable the official API client.
    """

    settings = create_settings_type(
        SimpleNamespace(),
        {"use_official_api": True},
        SPOTIFY_OPTIONS,
    )

    assert settings["use_official_api"] is True


def test_use_official_api_argument_overrides_config():
    """
    Tests that CLI arguments take priority over config values.
    """

    settings = create_settings_type(
        SimpleNamespace(use_official_api=True),
        {"use_official_api": False},
        SPOTIFY_OPTIONS,
    )

    assert settings["use_official_api"] is True
