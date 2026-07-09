"""CLI-side database bootstrap: flock-serialized programmatic migrations.

The CLI never shells out to the ``alembic`` binary and never reaches into
``apps/server`` internals — it migrates by importing the Plan 5 seam
(:func:`spotdl_server.bootstrap.upgrade_to_head`) and wrapping it in an OS-level
file lock so two concurrently-launched ``spotdl`` processes cannot race one
SQLite file. The second waiter acquires the lock only after the first commits,
finds the DB already at head, and no-ops.

The lock is a real advisory OS lock (``fcntl.flock`` on POSIX, ``msvcrt.locking``
on Windows), not an in-process ``threading`` primitive, so it serializes across
*processes* — the actual hazard when a user runs two ``spotdl`` commands at once.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

try:
    from spotdl_server.bootstrap import upgrade_to_head
except ImportError as exc:  # pragma: no cover - guard for a regressed upstream seam
    raise RuntimeError("Plan 5 seam missing — fix upstream, do not patch apps/server here") from exc

from spotdl_server.settings import Settings

# Blocking acquire budget: a migration is milliseconds, so 30 s only elapses if
# another process is wedged holding the lock — surface that as a clear error
# rather than hanging forever.
_LOCK_TIMEOUT_S = 30.0
_POLL_INTERVAL_S = 0.05


def _lock_path(settings: Settings) -> Path:
    """The migration lock file, alongside the SQLite database in the data dir.

    A per-data-dir serialization point even for non-SQLite (explicit
    ``database_url``) deployments — one lock guards one data dir's boot.
    """
    return settings.data_dir / "spotdl.db.migrate.lock"


# ``sys.platform`` (not a runtime flag) so the type checker prunes the branch
# that can't apply to the host — ``msvcrt`` off Windows, ``fcntl`` on it.
if sys.platform == "win32":  # pragma: no cover - exercised only on Windows CI

    def _acquire(handle: IO[str], *, timeout: float) -> None:
        import msvcrt

        deadline = time.monotonic() + timeout
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"could not acquire migration lock within {timeout:.0f}s"
                    ) from None
                time.sleep(_POLL_INTERVAL_S)

    def _release(handle: IO[str]) -> None:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:

    def _acquire(handle: IO[str], *, timeout: float) -> None:
        import fcntl

        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"could not acquire migration lock within {timeout:.0f}s"
                    ) from None
                time.sleep(_POLL_INTERVAL_S)

    def _release(handle: IO[str]) -> None:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _file_lock(path: Path, *, timeout: float) -> Iterator[None]:
    """Hold an exclusive advisory lock on ``path`` for the ``with`` body."""
    with open(path, "w") as handle:
        _acquire(handle, timeout=timeout)
        try:
            yield
        finally:
            _release(handle)


def migrate(settings: Settings) -> None:
    """Run ``upgrade head`` against ``settings``' database, serialized by a lock.

    Idempotent and process-safe: creates the data dir, takes an exclusive lock on
    the migration lock file, then runs the programmatic Alembic upgrade. A second
    concurrent ``spotdl`` blocks on the lock (up to 30 s), then sees an
    already-migrated DB and returns without changes.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    # Alembic's env config re-INFOs its migration context on every boot; that is
    # noise on stderr for an interactive CLI (`spotdl status --offline`). Errors
    # still surface as exceptions.
    logging.getLogger("alembic").setLevel(logging.WARNING)
    with _file_lock(_lock_path(settings), timeout=_LOCK_TIMEOUT_S):
        upgrade_to_head(settings, quiet=True)
