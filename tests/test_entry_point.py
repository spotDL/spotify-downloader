import json
import sys

import pytest

from spotdl.__main__ import console_entry_point, help_notice
from spotdl.download.downloader import DownloadManager
from spotdl.search import spotifyClient

from tests.utils import tracking_files

ORIGINAL_INITIALIZE = spotifyClient.initialize


def new_initialize(clientId, clientSecret):
    """This function allows calling `initialize()` multiple times"""
    try:
        return spotifyClient.get_spotify_client()
    except:
        return ORIGINAL_INITIALIZE(clientId, clientSecret)


@pytest.fixture()
def patch_dependencies(mocker, monkeypatch):
    """This is a helper fixture to patch out everything that shouldn't be called here"""
    monkeypatch.setattr(spotifyClient, "initialize", new_initialize)
    monkeypatch.setattr(DownloadManager, "__init__", lambda _: None)
    mocker.patch.object(DownloadManager, "download_single_song", autospec=True)
    mocker.patch.object(DownloadManager, "download_multiple_songs", autospec=True)
    mocker.patch.object(DownloadManager, "resume_download_from_tracking_file", autospec=True)
    mocker.patch.object(DownloadManager, "close", autospec=True)


@pytest.mark.parametrize("argument", ["-h", "-H", "--help", None])
def test_show_help(capsys, monkeypatch, argument):
    """The --help, -h switches or no arguments should display help message"""

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = ["dummy"]
    if argument:
        cli_args.append(argument)
    monkeypatch.setattr(sys, "argv", cli_args)
    console_entry_point()

    out, _ = capsys.readouterr()
    assert out == help_notice + "\n"


@pytest.mark.vcr()
def test_download_a_single_song(capsys, patch_dependencies, monkeypatch):
    """First example from the help - using the track url should trigger song download."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert "Fetching Song...\n" in out

    assert DownloadManager.download_single_song.call_count == 1
    assert DownloadManager.download_multiple_songs.call_count == 0


@pytest.mark.vcr()
def test_download_an_album(capsys, patch_dependencies, monkeypatch):
    """Second example - download whole album."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert "Fetching Album...\n" in out

    assert DownloadManager.download_multiple_songs.call_count == 1
    assert DownloadManager.download_single_song.call_count == 0


@pytest.mark.vcr()
def test_download_a_playlist(capsys, patch_dependencies, monkeypatch):
    """
    Third example - download a playlist.
    The playlist URL is different from the example, as the original one was to big.
    """
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "https://open.spotify.com/playlist/6ahTRKeqBqzQhZIhtIIE57",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert "Fetching Playlist...\n" in out

    assert DownloadManager.download_multiple_songs.call_count == 1
    assert DownloadManager.download_single_song.call_count == 0


@pytest.mark.vcr()
def test_search_and_download(capsys, patch_dependencies, monkeypatch):
    """Fourth example - search for a song, which cannot be found."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "The HU - Sugaan Essenna",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert (
        out == 'Searching for song "The HU - Sugaan Essenna"...\n'
        'No song named "The HU - Sugaan Essenna" could be found on spotify\n'
    )

    assert DownloadManager.download_multiple_songs.call_count == 0
    assert DownloadManager.download_single_song.call_count == 0


@pytest.mark.vcr()
def test_use_tracking_file(capsys, patch_dependencies, monkeypatch, fs):
    """Fifth example - use a spotdlTrackingFile."""
    fs.create_file("Back In Black.spotdlTrackingFile", contents=json.dumps(tracking_files.back_in_black))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "Back In Black.spotdlTrackingFile",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert out == 'Preparing to resume download...\n'

    assert DownloadManager.resume_download_from_tracking_file.call_count == 1
    assert DownloadManager.download_multiple_songs.call_count == 0
    assert DownloadManager.download_single_song.call_count == 0


@pytest.mark.vcr()
def test_multiple_elements(capsys, patch_dependencies, monkeypatch):
    """Last example - chaining tasks. Download two songs and search for one."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA",
            "https://open.spotify.com/track/2SiXAy7TuUkycRVbbWDEpo",
            "The HU - Sugaan Essenna",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()

    assert 'Fetching Song...\n' in out
    assert 'Searching for song "The HU - Sugaan Essenna"...\n' in out
    assert 'No song named "The HU - Sugaan Essenna" could be found on spotify\n' in out

    assert DownloadManager.download_single_song.call_count == 2
    assert DownloadManager.download_multiple_songs.call_count == 0
