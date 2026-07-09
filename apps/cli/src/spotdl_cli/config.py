"""Config file, credentials store, and setting precedence (CONTRACT D).

The CLI's effective configuration is resolved with the precedence

    CLI flag  >  environment (``SPOTDL_*``)  >  ``config.toml``  >  built-in default

:func:`load_config` returns a :class:`CliConfig` merged from the config file and
the environment; each command then layers its explicit flags on top via
:func:`merge_flag` (a flag left at its Typer default ``None`` does not override).

The config file lives under :func:`platformdirs.user_config_dir` and is
read/written with **tomlkit** so ``config edit`` preserves comments/formatting.
PATs are stored **separately** in ``credentials.toml`` (mode ``0600``), keyed by
server origin so multiple servers can be logged in at once — never in the shared
``config.toml`` and never logged.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import platformdirs
import tomlkit
from pydantic import BaseModel, ConfigDict

from spotdl_cli.client import DEFAULT_API_URL

__all__ = [
    "DEFAULT_API_URL",
    "CliConfig",
    "StoredCredential",
    "config_dir",
    "data_dir",
    "config_path",
    "credentials_path",
    "load_config",
    "merge_flag",
    "default_config_template",
    "store_token",
    "get_token",
    "delete_token",
]

_APP = "spotdl"
_ENV_PREFIX = "SPOTDL_"


class CliConfig(BaseModel):
    """User-facing settings (TOML keys mirror the field names) — CONTRACT D.

    ``output_dir`` maps to the embedded server's ``SPOTDL_LIBRARY_PATH`` /
    ``Settings.library_path`` (the engine's output root); ``None`` means the
    server default ``data_dir/"music"``.
    """

    model_config = ConfigDict(extra="ignore")

    api_url: str = DEFAULT_API_URL
    offline: bool = False
    output_dir: Path | None = None
    output_template: str = "{artists} - {title}.{output-ext}"
    format: str = "mp3"
    bitrate: str = "auto"
    overwrite: str = "skip"
    restrict: str = "none"
    threads: int = 4
    ffmpeg: str | None = None
    ffmpeg_args: str = ""
    ytdlp_args: str = ""
    cookie_file: Path | None = None
    proxy: str | None = None
    embed_lyrics: bool = True
    generate_lrc: bool = False
    sponsor_block: bool = False
    id3_separator: str = "/"
    log_level: str = "INFO"


# ---- platformdirs paths -----------------------------------------------------
# Resolved on every call (not cached) so tests can monkeypatch ``platformdirs``.


def config_dir() -> Path:
    return Path(platformdirs.user_config_dir(_APP, appauthor=False))


def data_dir() -> Path:
    """The embedded SQLite / ffmpeg / provider-cache home (CONTRACT D)."""
    return Path(platformdirs.user_data_dir(_APP, appauthor=False))


def config_path() -> Path:
    return config_dir() / "config.toml"


def credentials_path() -> Path:
    return config_dir() / "credentials.toml"


# ---- loading + precedence ---------------------------------------------------


def _env_overrides() -> dict[str, str]:
    """``SPOTDL_<FIELD>`` env values for known ``CliConfig`` fields (as strings;
    pydantic coerces them to the field type)."""
    out: dict[str, str] = {}
    for name in CliConfig.model_fields:
        env_key = _ENV_PREFIX + name.upper()
        if env_key in os.environ:
            out[name] = os.environ[env_key]
    return out


def load_config(path: Path | None = None) -> CliConfig:
    """Return the file+env-merged :class:`CliConfig` (a missing file ⇒ defaults)."""
    path = path if path is not None else config_path()
    data: dict[str, Any] = {}
    if path.exists():
        data.update(tomlkit.parse(path.read_text()).unwrap())
    data.update(_env_overrides())
    return CliConfig(**data)


def merge_flag(value: Any, *, config_default: Any) -> Any:
    """Layer an explicit CLI flag over the effective config default.

    ``value is None`` means the flag was left at its Typer default and must not
    override; any other value (including falsey ones the user typed) wins.
    """
    return config_default if value is None else value


# ---- config file writing (config set / edit) --------------------------------

_TEMPLATE_HEADER = "# spotDL configuration (config.toml)\n"


def default_config_template() -> str:
    """A fully commented default config: every key shown at its default value.

    Because every line is commented, parsing it yields an empty document, so the
    built-in defaults still apply until the user uncomments/sets a key.
    """
    lines = [
        _TEMPLATE_HEADER,
        "# Uncomment and edit any line to override the built-in default.\n",
        "# Precedence: CLI flag > SPOTDL_* env > this file > default.\n",
        "\n",
    ]
    defaults = CliConfig()
    for name in CliConfig.model_fields:
        value = getattr(defaults, name)
        lines.append(f"# {name} = {_toml_repr(value)}\n")
    return "".join(lines)


def _toml_repr(value: Any) -> str:
    """Render a default value as the TOML literal a user would type."""
    return str(tomlkit.item(_to_toml_value(value)).as_string())


def _to_toml_value(value: Any) -> Any:
    """Coerce a Python value into something tomlkit can serialize.

    ``None`` has no TOML representation, so it is shown as an empty string in the
    commented template (the key stays commented, so this is display-only).
    """
    if value is None:
        return ""
    if isinstance(value, Path):
        return str(value)
    return value


def _load_or_template_doc(path: Path) -> tomlkit.TOMLDocument:
    if path.exists():
        return tomlkit.parse(path.read_text())
    return tomlkit.parse(default_config_template())


def set_config_value(key: str, raw_value: str, *, path: Path | None = None) -> Any:
    """Validate/coerce ``raw_value`` for ``key`` and write it, preserving the rest.

    Raises :class:`KeyError` if ``key`` is not a known ``CliConfig`` field.
    """
    if key not in CliConfig.model_fields:
        raise KeyError(key)
    # Validate + coerce the single field through the model (all fields default,
    # so a one-field construction is enough to type-check the value).
    coerced = getattr(CliConfig.model_validate({key: raw_value}), key)
    path = path if path is not None else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = _load_or_template_doc(path)
    doc[key] = _to_toml_value(coerced)
    path.write_text(tomlkit.dumps(doc))
    return coerced


def ensure_config_file(path: Path | None = None) -> Path:
    """Create ``config.toml`` from the commented template if it does not exist."""
    path = path if path is not None else config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(default_config_template())
    return path


def edit_config(path: Path | None = None) -> None:
    """Open the config file in ``$EDITOR`` (creating a template first if absent)."""
    path = ensure_config_file(path)
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    subprocess.run([editor, str(path)], check=False)


# ---- credentials store ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoredCredential:
    """A stored PAT for one server origin (``credentials.toml``)."""

    token: str
    email: str | None = None
    token_id: str | None = None


def _read_credentials(path: Path) -> tomlkit.TOMLDocument:
    if path.exists():
        return tomlkit.parse(path.read_text())
    return tomlkit.document()


def _write_credentials(path: Path, doc: tomlkit.TOMLDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc))
    os.chmod(path, 0o600)


def _servers_table(doc: tomlkit.TOMLDocument) -> Any:
    servers = doc.get("servers")
    if servers is None:
        servers = tomlkit.table()
        doc["servers"] = servers
    return servers


def store_token(
    origin: str,
    token: str,
    email: str | None = None,
    *,
    token_id: str | None = None,
    path: Path | None = None,
) -> None:
    """Store ``token`` for ``origin`` in ``credentials.toml`` (mode ``0600``)."""
    path = path if path is not None else credentials_path()
    doc = _read_credentials(path)
    entry = tomlkit.table()
    entry["token"] = token
    if email is not None:
        entry["email"] = email
    if token_id is not None:
        entry["token_id"] = token_id
    _servers_table(doc)[origin] = entry
    _write_credentials(path, doc)


def get_token(origin: str, *, path: Path | None = None) -> StoredCredential | None:
    """Return the stored credential for ``origin``, or ``None`` if absent."""
    path = path if path is not None else credentials_path()
    if not path.exists():
        return None
    servers = tomlkit.parse(path.read_text()).get("servers")
    if servers is None or origin not in servers:
        return None
    entry = servers[origin]
    return StoredCredential(
        token=str(entry["token"]),
        email=str(entry["email"]) if "email" in entry else None,
        token_id=str(entry["token_id"]) if "token_id" in entry else None,
    )


def delete_token(origin: str, *, path: Path | None = None) -> None:
    """Remove ``origin`` from ``credentials.toml`` (a no-op if not present)."""
    path = path if path is not None else credentials_path()
    if not path.exists():
        return
    doc = tomlkit.parse(path.read_text())
    servers = doc.get("servers")
    if servers is None or origin not in servers:
        return
    del servers[origin]
    _write_credentials(path, doc)
