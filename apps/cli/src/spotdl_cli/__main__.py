"""``spotdl`` entry point — command registration + argv dispatch (Plan 8 Task 13).

``main()`` is the console-script entry point. It runs the v4 compatibility shim
over ``argv`` (translating v4 flags/operations, or failing fast on a removed one),
then applies the bare-query / TTY dispatch, and finally hands the normalized argv
to Typer:

    sys.argv → translate_v4_argv (shim) → _dispatch (bare-query / TTY) → Typer

Every spec §7 command is registered here (``download`` and bare-query sugar,
``search``/``url``/``save``/``meta``, ``sync``, ``web``, ``server``, ``auth``,
``config``, ``ffmpeg``, ``tui`` stub, plus the kept ``version``/``status``). A
global eager ``--version``/``-v`` option prints the version and exits (satisfying
the v4 shim's SAME row for it); ``spotdl version`` remains as a subcommand too.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Annotated

import typer

from spotdl_cli import __version__
from spotdl_cli.commands import download as _download_cmd
from spotdl_cli.commands import ffmpeg as ffmpeg_cmd
from spotdl_cli.commands import read as read_cmd
from spotdl_cli.commands import server as server_cmd
from spotdl_cli.commands import sync as _sync_cmd
from spotdl_cli.commands import tui as tui_cmd
from spotdl_cli.commands import web as web_cmd
from spotdl_cli.commands.auth import auth_app
from spotdl_cli.commands.config_cmd import config_app
from spotdl_cli.commands.tui import TUI_STUB_MESSAGE
from spotdl_cli.errors import ExitCode
from spotdl_cli.shim import V5_COMMANDS, Dropped, Rewritten, drop_message, translate_v4_argv


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show the spotdl version and exit.",
            is_eager=True,
            callback=_version_callback,
        ),
    ] = False,
) -> None:
    """spotdl — download music, with metadata, from the community server."""


app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")

_download_cmd.register(app)
_sync_cmd.register(app)


@app.command()
def version() -> None:
    """Print the spotdl version."""
    typer.echo(__version__)


@app.command()
def status(
    offline: Annotated[
        bool, typer.Option("--offline", help="Check the offline embedded server only.")
    ] = False,
) -> None:
    """Report whether the effective spotdl server is reachable."""
    typer.echo(asyncio.run(_probe_status(offline)))


read_cmd.register(app)
web_cmd.register(app)
server_cmd.register(app)
ffmpeg_cmd.register(app)
tui_cmd.register(app)


async def _probe_status(offline: bool) -> str:
    """Check the effective *resolution* transport's health (CONTRACT C).

    Deliberately does NOT go through ``SpotdlClient.from_config``: that always
    builds the embedded *downloads* transport (which boots SQLite + runs
    migrations), but a plain ``status`` only needs to know whether the server it
    would resolve metadata against answers. So this runs just the CONTRACT C
    resolution-transport selection and hits ``/api/v1/health``. The embedded DB is
    therefore created only when we are offline or fall back to the embedded server
    — never when the remote community server is reachable.
    """
    from urllib.parse import urlsplit

    from spotdl_server.settings import DeploymentMode, Settings

    from spotdl_cli.client import DEFAULT_API_URL
    from spotdl_cli.config import get_token, load_config
    from spotdl_cli.fallback import HEALTH_PATH, select_resolution_transport
    from spotdl_cli.transport import EmbeddedTransport, RemoteTransport

    cfg = load_config()
    api_url = str(cfg.api_url or DEFAULT_API_URL)
    is_offline = offline or cfg.offline
    parts = urlsplit(api_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    cred = get_token(origin)
    token = cred.token if cred is not None else None

    embedded: EmbeddedTransport | None = None

    def make_embedded() -> EmbeddedTransport:
        nonlocal embedded
        embedded = EmbeddedTransport(Settings(mode=DeploymentMode.EMBEDDED))
        return embedded

    transport = await select_resolution_transport(
        offline=is_offline,
        api_url=api_url,
        require_remote=False,
        make_remote=lambda: RemoteTransport(api_url, token=token),
        make_embedded=make_embedded,
    )
    try:
        # A freshly-built embedded transport still needs its DB + ASGI app booted;
        # a remote transport is ready to use as returned.
        if embedded is not None:
            await embedded.start()
        resp = await transport.http_client().get(HEALTH_PATH)
        resp.raise_for_status()
        state = str(resp.json()["status"])
    finally:
        await transport.aclose()

    where = "embedded" if embedded is not None else f"remote {api_url}"
    return f"server: {state} ({where})"


def _dispatch(argv: list[str]) -> list[str]:
    """Route a post-shim argv into a concrete command (spec §7).

    * bare ``spotdl`` in a TTY → the interactive ``tui`` (its stub for now); in a
      non-TTY the empty argv falls through to Typer's ``no_args_is_help`` so pipes
      and CI see the help text.
    * a first token that is neither a registered command nor an option, but looks
      like a URL/query → ``download`` (bare-query sugar). The shim already applies
      this to a v4-style argv; doing it here too keeps a v5-native argv (one that
      bypassed a shim rewrite) on the same path and makes the routing rule live in
      one place.
    """
    if not argv:
        if sys.stdout.isatty():
            return ["tui"]
        return argv
    first = argv[0]
    if first.startswith("-") or first in V5_COMMANDS:
        return argv
    return ["download", *argv]


def main(argv: list[str] | None = None) -> None:
    """Run the v4 compat shim + dispatch over the argv, then hand it to Typer."""
    args = list(sys.argv[1:] if argv is None else argv)
    result = translate_v4_argv(args)

    if isinstance(result, Dropped):
        typer.echo(drop_message(result.flag, result.pointer), err=True)
        raise SystemExit(ExitCode.USAGE)

    if isinstance(result, Rewritten):
        for line in result.notices:
            typer.echo(line, err=True)
        args = result.argv

    app(args=_dispatch(args))


# Re-exported so ``from spotdl_cli.__main__ import TUI_STUB_MESSAGE`` (and tests)
# have the pinned stub copy alongside the app/dispatch it drives.
__all__ = ["TUI_STUB_MESSAGE", "app", "main"]


if __name__ == "__main__":
    main()
