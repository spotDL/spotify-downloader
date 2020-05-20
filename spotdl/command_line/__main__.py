import logging
import coloredlogs

import sys

from spotdl.command_line.core import Spotdl
from spotdl.command_line.arguments import get_arguments
from spotdl.command_line.exceptions import ArgumentError

# hardcode loglevel for dependencies so that they do not spew generic
# log messages along with spotdl.
for module in ("chardet", "urllib3", "spotipy", "pytube"):
    logging.getLogger(module).setLevel(logging.CRITICAL)

coloredlogs.DEFAULT_FIELD_STYLES = {
    "levelname": {"bold": True, "color": "yellow"},
    "name": {"color": "blue"},
    "lineno": {"color": "magenta"},
}


def set_logger(level):
    if level == logging.DEBUG:
        fmt = "%(levelname)s:%(name)s:%(lineno)d:\n%(message)s\n"
    else:
        fmt = "%(levelname)s: %(message)s"
    logging.basicConfig(format=fmt, level=level)
    logger = logging.getLogger(name=__name__)
    coloredlogs.install(level=level, fmt=fmt, logger=logger)
    return logger


def main():
    try:
        argument_handler = get_arguments()
    except ArgumentError as e:
        logger = set_logger(logging.INFO)
        logger.info(e.args[0])
        sys.exit(5)

    logging_level = argument_handler.get_logging_level()
    logger = set_logger(logging_level)
    try:
        spotdl = Spotdl(argument_handler)
    except ArgumentError as e:
        argument_handler.parser.error(e.args[0])
    try:
        spotdl.match_arguments()
    except KeyboardInterrupt as e:
        print("", file=sys.stderr)
        logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()

