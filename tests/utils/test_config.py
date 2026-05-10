import os

import pytest
from tests.conftest import config_paths, populate_config

from spotdl.utils.config import *
from spotdl.utils.config import get_spotify_cache_path


# Fixtures to test various path setups. In the following, XDG refers to the XDG Base Directory
# specification
@pytest.fixture()
def fs_pre_xdg(tmp_path_factory, monkeypatch):
    """
    A system ignorant of XDG -- the paths are in legacy locations and the XDG variables are unset.
    """
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.delenv('XDG_CACHE_HOME', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.delenv('XDG_STATE_HOME', raising=False)
    home = tmp_path_factory.mktemp('user-home')
    monkeypatch.setenv('HOME', str(home))
    (home / '.spotdl').mkdir()
    paths = {
        'config_file': home / '.spotdl' / 'config.json',
        "state_dir": home / '.spotdl',
        "temp_dir": home / '.spotdl' / 'temp',
        "utils_dir": home / '.spotdl',
        "spotipy_client_cache_dir": home / '.spotdl' / '.spotipy',
        "spotify_cache_dir": home / '.spotdl' / '.spotify_cache',
        "errors_dir": home / '.spotdl' / 'errors',
        "web_ui_dir": home / '.spotdl' / 'web-ui',
    }
    populate_config(paths)
    return paths


@pytest.fixture()
def fs_xdg_new(tmp_path_factory, monkeypatch):
    """
    A system of an XDG-using user who hasn't yet created their spotdl directories.
    """
    home = tmp_path_factory.mktemp('user-home')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home / 'config'))
    monkeypatch.setenv('XDG_CACHE_HOME', str(home / 'cache'))
    monkeypatch.setenv('XDG_DATA_HOME', str(home / 'data'))
    monkeypatch.setenv('XDG_STATE_HOME', str(home / 'state'))
    monkeypatch.setenv('HOME', str(home))
    return config_paths()


@pytest.fixture()
def fs_xdg_full(config_dirs):
    return config_paths()


@pytest.mark.parametrize('fs', ['fs_pre_xdg', 'fs_xdg_new', 'fs_xdg_full'])
def test_config_paths(fs, request):
    """
    Tests that all config paths point to the expected locations
    """

    paths = request.getfixturevalue(fs)
    funcs = {
        'config_file'             : get_config_file,
        "state_dir"               : get_state_path,
        "temp_dir"                : get_temp_path,
        "utils_dir"               : get_utils_path,
        "spotipy_client_cache_dir": get_spotipy_client_cache_path,
        "spotify_cache_dir"       : get_spotify_cache_path,
        "errors_dir"              : get_errors_path,
        "web_ui_dir"              : get_web_ui_path,
    }
    for k in funcs:
        assert paths[k] == funcs[k]()


@pytest.mark.parametrize('fs', ['fs_pre_xdg', 'fs_xdg_new', 'fs_xdg_full'])
def test_get_config_not_created(fs, request):
    """
    Tests if exception is raised if config file does not exist.
    """

    paths = request.getfixturevalue(fs)
    try:
        os.remove(paths['config_file'])
    except FileNotFoundError:
        pass

    with pytest.raises(ConfigError):
        get_config()
