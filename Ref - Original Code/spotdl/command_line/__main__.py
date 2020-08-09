import logging
import sys

from spotdl.command_line.core import Spotdl
from spotdl.command_line import arguments
from spotdl.command_line.exceptions import ArgumentError

import spotdl.command_line.exitcodes
import spotdl.version

# hardcode loglevel for dependencies so that they do not spew generic
# log messages along with spotdl.
logger = logging.getLogger(name=__name__)


def main():
    try:
        parser = arguments.get_arguments()
    except ArgumentError as e:
        logger.info(e.args[0])
        sys.exit(spotdl.command_line.exitcodes.ARGUMENT_ERROR)
    else:
        args = parser.parse_args().__dict__
        logger.debug("spotdl {}".format(spotdl.version.__version__))
    try:
        with Spotdl(args) as spotdl_handler:
            exitcode = spotdl_handler.match_arguments()
    except ArgumentError as e:
        parser.error(
            e.args[0],
            exitcode=spotdl.command_line.exitcodes.ARGUMENT_ERROR
        )
    except KeyboardInterrupt as e:
        print("", file=sys.stderr)
        logger.exception(e)
        sys.exit(spotdl.command_line.exitcodes.KEYBOARD_INTERRUPT)
    else:
        sys.exit(exitcode)


if __name__ == "__main__":
    main()

