import logging
for module in ("urllib3", "spotipy", "pytube",):
    logging.getLogger(module).setLevel(logging.CRITICAL)

import coloredlogs
coloredlogs.DEFAULT_FIELD_STYLES = {
    "levelname": {"bold": True, "color": "yellow"},
    "name": {"color": "blue"},
    "lineno": {"color": "magenta"},
}

import sys

def set_logger(level):
    if level == logging.DEBUG:
        fmt = "%(levelname)s:%(name)s:%(lineno)d:\n%(message)s"
    else:
        fmt = "%(levelname)s: %(message)s"
    logging.basicConfig(format=fmt, level=level)
    logger = logging.getLogger(name=__name__)
    coloredlogs.install(level=level, fmt=fmt, logger=logger)
    return logger


def main():
    from spotdl.command_line.arguments import get_arguments
    arguments = get_arguments()
    logger = set_logger(arguments["log_level"])
    from spotdl.command_line.lib import Spotdl
    spotdl = Spotdl(arguments)
    try:
        spotdl.match_arguments()
    except KeyboardInterrupt as e:
        logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()

