import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from spotdl.download.downloader import Downloader
from spotdl.utils import ffmpeg
from spotdl.utils.logging import init_logging
from spotdl.utils.spotify import SpotifyClient, SpotifyError

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
    use_official_api=False,
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
            use_official_api=use_official_api,
        )


def fake_create_subprocess_exec(*args, stdout=None, stderr=None, **kwargs):
    return FakeProcess(args)


@pytest.fixture(scope="module")
def vcr_config():
    """
    Store response bodies decoded, newer vcrpy/urllib3 don't decompress
    recorded gzip bodies on replay.
    spotapi fetches its secrets from code.thetadev.de on login, which only
    happens when recording Spotify responses, so don't record it.
    """

    return {
        "decode_compressed_response": True,
        "filter_headers": ["authorization", "cookie"],
        "ignore_hosts": ["code.thetadev.de"],
    }


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


class SpotifyCassetteError(SpotifyError):
    """
    Raised when a Spotify call has no recorded response, or replays a recorded error.
    """


class SpotifyCassette:
    """
    Records and replays SpotifyClient calls.

    The default Spotify client (SpotipyFree) talks to Spotify through curl_cffi,
    which VCR cannot intercept, so its responses are stored per call in a JSON
    file next to the test's VCR cassette instead.
    """

    def __init__(self, client, path, record_mode):
        self._client = client
        self._path = path
        self._dirty = False

        if path is None:
            # Test has no `vcr` marker, so it must not reach Spotify at all
            self._mode = "blocked"
            self._entries = {}
        elif record_mode in ("all", "rewrite"):
            self._mode = "record"
            self._entries = {}
        else:
            exists = path.is_file()
            self._entries = json.loads(path.read_text("utf-8")) if exists else {}
            if record_mode == "none" or (record_mode == "once" and exists):
                self._mode = "replay"
            else:
                self._mode = "record"

    def __getattr__(self, name):
        def call(*args, **kwargs):
            request = json.dumps([name, args, kwargs], sort_keys=True, default=str)
            key = hashlib.sha1(request.encode("utf-8")).hexdigest()

            if key in self._entries:
                entry = self._entries[key]
                if "error" in entry:
                    raise SpotifyCassetteError(entry["error"])

                return copy.deepcopy(entry["response"])

            if self._mode == "blocked":
                raise SpotifyCassetteError(
                    f"Spotify call {name}() made by a test without @pytest.mark.vcr()"
                )

            if self._mode == "replay":
                raise SpotifyCassetteError(
                    f"No recorded Spotify response for {request[:200]} in "
                    f"{self._path}. Re-run with --record-mode=once to record it."
                )

            entry = {"request": request[:200]}
            try:
                response = getattr(self._client, name)(*args, **kwargs)
                entry["response"] = json.loads(json.dumps(response))
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                self._entries[key] = entry
                self._dirty = True

            return copy.deepcopy(entry["response"])

        return call

    def save(self):
        """
        Write recorded responses to disk, if anything new was recorded.
        """

        if not self._dirty or self._path is None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, indent=1, sort_keys=True, ensure_ascii=False)
            + "\n",
            "utf-8",
        )


@pytest.fixture(autouse=True)
def spotify_cassette(request, monkeypatch, record_mode, disable_recording):
    """
    Route Spotify calls through a SpotifyCassette for every test.
    `live` tests and `--disable-recording` talk to Spotify directly.
    """

    if disable_recording or request.node.get_closest_marker("live") is not None:
        yield None
        return

    path = None
    if request.node.get_closest_marker("vcr") is not None:
        name = re.sub(r"[^\w.-]+", "_", request.node.name).strip("_")
        path = Path(
            request.node.path.parent,
            "cassettes",
            request.node.path.stem,
            f"{name}.spotify.json",
        )

    cassette = SpotifyCassette(SpotifyClient(), path, record_mode)
    monkeypatch.setattr(SpotifyClient, "_instance", cassette)

    yield cassette

    cassette.save()
