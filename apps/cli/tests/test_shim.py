"""Table-driven tests for the v4 → v5 compat shim (CONTRACT F).

Every row of :data:`spotdl_cli.shim.V4_FLAG_TABLE` is exercised by its kind
(SAME / RENAME / SOFT-DROP / DROP), plus the operation-mapping rules and the
``main()`` wiring (notice/error rendering and the ``USAGE`` exit on a DROP).
"""

from __future__ import annotations

import pytest
from spotdl_cli.errors import ExitCode
from spotdl_cli.shim import (
    V4_FLAG_TABLE,
    Dropped,
    FlagSpec,
    Rewritten,
    Unchanged,
    drop_message,
    softdrop_warning,
    translate_v4_argv,
)


def _notes(notices: list[str]) -> list[str]:
    return [n for n in notices if n.startswith("note:")]


def _warnings(notices: list[str]) -> list[str]:
    return [n for n in notices if n.startswith("warning:")]


# --- Completeness: every v4 arguments.py flag is in the table ---------------
def test_every_v4_flag_is_covered() -> None:
    """The union of covered flags equals v4's full ``arguments.py`` surface."""
    covered = {flag for spec in V4_FLAG_TABLE for flag in spec.flags}
    v4_flags = {
        # main
        "--audio",
        "--lyrics",
        "--genius-access-token",
        "--config",
        "--search-query",
        "--dont-filter-results",
        "--album-type",
        "--only-verified-results",
        # spotify
        "--user-auth",
        "--client-id",
        "--client-secret",
        "--auth-token",
        "--cache-path",
        "--no-cache",
        "--max-retries",
        "--headless",
        "--use-cache-file",
        # ffmpeg
        "--ffmpeg",
        "--threads",
        "--bitrate",
        "--ffmpeg-args",
        # output
        "--format",
        "--save-file",
        "--preload",
        "--output",
        "--m3u",
        "--cookie-file",
        "--overwrite",
        "--restrict",
        "--print-errors",
        "--save-errors",
        "--sponsor-block",
        "--archive",
        "--playlist-numbering",
        "--playlist-retain-track-cover",
        "--scan-for-songs",
        "--fetch-albums",
        "--id3-separator",
        "--ytm-data",
        "--add-unavailable",
        "--generate-lrc",
        "--force-update-metadata",
        "--sync-without-deleting",
        "--max-filename-length",
        "--yt-dlp-args",
        "--detect-formats",
        "--redownload",
        "--skip-album-art",
        "--ignore-albums",
        "--skip-explicit",
        "--proxy",
        "--create-skip-file",
        "--respect-skip-file",
        "--sync-remove-lrc",
        # web
        "--host",
        "--port",
        "--keep-alive",
        "--allowed-origins",
        "--web-use-output-dir",
        "--keep-sessions",
        "--force-update-gui",
        "--web-gui-repo",
        "--web-gui-location",
        "--enable-tls",
        "--cert-file",
        "--key-file",
        "--ca-file",
        # misc
        "--log-level",
        "--simple-tui",
        "--log-format",
        # other
        "--download-ffmpeg",
        "--generate-config",
        "--check-for-updates",
        "--profile",
        "--version",
        "-v",
    }
    assert covered == v4_flags


def test_no_duplicate_flag_across_rows() -> None:
    seen: set[str] = set()
    for spec in V4_FLAG_TABLE:
        for flag in spec.flags:
            assert flag not in seen, f"{flag} appears in two rows"
            seen.add(flag)


def test_every_row_kind_is_valid() -> None:
    for spec in V4_FLAG_TABLE:
        assert spec.kind in {"SAME", "RENAME", "SOFT-DROP", "DROP"}
        if spec.kind == "RENAME":
            assert spec.rename_to, f"{spec.v4_flag} RENAME needs rename_to"
        if spec.kind in {"DROP", "SOFT-DROP"}:
            assert spec.pointer, f"{spec.v4_flag} needs a pointer"


def test_common_surface_is_at_least_25_flags() -> None:
    """CONTRACT F: ≥25 commonly-used SAME/RENAME flags."""
    common = [
        flag for spec in V4_FLAG_TABLE if spec.kind in {"SAME", "RENAME"} for flag in spec.flags
    ]
    assert len(common) >= 25


# --- Table-driven: one parametrization per (row, flag) ----------------------
def _rows() -> list[tuple[FlagSpec, str]]:
    return [(spec, flag) for spec in V4_FLAG_TABLE for flag in spec.flags]


