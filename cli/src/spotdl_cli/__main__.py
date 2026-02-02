"""Entry point for SpotDL CLI.

Dispatches to either:
- Typer CLI for non-interactive use (when arguments are provided)
- Textual TUI for interactive use (when no args or --tui flag)
"""

import sys


def main() -> None:
    """Main entry point that dispatches to CLI or TUI."""
    # Check if we should launch TUI or CLI
    args = sys.argv[1:]

    # TUI mode: no args, or explicit --tui/-t flag
    if not args or args[0] in ("--tui", "-t"):
        from spotdl_cli.app import run

        run()
    # Help flags should go to CLI
    elif args[0] in ("--help", "-h"):
        from spotdl_cli.cli import app

        app()
    # CLI mode: any other arguments
    else:
        from spotdl_cli.cli import app

        app()


if __name__ == "__main__":
    main()
