import sys
import json

import pytest

from tests.utils import tracking_files

from spotdl.download import ffmpeg
from spotdl.search import SpotifyClient
from spotdl.__main__ import console_entry_point
from spotdl.parsers.argument_parser import help_notice
from spotdl.download.downloader import DownloadManager


ORIGINAL_INITIALIZE = SpotifyClient.init


def new_initialize(client_id, client_secret, user_auth):
    """This function allows calling `initialize()` multiple times"""
    try:
        return SpotifyClient()
    except:
        return ORIGINAL_INITIALIZE(client_id, client_secret, user_auth)


@pytest.fixture()
def patch_dependencies(mocker, monkeypatch):
    """This is a helper fixture to patch out everything that shouldn't be called here"""
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)
    monkeypatch.setattr(DownloadManager, "__init__", lambda *_: None)
    monkeypatch.setattr(ffmpeg, "has_correct_version", lambda *_: True)
    mocker.patch.object(DownloadManager, "download_single_song", autospec=True)
    mocker.patch.object(DownloadManager, "download_multiple_songs", autospec=True)
    mocker.patch.object(
        DownloadManager, "resume_download_from_tracking_file", autospec=True
    )
    mocker.patch.object(DownloadManager, "__exit__", autospec=True)


@pytest.mark.parametrize("argument", ["-h", "--help"])
def test_show_help(capsys, monkeypatch, argument):
    """The --help, -h switches or no arguments should display help message"""

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = ["dummy"]
    if argument:
        cli_args.append(argument)
    monkeypatch.setattr(sys, "argv", cli_args)

    with pytest.raises(SystemExit):
        console_entry_point()

    out, _ = capsys.readouterr()
    assert help_notice in out


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

    assert DownloadManager.download_single_song.call_count == 0
    assert DownloadManager.download_multiple_songs.call_count == 1


@pytest.mark.vcr()
def test_download_an_album(capsys, patch_dependencies, monkeypatch):
    """Second example - download whole album."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dummy",
            "https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ",
            "--search-threads=1",
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
            "https://open.spotify.com/playlist/0slbokxiWCo9egF9UhVmmI",
            "--search-threads=1",
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

    # with pytest.raises(Exception, match="No song matches found on Spotify"):
    console_entry_point()

    out, err = capsys.readouterr()
    assert out == (
        'Searching Spotify for song named "The HU - Sugaan Essenna"...\n'
        "No song matches found on Spotify\n\n"
    )

    assert DownloadManager.download_multiple_songs.call_count == 0
    assert DownloadManager.download_single_song.call_count == 0


@pytest.mark.vcr()
def test_use_tracking_file(capsys, patch_dependencies, monkeypatch, fs):
    """Fifth example - use a spotdlTrackingFile."""
    fs.create_file(
        "Back In Black.spotdlTrackingFile",
        contents=json.dumps(tracking_files.back_in_black),
    )
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
    assert out == "Preparing to resume download...\n"

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
            "https://open.spotify.com/track/4EWCNWgDS8707fNSZ1oaA5",
            "https://open.spotify.com/track/2SiXAy7TuUkycRVbbWDEpo",
            "The HU - Sugaan Essenna",
        ],
    )

    console_entry_point()

    out, err = capsys.readouterr()
    assert "Fetching Song...\n" in out
    assert (
        'Found YouTube URL for "Kanye West - Heartless" : https://www.youtube.com/watch?v=s40BTpfAELs\n'
        in out
    )

    assert "Fetching Song...\n" in out
    assert (
        'Found YouTube URL for "AC/DC - You Shook Me All Night Long" : https://www.youtube.com/watch?v=SP9t2Iq_zQ8\n'
        in out
    )

    assert 'Searching Spotify for song named "The HU - Sugaan Essenna"...\n' in out
    assert "No song matches found on Spotify\n" in out

    assert DownloadManager.download_single_song.call_count == 0
    assert DownloadManager.download_multiple_songs.call_count == 1
