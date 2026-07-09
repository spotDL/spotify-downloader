"""``spotdl config get|set|edit`` — inspect and edit the config file (CONTRACT D).

``get`` prints the **effective** value (file + env merged); ``set`` writes a key
to ``config.toml`` preserving the rest of the file; ``edit`` opens it in
``$EDITOR``, creating a commented template first if it does not exist.
"""

from __future__ import annotations

import typer
from rich.console import Console

from spotdl_cli.config import (
    CliConfig,
    edit_config,
    load_config,
    set_config_value,
)

config_app = typer.Typer(no_args_is_help=True, add_completion=False, help="Manage the config file.")

_err = Console(stderr=True)


@config_app.command("get")
def config_get(
    key: str | None = typer.Argument(None, help="Setting to read; omit to list all."),
) -> None:
    """Print the effective value of a setting (or all settings)."""
    cfg = load_config()
    if key is None:
        for name in CliConfig.model_fields:
            typer.echo(f"{name} = {getattr(cfg, name)}")
        return
    if key not in CliConfig.model_fields:
        _err.print(f"error: unknown setting '{key}'", style="red", markup=False)
        raise typer.Exit(code=2)
    typer.echo(str(getattr(cfg, key)))


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Setting to write."),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """Write a setting to config.toml, preserving comments and other keys."""
    try:
        coerced = set_config_value(key, value)
    except KeyError:
        _err.print(f"error: unknown setting '{key}'", style="red", markup=False)
        raise typer.Exit(code=2) from None
    except ValueError as exc:
        _err.print(f"error: invalid value for '{key}': {exc}", style="red", markup=False)
        raise typer.Exit(code=2) from None
    typer.echo(f"{key} = {coerced}")


@config_app.command("edit")
def config_edit() -> None:
    """Open the config file in $EDITOR (creating a commented template if absent)."""
    edit_config()
