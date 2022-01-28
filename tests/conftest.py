import pytest
import asyncio

from pathlib import Path

from spotdl.utils.spotify import SpotifyClient

ORIGINAL_INITIALIZE = SpotifyClient.init


class FakeProcess:
    """Instead of running ffmpeg, just fake it"""

    def __init__(self, *args):
        command = list(*args)
        self._input = Path(command[command.index("-i") + 1])
        self._output = Path(command[-1])

    async def communicate(self):
        """
        Ensure that the file has been download, and create empty output file,
        to avoid infinite loop.
        """
        assert self._input.is_file()
        self._output.open("w").close()
        return (None, None)

    async def wait(self):
        return None

    @property
    def returncode(self):
        return 0


def new_initialize(client_id, client_secret, user_auth):
    """This function allows calling `initialize()` multiple times"""
    try:
        return SpotifyClient()
    except:
        return ORIGINAL_INITIALIZE(client_id, client_secret, user_auth)


async def fake_create_subprocess_exec(*args, stdout=None, stderr=None):
    return FakeProcess(args)


@pytest.fixture()
def patch_dependencies(monkeypatch):
    """
    This function is called before each test.
    """

    monkeypatch.setattr(SpotifyClient, "init", new_initialize)
    monkeypatch.setattr(
        asyncio.subprocess, "create_subprocess_exec", fake_create_subprocess_exec
    )
