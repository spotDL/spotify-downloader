"""
Module for archiving sets of data
"""

from pathlib import Path
from typing import Set

__all__ = ["Archive"]


class Archive(Set):
    """
    Archive class.
    A file-persistable set.
    """

    def load(self, file: str) -> bool:
        """
        Imports the archive from the file.

        ### Arguments
        - file: the file name of the archive

        ### Returns
        - if the file exists
        """

        if not Path(file).exists():
            return False

        with open(file, "r", encoding="utf-8") as archive:
            self.clear()
            self.update([line.strip() for line in archive])

        return True

    def save(self, file: str) -> bool:
        """
        Exports the current archive to the file.

        ### Arguments
        - file: the file name of the archive
        """

        with open(file, "w", encoding="utf-8") as archive:
            for element in sorted(self):
                archive.write(f"{element}\n")

        return True

    def initialize(self, file: str) -> None:
        """
        Create the archive file if it doesn't exist.

        ### Arguments
        - file: the file name of the archive
        """
        if not Path(file).exists():
            with open(file, "w", encoding="utf-8") as archive:
                archive.write("")

    def add_entry(self, file: str, url: str) -> None:
        """
        Adds an entry to the archive file and flushes it immediately.

        ### Arguments
        - file: the file name of the archive
        - url: the URL to append to the archive file
        """
        with open(file, "a", encoding="utf-8") as archive:
            archive.write(f"{url}\n")
            archive.flush()
