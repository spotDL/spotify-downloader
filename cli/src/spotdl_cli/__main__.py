"""Main entry point for SpotDL CLI."""

from spotdl_cli.app import SpotDLApp


def main() -> None:
    """Run the SpotDL TUI application."""
    app = SpotDLApp()
    app.run()


if __name__ == "__main__":
    main()
