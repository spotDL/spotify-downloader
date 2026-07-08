from spotdl_cli import __version__
from spotdl_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_status_reaches_embedded_server() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "server: ok (embedded)" in result.output
