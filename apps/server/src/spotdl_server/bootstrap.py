"""Programmatic Alembic migration seam (Plan 8's required entry point).

Plan 8's embedded CLI transport migrates the database at startup by importing
``spotdl_server`` and calling :func:`upgrade_to_head` — never by shelling out to
the ``alembic`` binary and never by importing ``spotdl_cli`` (keeps the
``core ← server ← cli`` dependency direction clean).

The Alembic config/scripts are located **relative to the installed package**
(via ``__file__``), not the current working directory, so this works from any
CWD and from a wheel install where the ``alembic`` tree is force-included under
the package (see ``[tool.hatch.build.targets.wheel.force-include]``).
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from spotdl_server.settings import Settings

_PACKAGE_DIR = Path(__file__).resolve().parent


def _locate_alembic() -> tuple[Path, Path]:
    """Return ``(alembic.ini, alembic_scripts_dir)`` resolved from the package.

    Two layouts are supported, tried in order:
      * wheel install — force-included at ``<package>/alembic.ini`` + ``<package>/alembic``.
      * editable/source tree — ``apps/server/alembic.ini`` + ``apps/server/alembic``
        (two levels up from ``src/spotdl_server``).
    """
    candidates = (
        _PACKAGE_DIR,  # wheel: force-included beside the package
        _PACKAGE_DIR.parent.parent,  # source: apps/server/ (src/spotdl_server -> src -> server)
    )
    for base in candidates:
        ini = base / "alembic.ini"
        scripts = base / "alembic"
        if ini.is_file() and scripts.is_dir():
            return ini, scripts
    raise RuntimeError(
        "could not locate the packaged alembic config relative to "
        f"{_PACKAGE_DIR}; checked {[str(c) for c in candidates]}"
    )


def _build_config(settings: Settings) -> Config:
    ini, scripts = _locate_alembic()
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(scripts))
    # env.py honours this attribute (and `-x db_url`) ahead of Settings().
    cfg.attributes["db_url"] = settings.effective_database_url()
    return cfg


def upgrade_to_head(settings: Settings, *, quiet: bool = False) -> None:
    """Run Alembic ``upgrade head`` programmatically against
    ``settings.effective_database_url()``.

    Idempotent: a no-op when the database is already at head. Synchronous by
    design — call once at process startup, before the event loop is running.
    """
    # Mirror build_engine: ensure the SQLite parent dir exists before Alembic
    # opens the file (Postgres/explicit URLs need no local directory).
    if settings.database_url is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    cfg = _build_config(settings)
    if quiet:
        # An interactive CLI (embedded mode) suppresses alembic's fileConfig
        # re-configuration (env.py honours this attribute); errors still raise.
        cfg.attributes["skip_logging_config"] = True
    command.upgrade(cfg, "head")
