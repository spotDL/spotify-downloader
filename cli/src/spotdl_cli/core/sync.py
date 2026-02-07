"""Playlist sync manager for the sync command.

Handles synchronizing a local music library with remote playlists,
including renaming, deletion, and downloading of new songs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from spotdl_cli.config import Settings
from spotdl_cli.core.m3u import create_file_name
from spotdl_cli.core.types import Song

logger = logging.getLogger(__name__)

# Sync file JSON structure:
# {
#   "type": "sync",
#   "query": ["original query 1", ...],
#   "songs": [Song.json, ...]
# }


class SyncFile:
    """Represents a .spotdl sync file."""

    def __init__(
        self,
        query: list[str],
        songs: list[Song],
    ) -> None:
        self.query = query
        self.songs = songs

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "sync",
            "query": self.query,
            "songs": [song.json if hasattr(song, "json") else song.to_dict() for song in self.songs],
        }

    def save(self, path: Path) -> None:
        """Save sync file to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("Saved sync file: %s", path)

    @classmethod
    def load(cls, path: Path) -> SyncFile:
        """Load sync file from disk.

        Args:
            path: Path to the .spotdl sync file.

        Returns:
            SyncFile instance.

        Raises:
            ValueError: If the file is not a valid sync file.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if data.get("type") != "sync":
            raise ValueError(f"Not a sync file (type={data.get('type')})")

        query = data.get("query", [])
        songs = [Song.from_dict(s) for s in data.get("songs", [])]

        return cls(query=query, songs=songs)


class PlaylistSyncManager:
    """Manages playlist synchronization.

    Compares old playlist state (from sync file) with current state
    (freshly resolved) and determines which files to rename, delete,
    or download.
    """

    def __init__(
        self,
        settings: Settings,
        output_template: str | None = None,
        file_extension: str | None = None,
    ) -> None:
        self._settings = settings
        self._output_template = output_template or settings.output_template
        self._file_extension = file_extension or settings.audio_format

    def _get_song_path(self, song: Song) -> Path:
        """Get the expected file path for a song."""
        return self._settings.output_dir / create_file_name(
            song,
            self._output_template,
            self._file_extension,
        )

    def compute_sync_actions(
        self,
        old_songs: list[Song],
        new_songs: list[Song],
        no_delete: bool = False,
        remove_lrc: bool = False,
    ) -> SyncActions:
        """Compute the actions needed to sync old state to new state.

        Args:
            old_songs: Songs from the sync file (previous state).
            new_songs: Songs from the current remote playlist.
            no_delete: If True, skip deletion of removed songs.
            remove_lrc: If True, also delete .lrc files for removed songs.

        Returns:
            SyncActions with lists of renames, deletions, and new songs.
        """
        old_urls = {s.url for s in old_songs}
        new_urls = {s.url for s in new_songs}
        new_by_url = {s.url: s for s in new_songs}

        renames: list[tuple[Path, Path]] = []
        deletions: list[Path] = []
        downloads: list[Song] = []

        # Process old songs: delete or rename
        for old_song in old_songs:
            old_path = self._get_song_path(old_song)

            if old_song.url not in new_urls:
                # Song removed from playlist
                if not no_delete and old_path.exists():
                    deletions.append(old_path)
                    if remove_lrc:
                        lrc_path = old_path.with_suffix(".lrc")
                        if lrc_path.exists():
                            deletions.append(lrc_path)
            else:
                # Song still in playlist, check if path changed
                new_song = new_by_url[old_song.url]
                new_path = self._get_song_path(new_song)

                if old_path != new_path and old_path.exists():
                    renames.append((old_path, new_path))

        # Songs to download (new additions)
        for new_song in new_songs:
            if new_song.url not in old_urls:
                downloads.append(new_song)

        return SyncActions(
            renames=renames,
            deletions=deletions,
            downloads=downloads,
        )

    def execute_renames(self, renames: list[tuple[Path, Path]]) -> int:
        """Execute file renames.

        Args:
            renames: List of (old_path, new_path) tuples.

        Returns:
            Number of successful renames.
        """
        count = 0
        for old_path, new_path in renames:
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                old_path.rename(new_path)
                logger.info("Renamed: %s -> %s", old_path.name, new_path.name)

                # Also rename LRC file if it exists
                old_lrc = old_path.with_suffix(".lrc")
                if old_lrc.exists():
                    new_lrc = new_path.with_suffix(".lrc")
                    old_lrc.rename(new_lrc)

                count += 1
            except OSError as e:
                logger.error("Failed to rename %s: %s", old_path, e)

        return count

    def execute_deletions(self, deletions: list[Path]) -> int:
        """Execute file deletions.

        Args:
            deletions: List of file paths to delete.

        Returns:
            Number of successful deletions.
        """
        count = 0
        for path in deletions:
            try:
                path.unlink()
                logger.info("Deleted: %s", path.name)
                count += 1
            except OSError as e:
                logger.error("Failed to delete %s: %s", path, e)

        return count


class SyncActions:
    """Container for computed sync actions."""

    def __init__(
        self,
        renames: list[tuple[Path, Path]],
        deletions: list[Path],
        downloads: list[Song],
    ) -> None:
        self.renames = renames
        self.deletions = deletions
        self.downloads = downloads

    @property
    def has_changes(self) -> bool:
        """Whether there are any changes to apply."""
        return bool(self.renames or self.deletions or self.downloads)

    def summary(self) -> str:
        """Get a human-readable summary of actions."""
        parts = []
        if self.renames:
            parts.append(f"{len(self.renames)} rename(s)")
        if self.deletions:
            parts.append(f"{len(self.deletions)} deletion(s)")
        if self.downloads:
            parts.append(f"{len(self.downloads)} new download(s)")
        return ", ".join(parts) if parts else "No changes"
