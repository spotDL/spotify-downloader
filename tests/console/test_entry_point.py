import pytest
import sys

from spotdl.console.entry_point import entry_point

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
