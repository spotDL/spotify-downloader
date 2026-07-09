import asyncio
import sys

import typer

from spotdl_cli import __version__
from spotdl_cli.client import embedded_client
from spotdl_cli.errors import ExitCode
from spotdl_cli.shim import Dropped, Rewritten, drop_message, translate_v4_argv

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
