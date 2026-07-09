"""Render the v4 → v5 migration guide from the CLI compat-shim table.

**Single source of truth (spec §12).** The migration guide is *never* hand
edited: it is rendered from ``spotdl_cli``'s module-level ``V4_FLAG_TABLE`` (the
argv-preprocessor translation table) plus the ``.spotdl`` v4 → v2 field table.
Both are owned by Plan 8's ``apps/cli`` shim; this script is only their
Markdown projection, wired into the docs build via ``mkdocs-gen-files`` and
drift-checked in CI (mirroring Plan 8's generated-client in-sync guard).

Modes
-----
* **Under ``mkdocs-gen-files``** (the docs build): the module is executed by the
  plugin while a :class:`FilesEditor` context is active; it writes the rendered
  Markdown into the *virtual* docs tree at ``migration/v4-to-v5.md`` (shadowing
  the committed copy, which is what mkdocs actually serves).
* **Standalone** ``python scripts/docs/gen_migration_guide.py``: writes the
  committed ``docs/migration/v4-to-v5.md``.
* **``--check``**: re-renders in memory and fails (exit 1) if the committed file
  drifts — the ``make docs-check`` / CI guard.

The Plan 8 interface (documented, depended upon)
------------------------------------------------
``from spotdl_cli.shim import V4_FLAG_TABLE`` — an iterable of *flag rows*, each
exposing (attribute, mapping-key, or positional 3-tuple, in that resolution
order):

* ``v4_flag`` — the v4 ``arguments.py`` flag, e.g. ``"--scan-for-songs"``;
* ``kind`` — one of ``SAME`` / ``RENAME`` / ``SOFT-DROP`` / ``DROP``;
* ``v5_form`` — the "v5 form / pointer" Markdown cell (may embed a note).

``from spotdl_cli.shim import SPOTDL_FIELD_TABLE`` — the ``.spotdl`` v4 → v2
field table: an iterable of rows exposing ``v4_field`` / ``v2_field`` / ``note``.

**Until Plan 8 lands** (``V4_FLAG_TABLE`` does not exist yet), this script falls
back to the clearly-marked ``_PLACEHOLDER_*`` inputs below — faithful copies of
Plan 8 CONTRACT F/G — so the committed guide is complete and the docs build is
green. When Plan 8 lands, the real table is imported automatically, the
committed guide drifts, and ``make docs-check`` fails until it is regenerated
(the intended handoff). ``scripts/docs/tests/test_gen_migration_guide.py``
carries a test that activates the moment the real table is importable.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Committed output path (relative to repo root) and the docs-tree path used by
# the mkdocs-gen-files virtual write.
_DOC_RELPATH = "migration/v4-to-v5.md"
_COMMITTED_PATH = _REPO_ROOT / "docs" / _DOC_RELPATH

_KIND_ORDER = ("SAME", "RENAME", "SOFT-DROP", "DROP")
_KIND_HEADINGS = {
    "SAME": "Unchanged flags (SAME)",
    "RENAME": "Renamed flags (RENAME)",
    "SOFT-DROP": "Obsolete no-ops (SOFT-DROP)",
    "DROP": "Removed flags (DROP)",
}
_KIND_BLURBS = {
    "SAME": "These flags keep the same name and meaning — copy them across verbatim.",
    "RENAME": (
        "These flags were renamed. `spotdl` auto-translates a v4 invocation and "
        "prints a one-line note; update your scripts to the v5 form."
    ),
    "SOFT-DROP": (
        "These flags became no-ops (their behavior is automatic in v5). They are "
        "stripped with a warning and execution continues."
    ),
    "DROP": (
        "These flags named behavior the client no longer performs. `spotdl` "
        "fails fast with a pointer to the replacement."
    ),
}


@dataclass(frozen=True)
class FlagRow:
    """A normalized ``V4_FLAG_TABLE`` row (independent of the source shape)."""

    v4_flag: str
    kind: str
    v5_form: str


@dataclass(frozen=True)
class FieldRow:
    """A normalized ``.spotdl`` v4 → v2 field-table row."""

    v4_field: str
    v2_field: str
    note: str


# ---------------------------------------------------------------------------
# PLACEHOLDER inputs — used ONLY until Plan 8's shim lands. Faithful copies of
# Plan 8 CONTRACT F (flag table) and CONTRACT G (.spotdl field table). The
# `--playlist-retain-track-cover` cell is carried VERBATIM (CONTRACT F).
# ---------------------------------------------------------------------------
_PLAYLIST_RETAIN_TRACK_COVER_NOTE = (
    "`--retain-track-cover` — **documented behavior gap:** v4's flag *also* set "
    "each track's album name to the playlist name; v5's `--retain-track-cover` "
    "only retains per-track cover art. To get the album-name override too, "
    "combine with `--playlist-numbering`. The rendered migration guide carries "
    "this note verbatim."
)

_PLACEHOLDER_FLAG_TABLE: tuple[tuple[str, str, str], ...] = (
    ("--output", "SAME", "`--output` (output template incl. dir)"),
    ("--format", "SAME", "`--format`"),
    ("--bitrate", "SAME", "`--bitrate`"),
    ("--overwrite", "SAME", "`--overwrite`"),
    ("--restrict", "SAME", "`--restrict` (`--restrict` with no value → `--restrict strict`)"),
    ("--m3u", "SAME", "`--m3u` (optional value; default `{list[0]}.m3u8`)"),
    ("--save-file", "SAME", "`--save-file`"),
    ("--archive", "SAME", "`--archive`"),
    ("--cookie-file", "SAME", "`--cookie-file`"),
    ("--proxy", "SAME", "`--proxy`"),
    ("--threads", "SAME", "`--threads` (download concurrency)"),
    ("--ffmpeg", "SAME", "`--ffmpeg` (executable path)"),
    ("--ffmpeg-args", "SAME", "`--ffmpeg-args`"),
    ("--yt-dlp-args", "SAME", "`--yt-dlp-args`"),
    ("--sponsor-block", "SAME", "`--sponsor-block`"),
    ("--generate-lrc", "SAME", "`--generate-lrc`"),
    ("--save-errors", "SAME", "`--save-errors`"),
    ("--print-errors", "SAME", "`--print-errors`"),
    ("--skip-explicit", "SAME", "`--skip-explicit`"),
    ("--detect-formats", "SAME", "`--detect-formats`"),
    ("--max-filename-length", "SAME", "`--max-filename-length`"),
    ("--id3-separator", "SAME", "`--id3-separator`"),
    ("--playlist-numbering", "SAME", "`--playlist-numbering`"),
    ("--add-unavailable", "SAME", "`--add-unavailable`"),
    ("--create-skip-file", "SAME", "`--create-skip-file`"),
    ("--respect-skip-file", "SAME", "`--respect-skip-file`"),
    ("--log-level", "SAME", "`--log-level`"),
    ("--scan-for-songs", "RENAME", "`--scan`"),
    ("--playlist-retain-track-cover", "RENAME", _PLAYLIST_RETAIN_TRACK_COVER_NOTE),
    ("--sync-without-deleting", "RENAME", "`--no-delete` (on `sync`)"),
    ("--sync-remove-lrc", "RENAME", "`--remove-lrc` (on `sync`)"),
    ("--redownload", "RENAME", "`--redownload` (on `meta`; kept)"),
    ("--skip-album-art", "RENAME", "`--skip-album-art` (on `meta`; kept)"),
    ("--force-update-metadata", "RENAME", "`--overwrite metadata`"),
    ("--host / --port", "SAME", "`--host` / `--port` (on `web`/`server`)"),
    ("--download-ffmpeg", "RENAME", "`spotdl ffmpeg download` (operation → subcommand)"),
    ("--generate-config", "RENAME", "`spotdl config edit`"),
    (
        "--version / -v",
        "SAME",
        "`--version` (global eager flag printing the version; `spotdl version` also works)",
    ),
    (
        "--config",
        "SOFT-DROP",
        "config is auto-loaded from `config.toml` in v5 — the flag is unnecessary and was ignored",
    ),
    (
        "--audio",
        "DROP",
        "audio-source matching is server-side now; the server ranks providers and community "
        "voting refines matches",
    ),
    (
        "--lyrics",
        "DROP",
        "lyrics providers are server-side; use `--generate-lrc` for `.lrc`, and vote on lyrics "
        "in the TUI/web",
    ),
    (
        "--genius-access-token",
        "DROP",
        "lyrics are fetched server-side; no client token needed",
    ),
    (
        "--client-id / --client-secret / --auth-token / --user-auth",
        "DROP",
        "Spotify credentials are no longer client-side; the community server serves metadata "
        "(self-host: set operator creds on the server)",
    ),
    (
        "--cache-path / --no-cache / --use-cache-file",
        "DROP",
        "metadata caching is server-side (permanent snapshot cache)",
    ),
    (
        "--headless / --max-retries",
        "DROP",
        "Spotify auth/retry is a server concern now",
    ),
    (
        "--search-query / --dont-filter-results / --only-verified-results / --album-type",
        "DROP",
        "matching/search tuning is server-side (versioned matcher); community voting refines "
        "results",
    ),
    ("--ytm-data", "DROP", "metadata source selection is server-side"),
    (
        "--fetch-albums / --ignore-albums",
        "DROP",
        "resolve albums explicitly (`spotdl download album:<name>` / album URL)",
    ),
    (
        "--preload",
        "SOFT-DROP",
        "downloads are queued and prefetched automatically in v5 — the flag was ignored",
    ),
    (
        "--simple-tui",
        "DROP",
        "the plain Rich progress is the default non-TTY renderer; there is no separate simple TUI",
    ),
    ("--log-format", "DROP", "custom logging formats were removed; use `--log-level`"),
    (
        "--profile / --check-for-updates",
        "DROP",
        "removed (use your OS profiler / `pip install -U spotdl`)",
    ),
    (
        "--web-gui-repo / --web-gui-location / --force-update-gui",
        "DROP",
        "the web UI is bundled in the package now — no runtime GitHub fetch (spec §8)",
    ),
    (
        "--keep-alive / --keep-sessions / --web-use-output-dir / --allowed-origins",
        "DROP",
        "web-server session model changed; run `spotdl web` (embedded, single-user) or "
        "`spotdl server --mode selfhost`",
    ),
    (
        "--enable-tls / --cert-file / --key-file / --ca-file",
        "DROP",
        "terminate TLS at a reverse proxy (see the self-host deploy docs / `deploy/`)",
    ),
)

_PLACEHOLDER_FIELD_TABLE: tuple[tuple[str, str, str], ...] = (
    (
        "(top-level bare array)",
        "`SaveFileV2.songs[]`",
        "v4's `.spotdl` was a bare JSON array of `Song.asdict`; v5 wraps it in "
        "`{version: 2, ...}`.",
    ),
    ("`name`", "`SaveFileSong.name`", "Track title, copied through."),
    ("`artists`", "`SaveFileSong.artists`", "Artist list, copied through."),
    (
        "`duration`",
        "`SaveFileSong.duration`",
        "v4 stored **seconds**; v5 stores **milliseconds** (s → ms).",
    ),
    (
        "`download_url`",
        "`SaveFileSong.match.url`",
        "Moved under the per-track `match`; audio-target URL.",
    ),
    (
        "`list_name` / `album_name`",
        "`SaveFileV2.kind` + `.name`",
        "Used to infer `kind` (`playlist`/`album`/`single`) and the collection `name`.",
    ),
    (
        "(audio host of `download_url`)",
        "`SaveFileSong.match.provider`",
        "Inferred from the URL host (`youtu.be`→`youtube`, "
        "`music.youtube.com`→`youtube-music`, `soundcloud.com`→`soundcloud`, "
        "`*.bandcamp.com`→`bandcamp`, unknown→`youtube`) — never a validation failure.",
    ),
    (
        "(file mtime)",
        "`SaveFileV2.created_at`",
        "v4 files carry no timestamp; the loader uses the file mtime (ISO-8601).",
    ),
    (
        "(none)",
        "`SaveFileV2.matcher_version`",
        "`null` for migrated v4 files (no matcher provenance existed).",
    ),
    ("(none)", "`SaveFileV2.source`", "`null` — v4 files record no originating URL."),
)


# ---------------------------------------------------------------------------
# Row normalization — tolerant of attribute / mapping / positional shapes so the
# projection survives whatever concrete container Plan 8 chooses.
# ---------------------------------------------------------------------------
def _field(row: object, name: str, index: int) -> str:
    if isinstance(row, Mapping):
        return str(row[name])
    if hasattr(row, name):
        return str(getattr(row, name))
    if isinstance(row, Sequence) and not isinstance(row, str | bytes):
        return str(row[index])
    raise TypeError(f"cannot read field {name!r} from row {row!r}")


def _normalize_flag_row(row: object) -> FlagRow:
    return FlagRow(
        v4_flag=_field(row, "v4_flag", 0),
        kind=_field(row, "kind", 1),
        v5_form=_field(row, "v5_form", 2),
    )


def _normalize_field_row(row: object) -> FieldRow:
    return FieldRow(
        v4_field=_field(row, "v4_field", 0),
        v2_field=_field(row, "v2_field", 1),
        note=_field(row, "note", 2),
    )


def _import_shim_attr(name: str) -> Any:
    """Return ``spotdl_cli.shim.<name>`` if importable, else ``None``.

    Uses a dynamic import (rather than a static ``from … import``) so the
    projection type-checks cleanly before Plan 8's ``spotdl_cli.shim`` module
    exists, and needs no ``type: ignore`` once it does.
    """
    import importlib

    try:
        module = importlib.import_module("spotdl_cli.shim")
    except ImportError:
        return None
    return getattr(module, name, None)


def load_flag_table() -> tuple[list[FlagRow], bool]:
    """Return ``(rows, using_placeholder)``.

    Imports the real ``spotdl_cli.shim.V4_FLAG_TABLE`` when available; otherwise
    falls back to the in-file placeholder (Plan 8 not landed yet).
    """
    table = _import_shim_attr("V4_FLAG_TABLE")
    if table is None:
        return [_normalize_flag_row(r) for r in _PLACEHOLDER_FLAG_TABLE], True
    return [_normalize_flag_row(r) for r in table], False


def load_field_table() -> tuple[list[FieldRow], bool]:
    """Return ``(rows, using_placeholder)`` for the ``.spotdl`` field table."""
    table = _import_shim_attr("SPOTDL_FIELD_TABLE")
    if table is None:
        return [_normalize_field_row(r) for r in _PLACEHOLDER_FIELD_TABLE], True
    return [_normalize_field_row(r) for r in table], False


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _render_flag_group(kind: str, rows: Iterable[FlagRow]) -> list[str]:
    group = [r for r in rows if r.kind.upper() == kind]
    if not group:
        return []
    lines = [f"### {_KIND_HEADINGS[kind]}", "", _KIND_BLURBS[kind], ""]
    lines += ["| v4 flag | v5 form / pointer |", "|---|---|"]
    for r in group:
        lines.append(f"| `{r.v4_flag}` | {r.v5_form} |")
    lines.append("")
    return lines


def render_markdown(
    flag_rows: list[FlagRow] | None = None,
    field_rows: list[FieldRow] | None = None,
    *,
    placeholder: bool | None = None,
) -> str:
    """Render the full migration guide Markdown from the two tables."""
    if flag_rows is None:
        flag_rows, flag_ph = load_flag_table()
    else:
        flag_ph = False
    if field_rows is None:
        field_rows, field_ph = load_field_table()
    else:
        field_ph = False
    is_placeholder = placeholder if placeholder is not None else (flag_ph or field_ph)

    lines: list[str] = [
        "<!-- GENERATED FILE — do not edit by hand.",
        "     Source: spotdl_cli.shim (V4_FLAG_TABLE + SPOTDL_FIELD_TABLE), rendered by",
        "     scripts/docs/gen_migration_guide.py. Run `make docs` to regenerate. -->",
        "",
        "# Migrating from spotDL v4",
        "",
        "spotDL v5 is a ground-up rewrite (server + CLI/TUI + web UI). Most everyday "
        "`spotdl` commands work exactly as before — `spotdl <url>` still downloads. The "
        "CLI ships a **compat shim** that translates a v4 invocation on the fly: renamed "
        "flags are rewritten (with a one-line note), obsolete no-ops are ignored (with a "
        "warning), and flags whose behavior genuinely moved server-side fail fast with a "
        "pointer to the replacement.",
        "",
        "> Stable v4 remains installed by a plain `pip install spotdl` until v5 reaches GA. "
        "This guide is generated from the CLI's translation table, so it is always in sync "
        "with what the shim actually does.",
        "",
        "## What changed at a glance",
        "",
        "- **Metadata, search and matching are server-side.** No Spotify client ID/secret "
        "on your machine — the community server (or your self-hosted one) serves metadata "
        "and ranks audio matches; community voting refines them.",
        "- **The web UI is bundled** in the package (spec §8) — no runtime GitHub fetch.",
        "- **TLS terminates at a reverse proxy** for self-hosting (see the "
        "[self-hosting docs](../self-hosting/reverse-proxy.md)), not via client flags.",
        "- **`.spotdl` files are auto-migrated** from v4's bare array to the v2 format on load.",
        "",
        "## Flag translation table",
        "",
        "Every v4 `arguments.py` flag is accounted for below, grouped by how the shim treats it.",
        "",
    ]

    for kind in _KIND_ORDER:
        lines += _render_flag_group(kind, flag_rows)

    lines += [
        "## `.spotdl` file auto-migration",
        "",
        "v4's `.spotdl` save file was a bare JSON array of `Song.asdict`. v5 uses the "
        "structured **v2** format (`{version: 2, kind, name, source, created_at, "
        "matcher_version, songs: [...]}`). `spotdl` detects a v4 file by its top-level "
        "JSON type (a list ⇒ v4) and migrates it in memory on load; the migrated form is "
        "only written back to disk when a command emits a new `.spotdl` (then it is v2).",
        "",
        "| v4 field | v5 (`.spotdl` v2) field | Notes |",
        "|---|---|---|",
    ]
    for fr in field_rows:
        lines.append(f"| {fr.v4_field} | {fr.v2_field} | {fr.note} |")
    lines.append("")

    if is_placeholder:
        lines += [
            "<!-- NOTE: rendered from the PLACEHOLDER tables baked into",
            "     scripts/docs/gen_migration_guide.py because spotdl_cli.shim.V4_FLAG_TABLE",
            "     (Plan 8) is not importable yet. When Plan 8 lands, `make docs` regenerates",
            "     this file from the real table and the placeholder note disappears. -->",
            "",
        ]

    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def _write_committed(content: str) -> None:
    _COMMITTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    _COMMITTED_PATH.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the v4→v5 migration guide.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail (exit 1) if the committed guide differs from a fresh render",
    )
    args = parser.parse_args(argv)

    content = render_markdown()
    if args.check:
        current = _COMMITTED_PATH.read_text(encoding="utf-8") if _COMMITTED_PATH.exists() else ""
        if current != content:
            sys.stderr.write(f"{_DOC_RELPATH} is stale — run `make docs` to regenerate it.\n")
            return 1
        return 0

    _write_committed(content)
    return 0


def _under_gen_files_build() -> bool:
    """True only while the mkdocs-gen-files plugin's FilesEditor context is active.

    Distinguishes "executed by the docs build" from "imported by a test": the
    plugin enters a :class:`FilesEditor` (setting ``_current``) before running
    this script, so a live ``_current`` means we should write into the virtual
    docs tree rather than touch disk.
    """
    try:
        from mkdocs_gen_files.editor import FilesEditor
    except ImportError:
        return False
    return FilesEditor._current is not None


if __name__ == "__main__":
    raise SystemExit(main())
elif _under_gen_files_build():
    import mkdocs_gen_files

    with mkdocs_gen_files.open(_DOC_RELPATH, "w") as _f:
        _f.write(render_markdown())
    mkdocs_gen_files.set_edit_path(_DOC_RELPATH, "scripts/docs/gen_migration_guide.py")
