"""
Module for logging
"""

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from rich.theme import Theme


class SpotdlFormatter(logging.Formatter):
    """
    A custom logger for spotdl.
    """

    highlight = RichHandler.HIGHLIGHTER_CLASS()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record.
        """

        result = super().format(record)

        if record.levelno == logging.DEBUG:
            return f"[blue]{result}"

        if record.levelno == logging.INFO:
            return f"[green]{result}"

        if record.levelno == logging.WARNING:
            return f"[yellow]{result}"

        if record.levelno == logging.ERROR:
            return f"[red]{result}"

        if record.levelno == logging.CRITICAL:
            return f"[bold red]{result}"

        return result


def init_logging(log_level: str):
    """
    Initialize logging for spotdl.

    ### Arguments
    - `console`: The console to use.
    - `log_level`: The log level to use.
    """

    # Don't log too much
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("syncedlyrics").setLevel(logging.WARNING)

    # Create console
    console = Console(
        theme=Theme(
            {
                "logging.level.debug": "blue",
                "logging.level.info": "green",
                "logging.level.warning": "yellow",
                "logging.level.error": "red",
                "logging.level.critical": "bold red",
            }
        )
    )

    # Create a rich handler
    rich_handler = RichHandler(
        show_time=log_level == "DEBUG",
        log_time_format="[%X]",
        omit_repeated_times=False,
        console=console,
        level=log_level,
        markup=True,
        show_path=log_level == "DEBUG",
        show_level=log_level == "DEBUG",
        rich_tracebacks=True,
    )

    msg_format = "%(message)s"
    if log_level == "DEBUG":
        msg_format = "%(threadName)s - %(message)s"

    # Add rich handler to spotdl logger
    rich_handler.setFormatter(SpotdlFormatter(msg_format))

    # Create spotdl logger
    spotdl_logger = logging.getLogger("spotdl")

    # Setup spotdl logger
    spotdl_logger.setLevel(log_level)
    spotdl_logger.addHandler(rich_handler)

    # Install rich traceback handler
    install(show_locals=False, extra_lines=1, console=console)
