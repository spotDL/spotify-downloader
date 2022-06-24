import pytest
import json
import sys
import re

from spotdl.console.entry_point import console_entry_point, entry_point
from spotdl.utils.spotify import SpotifyClient
from tests.conftest import new_initialize, clean_ansi_sequence


@pytest.mark.parametrize("argument", ["-h", "--help"])
def test_show_help(capsys, monkeypatch, argument):
    """
    The --help, -h switches or no arguments should display help message
    """

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = ["dummy"]
    if argument:
        cli_args.append(argument)

    monkeypatch.setattr(sys, "argv", cli_args)

    with pytest.raises(SystemExit):
        entry_point()

    out, _ = capsys.readouterr()
    assert "usage: spotdl [-h]" in out


@pytest.mark.parametrize("argument", ["-v", "--version"])
def test_show_version(capsys, monkeypatch, argument):
    """
    The --version, -v switches or no arguments should display version message
    """

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = ["dummy"]
    if argument:
        cli_args.append(argument)

    monkeypatch.setattr(sys, "argv", cli_args)

    with pytest.raises(SystemExit):
        entry_point()

    out, _ = capsys.readouterr()

    assert re.match(r"\d{1,2}\.\d{1,2}\.\d{1,3}", out) is not None


@pytest.mark.vcr()
def test_download_song(capsys, monkeypatch, tmpdir):
    """
    This test checks if the song is downloaded correctly
    """

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = [
        "dummy",
        "download",
        "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv",
        "--no-cache",
    ]

    monkeypatch.setattr(sys, "argv", cli_args)
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)
    monkeypatch.chdir(tmpdir)

    console_entry_point()

    out, _ = capsys.readouterr()
    out = clean_ansi_sequence(out)

    assert 'Downloaded "Jim Yosef - Linked"' in out


@pytest.mark.vcr()
def test_preload_song(capsys, monkeypatch, tmpdir):
    """
    This test checks if the song is preloaded correctly.
    """

    # `dummy` is an initial argument, which represents file path.
    # in real word sys.argv when no arguments are supplied contains just the script file path
    cli_args = [
        "dummy",
        "save",
        "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv",
        "--save-file",
        "test.spotdl",
        "--preload",
        "--no-cache",
    ]

    monkeypatch.setattr(sys, "argv", cli_args)
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)
    monkeypatch.chdir(tmpdir)

    console_entry_point()

    out, _ = capsys.readouterr()

    out = clean_ansi_sequence(out)

    assert "Saved 1 song to test.spotdl" in out

    with open("test.spotdl", "r") as f:
        data = json.load(f)

    assert data[0]["name"] == "Linked"
    assert data[0]["download_url"] is not None
