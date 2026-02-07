"""URL archive for tracking downloaded songs and avoiding re-downloads."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Archive(set[str]):
    """Simple URL archive persisted as a text file (one URL per line)."""

    def load(self, file: str | Path) -> bool:
        """Load URLs from an archive file.

        Args:
            file: Path to the archive file.

        Returns:
            True if the file was loaded successfully.
        """
        path = Path(file)
        if not path.exists():
            return False

        try:
            with open(path, encoding="utf-8") as f:
                self.update(line.strip() for line in f if line.strip())
            logger.debug("Loaded %d URLs from archive %s", len(self), path)
            return True
        except OSError as e:
            logger.warning("Failed to load archive %s: %s", path, e)
            return False

    def save(self, file: str | Path) -> bool:
        """Save URLs to an archive file.

        Args:
            file: Path to the archive file.

        Returns:
            True if the file was saved successfully.
        """
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self)))
            logger.debug("Saved %d URLs to archive %s", len(self), path)
            return True
        except OSError as e:
            logger.warning("Failed to save archive %s: %s", path, e)
            return False
