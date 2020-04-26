import logzero
import sys

from spotdl import command_line


def main():
    arguments = command_line.get_arguments()
    spotdl = command_line.Spotdl(arguments.__dict__)
    try:
        spotdl.match_arguments()
    except KeyboardInterrupt as e:
        logzero.logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()

