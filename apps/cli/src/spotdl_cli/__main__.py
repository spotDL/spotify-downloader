import asyncio

import typer

from spotdl_cli import __version__
from spotdl_cli.client import embedded_client
from spotdl_cli.commands import ffmpeg as ffmpeg_cmd
from spotdl_cli.commands import read as read_cmd
from spotdl_cli.commands import server as server_cmd
from spotdl_cli.commands import web as web_cmd

app = typer.Typer(no_args_is_help=True, add_completion=False)


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