@pytest.mark.parametrize("spec,flag", _rows(), ids=lambda v: v if isinstance(v, str) else "")
def test_table_row(spec: FlagSpec, flag: str) -> None:
    value = "V" if spec.takes_value else None

    if spec.operation:
        # Operation-flags become the leading subcommand and emit the note.
        result = translate_v4_argv([flag])
        assert isinstance(result, Rewritten)
        assert result.argv == list(spec.rename_to)
        assert len(_notes(result.notices)) == 1
        return

    argv = ["download", "x", flag] + ([value] if value else [])

    if spec.kind == "SAME":
        result = translate_v4_argv(argv)
        # Already valid v5 → unchanged, and no translation note.
        assert isinstance(result, Unchanged)

    elif spec.kind == "RENAME":
        result = translate_v4_argv(argv)
        if tuple(spec.rename_to) == (flag,):
            # Kept-same rename (name unchanged, semantics relocated): no rewrite.
            assert isinstance(result, Unchanged)
        else:
            assert isinstance(result, Rewritten)
            assert flag not in result.argv
            for tok in spec.rename_to:
                assert tok in result.argv
            assert len(_notes(result.notices)) == 1  # real rewrite → one note

    elif spec.kind == "SOFT-DROP":
        result = translate_v4_argv(argv)
        assert isinstance(result, Rewritten)
        assert result.argv == ["download", "x"]  # flag (and value) stripped
        assert _warnings(result.notices) == [softdrop_warning(flag, spec.pointer)]
        assert _notes(result.notices) == []  # a no-op strip is not a translation

    elif spec.kind == "DROP":
        result = translate_v4_argv(argv)
        assert isinstance(result, Dropped)
        assert result.flag == flag
        assert result.pointer == spec.pointer


# --- Kept-same RENAME rows leave the argv untouched -------------------------
def test_kept_rename_is_unchanged() -> None:
    for flag in ("--redownload", "--skip-album-art"):
        result = translate_v4_argv(["meta", "x", flag])
        assert isinstance(result, Unchanged)


# --- Operation mapping ------------------------------------------------------
def test_explicit_download_is_unchanged() -> None:
    assert isinstance(translate_v4_argv(["download", "x"]), Unchanged)


def test_bare_query_gets_download_without_note() -> None:
    result = translate_v4_argv(["x"])
    assert isinstance(result, Rewritten)
    assert result.argv == ["download", "x"]
    assert result.notices == []  # sugar, not a translation


def test_v5_native_subcommands_pass_through_unsugared() -> None:
    # A leading v5-native subcommand is a real invocation, not a download query, so
    # it must survive the shim untouched (`spotdl tui`, `spotdl auth login`, ...).
    for argv in (["tui"], ["tui", "--offline"], ["auth", "login"], ["config", "set", "k", "v"]):
        assert isinstance(translate_v4_argv(argv), Unchanged), argv


def test_download_ffmpeg_becomes_subcommand() -> None:
    result = translate_v4_argv(["--download-ffmpeg"])
    assert isinstance(result, Rewritten)
    assert result.argv == ["ffmpeg", "download"]
    assert len(_notes(result.notices)) == 1


def test_generate_config_becomes_subcommand() -> None:
    result = translate_v4_argv(["--generate-config"])
    assert isinstance(result, Rewritten)
    assert result.argv == ["config", "edit"]


def test_save_with_save_file_is_unchanged() -> None:
    result = translate_v4_argv(["save", "x", "--save-file", "f.spotdl"])
    assert isinstance(result, Unchanged)


def test_web_operation_passes_through() -> None:
    assert isinstance(translate_v4_argv(["web", "--host", "0.0.0.0"]), Unchanged)


def test_empty_argv_is_unchanged() -> None:
    assert isinstance(translate_v4_argv([]), Unchanged)


def test_version_flag_passes_through() -> None:
    assert isinstance(translate_v4_argv(["--version"]), Unchanged)
    assert isinstance(translate_v4_argv(["-v"]), Unchanged)


# --- A real, mixed v4 line: drops win and fail fast -------------------------
def test_mixed_v4_line_drops_on_client_id() -> None:
    argv = ["download", "url", "--output", "{artist}", "--scan-for-songs", "--client-id", "X"]
    result = translate_v4_argv(argv)
    assert isinstance(result, Dropped)
    assert result.flag == "--client-id"
    assert "Spotify credentials are no longer client-side" in result.pointer


def test_rename_rewrites_and_notes_once() -> None:
    result = translate_v4_argv(["download", "x", "--scan-for-songs"])
    assert isinstance(result, Rewritten)
    assert result.argv == ["download", "x", "--scan"]
    assert len(_notes(result.notices)) == 1


def test_soft_drop_strips_and_continues() -> None:
    result = translate_v4_argv(["download", "x", "--config"])
    assert isinstance(result, Rewritten)
    assert result.argv == ["download", "x"]
    assert len(_warnings(result.notices)) == 1


def test_same_value_flag_value_not_reparsed() -> None:
    # A value that happens to look like a DROP flag must not trip a false drop.
    result = translate_v4_argv(["download", "x", "--output", "--audio"])
    assert isinstance(result, Unchanged)


# --- main() wiring: notices/errors + exit codes -----------------------------
def test_main_exits_usage_on_drop(capsys: pytest.CaptureFixture[str]) -> None:
    from spotdl_cli.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["download", "x", "--audio", "youtube"])
    assert exc.value.code == ExitCode.USAGE
    err = capsys.readouterr().err
    assert err.startswith("error: `--audio` was removed in spotdl v5.")


def test_drop_message_format() -> None:
    assert drop_message("--audio", "gone.") == "error: `--audio` was removed in spotdl v5. gone."
