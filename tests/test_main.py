import pytest
import sys
import re

from spotdl.__main__ import console_entry_point, __version__


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
        console_entry_point()

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
        console_entry_point()

    out, _ = capsys.readouterr()

    assert re.match(r"\d{1,2}\.\d{1,2}\.\d{1,3}", out) is not None


def test_check_version():
    """
    The version should be a string of numbers separated by dots
    """

    assert re.match(r"\d{1,2}\.\d{1,2}\.\d{1,3}", __version__) is not None
