import re
import subprocess
from pathlib import Path

import pytest
from freezegun import freeze_time

from spotdl.download.downloader import Downloader
from spotdl.utils import ffmpeg
from spotdl.utils.logging import init_logging
from spotdl.utils.spotify import SpotifyClient

ORIGINAL_INITIALIZE = SpotifyClient.init

SpotifyClient.init(
    "ad996353310b4ced82f5be1309b11b14", "2e5851cff3bc45f495cd7cfa40be1b48"
)

init_logging("MATCH")


@pytest.fixture
def last_vcr_recording_time():
    with freeze_time("2024-10-14 12:00:00"):
        yield


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


def clean_ansi_sequence(text):
    """
    Remove ANSI escape sequences from text
    """

    return re.sub(
        r"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])",
        "",
        text,
    )
