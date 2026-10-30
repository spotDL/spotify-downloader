"""
Console module, contains the console entry point and different subcommands.
"""

from spotdl.console.entry_point import console_entry_point
from spotdl.console.remove import remove as remove_cmd

__all__ = [
    "console_entry_point",
    "remove_cmd",
]
