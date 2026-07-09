import asyncio
import sys

import typer

from spotdl_cli import __version__
from spotdl_cli.client import embedded_client
from spotdl_cli.commands import download as _download_cmd
from spotdl_cli.commands import ffmpeg as ffmpeg_cmd
from spotdl_cli.commands import read as read_cmd
from spotdl_cli.commands import server as server_cmd
from spotdl_cli.commands import sync as _sync_cmd
from spotdl_cli.commands import web as web_cmd
from spotdl_cli.commands.auth import auth_app
from spotdl_cli.commands.config_cmd import config_app
from spotdl_cli.errors import ExitCode
from spotdl_cli.shim import Dropped, Rewritten, drop_message, translate_v4_argv

app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")

# Additive command registration (Task 13 finalizes bare-query/TTY dispatch).
_download_cmd.register(app)
_sync_cmd.register(app)


@app.command()
def version() -> None:
    """Print the spotdl version."""
    typer.echo(__version__)


@app.command()
def status() -> None:
    """Check that the spotdl server is reachable."""

    async def _check() -> str:
        async with embedded_client() as client:
            resp = await client.get("/api/v1/health")
            resp.raise_for_status()
            return str(resp.json()["status"])

    typer.echo(f"server: {asyncio.run(_check())} (embedded)")


read_cmd.register(app)
web_cmd.register(app)
server_cmd.register(app)
ffmpeg_cmd.register(app)


def main(argv: list[str] | None = None) -> None:
    """Run the v4 compat shim over the argv, then hand the result to Typer."""
    args = list(sys.argv[1:] if argv is None else argv)
    result = translate_v4_argv(args)

    if isinstance(result, Dropped):
        typer.echo(drop_message(result.flag, result.pointer), err=True)
        raise SystemExit(ExitCode.USAGE)

    if isinstance(result, Rewritten):
        for line in result.notices:
            typer.echo(line, err=True)
        app(args=result.argv)
        return

    app(args=args)


if __name__ == "__main__":
    main()
