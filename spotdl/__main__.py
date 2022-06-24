"""
Main module for spotdl. Exports version and main function.
"""

from spotdl.console import console_entry_point
from spotdl._version import __version__

if __name__ == "__main__":
    console_entry_point()
