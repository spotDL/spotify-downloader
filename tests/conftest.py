import re
import subprocess
import json
from pathlib import Path
import platformdirs

import pytest

from spotdl.download.downloader import Downloader
from spotdl.utils import ffmpeg
from spotdl.utils.config import DEFAULT_CONFIG
from spotdl.utils.logging import init_logging
from spotdl.utils.spotify import SpotifyClient

ORIGINAL_INITIALIZE = SpotifyClient.init

SpotifyClient.init(
    "ad996353310b4ced82f5be1309b11b14", "2e5851cff3bc45f495cd7cfa40be1b48"
)

init_logging("MATCH")


class FakeProcess:
    """Instead of running ffmpeg, just fake it"""

    def __init__(self, *args):
        command = list(*args)
        self._input = Path(command[command.index("-i") + 1])
        self._output = Path(command[-1])

    def communicate(self):
        """
        Ensure that the file has been download, and create empty output file,
        to avoid infinite loop.
        """
        assert self._input.is_file()
        self._output.open("w").close()
        return (None, None)

    def wait(self):
        return None

    @property
    def returncode(self):
        return 0


def new_initialize(
    client_id,
    client_secret,
    auth_token=None,
    user_auth=False,
    cache_path=None,
    no_cache=True,
    headless=True,
    max_retries=3,
    use_cache_file=False,
):
    """This function allows calling `initialize()` multiple times"""
    try:
        return SpotifyClient()
    except Exception:
        return ORIGINAL_INITIALIZE(
            client_id="ad996353310b4ced82f5be1309b11b14",
            client_secret="2e5851cff3bc45f495cd7cfa40be1b48",
            auth_token=auth_token,
            user_auth=user_auth,
            cache_path=cache_path,
            no_cache=no_cache,
            headless=headless,
            max_retries=max_retries,
            use_cache_file=use_cache_file,
        )


def fake_create_subprocess_exec(*args, stdout=None, stderr=None, **kwargs):
    return FakeProcess(args)


@pytest.fixture()
def patch_dependencies(mocker, monkeypatch):
    """
    This function is called before each test.
    """

    monkeypatch.setattr(SpotifyClient, "init", new_initialize)
    monkeypatch.setattr(subprocess, "Popen", fake_create_subprocess_exec)
    monkeypatch.setattr(ffmpeg, "get_ffmpeg_version", lambda *_: (4.4, 2022))

    mocker.patch.object(Downloader, "download_song", autospec=True)
    mocker.patch.object(Downloader, "download_multiple_songs", autospec=True)


def config_paths():
    pd=platformdirs
    return {
        'config_file'             : pd.user_config_path(appname='spotdl') / 'config.json',
        "state_dir"               : pd.user_state_path(appname='spotdl'),
        "temp_dir"                : pd.user_cache_path(appname='spotdl') / 'temp',
        "utils_dir"               : pd.user_data_path(appname='spotdl') / 'utils',
        "spotipy_client_cache_dir": pd.user_cache_path(appname='spotdl') / 'spotipy',
        "spotify_cache_dir"       : pd.user_cache_path(appname='spotdl') / 'spotify_cache',
        "errors_dir"              : pd.user_log_path(appname='spotdl') / 'errors',
        "web_ui_dir"              : pd.user_data_path(appname='spotdl') / 'web-ui',
    }


@pytest.fixture()
def config_dirs(tmp_path_factory, monkeypatch):
    """
    A system with all spotdl directories set to temporary directories.
    Use this especially for tests that write (eg temp files) to the filesystem.
    """
    home = tmp_path_factory.mktemp('user-home')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home / 'config'))
    monkeypatch.setenv('XDG_CACHE_HOME', str(home / 'cache'))
    monkeypatch.setenv('XDG_DATA_HOME', str(home / 'data'))
    monkeypatch.setenv('XDG_STATE_HOME', str(home / 'state'))
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    paths = config_paths()
    populate_config(paths)

def populate_config(paths):
    for p in filter(lambda k: k.endswith('_file'), paths):
        f = paths[p]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
    for p in filter(lambda k: k.endswith('_dir'), paths):
        d = paths[p]
        d.mkdir(parents=True, exist_ok=True)
    with open(paths['config_file'], 'w') as fp:
        json.dump(DEFAULT_CONFIG, fp, indent=4)


def clean_ansi_sequence(text):
    """
    Remove ANSI escape sequences from text
    """

    return re.sub(
        r"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])",
        "",
        text,
    )
