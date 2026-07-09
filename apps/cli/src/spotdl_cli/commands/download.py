"""``spotdl download`` — submit queries to the embedded engine with WS progress.

Exposes the full Plan 4 download surface (spec §7): per-request knobs ride on the
``DownloadSubmitRequest`` (via :class:`~spotdl_cli.views.DownloadSubmit`), while
engine/session knobs route to the embedded server's ``SPOTDL_*`` ``Settings``
(Seam 1). Downloads always run against the **embedded** transport (CONTRACT:
download flow). Progress streams over one WS code path; per-track failures are
collected and summarized, and the process exit code follows CONTRACT E.

Cross-track seam (noted): building the embedded client is delegated to
:func:`_open_client`, which wires ``SpotdlClient.from_config`` (Plan 8 Tasks 4/5)
over ``load_config`` (Task 3). Those land on sibling tracks; tests patch
``_open_client`` with a fake client, and option resolution is pure and directly
tested. Bare-query sugar (``spotdl <url>`` → ``download``) is finalized in Task 13.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from spotdl_cli.client import SpotdlClient
from spotdl_cli.errors import ApiError, ExitCode, render_api_error
from spotdl_cli.progress import (
    FailedJob,
    RichProgressReporter,
    consume_progress,
    render_summary,
    write_error_report,
)
from spotdl_cli.savefile import dump_save_file, load_save_file

_FORMATS = ["mp3", "m4a", "flac", "ogg", "opus", "wav"]
_OVERWRITE = ["force", "skip", "metadata"]
_RESTRICT = ["strict", "ascii", "none"]


@dataclass(frozen=True)
class ResolvedDownload:
    """A fully-resolved download invocation: what to submit + how to boot embedded."""

    submits: list[Any]  # list[DownloadSubmit]; Any avoids a views import cycle at edges
    settings_env: dict[str, str]
    save_file: Path | None
    save_errors: Path | None
    print_errors: bool
    offline: bool
    submit_failures: list[FailedJob] = field(default_factory=list)


def split_output_template(output: str) -> tuple[str | None, str]:
    """Split a v4 ``-o`` value into (library_dir_override, template).

    Any literal directory prefix *before the first template variable* is peeled
    off as the engine output root (routed to ``SPOTDL_LIBRARY_PATH``); the rest is
    the output template. ``-o "~/Music/{artists}/{title}.{output-ext}"`` →
    (``~/Music``, ``{artists}/{title}.{output-ext}``). A value with no directory
    prefix keeps the whole thing as the template and overrides nothing.
    """
    brace = output.find("{")
    if brace == -1:
        return None, output
    slash = output.rfind("/", 0, brace)
    if slash == -1:
        return None, output
    library = output[:slash]
    template = output[slash + 1 :]
    return (library or None), template


def _cfg(cfg: Any, name: str) -> Any:
    return getattr(cfg, name, None) if cfg is not None else None


def _pick(flag: Any, cfg: Any, name: str) -> Any:
    """Precedence: an explicit flag wins, else the config value, else ``None``.

    ``None`` means "leave it to the embedded server's configured default" — for
    per-request fields that is server-side, for engine knobs it is the ``Settings``
    default / the caller's ambient ``SPOTDL_*`` env.
    """
    if flag is not None:
        return flag
    return _cfg(cfg, name)


def _query_to_submits(query: str, per_request: dict[str, Any]) -> list[Any]:
    """One query → one submit, except a ``.spotdl`` file → one submit per song."""
    from spotdl_cli.views import DownloadSubmit

    path = Path(query)
    if query.lower().endswith(".spotdl") and path.is_file():
        save = load_save_file(path)
        submits: list[Any] = []
        for song in save.songs:
            ref = song.track_url or (
                f"{song.artist or (song.artists[0] if song.artists else '')} - {song.name}".strip(
                    " -"
                )
            )
            submits.append(DownloadSubmit(query=ref, **per_request))
        return submits
    return [DownloadSubmit(query=query, **per_request)]


def _resolve(  # noqa: PLR0913 - a wide option surface is the contract here
    queries: list[str],
    *,
    cfg: Any = None,
    output: str | None = None,
    output_format: str | None = None,
    bitrate: str | None = None,
    overwrite: str | None = None,
    restrict: str | None = None,
    m3u: str | None = None,
    save_file: Path | None = None,
    archive: Path | None = None,
    embed_lyrics: bool = True,
    generate_lrc: bool = False,
    sponsor_block: bool = False,
    threads: int | None = None,
    cookie_file: Path | None = None,
    proxy: str | None = None,
    ffmpeg: str | None = None,
    ffmpeg_args: str | None = None,
    ytdlp_args: str | None = None,
    detect_formats: list[str] | None = None,
    max_filename_length: int | None = None,
    id3_separator: str | None = None,
    skip_explicit: bool | None = None,
    playlist_numbering: bool | None = None,
    retain_track_cover: bool | None = None,
    scan: bool | None = None,
    add_unavailable: bool | None = None,
    create_skip_file: bool | None = None,
    respect_skip_file: bool | None = None,
    save_errors: Path | None = None,
    print_errors: bool = False,
    offline: bool = False,
) -> ResolvedDownload:
    """Pure option → (submits + embedded ``Settings`` env) resolution (CONTRACT)."""
    # -o splits into a library override + the template; else config values apply.
    library_override: str | None = _cfg(cfg, "output_dir")
    template = _pick(output, cfg, "output_template")
    if output is not None:
        lib, template = split_output_template(output)
        if lib is not None:
            library_override = lib

    generate_m3u = m3u is not None
    per_request: dict[str, Any] = {
        "output_format": _pick(output_format, cfg, "format"),
        "bitrate": _pick(bitrate, cfg, "bitrate"),
        "output_template": str(template) if template is not None else None,
        "overwrite": _pick(overwrite, cfg, "overwrite"),
        "embed_lyrics": embed_lyrics,
        "generate_lrc": generate_lrc,
        "generate_m3u": generate_m3u,
        "m3u_template": m3u if m3u else None,
        "generate_save_file": save_file is not None,
        "sponsor_block": sponsor_block,
        "update_archive": archive is not None,
    }

    submits: list[Any] = []
    for query in queries:
        submits.extend(_query_to_submits(query, per_request))

    env = _settings_env(
        cfg=cfg,
        library_override=library_override,
        restrict=restrict,
        archive=archive,
        threads=threads,
        cookie_file=cookie_file,
        proxy=proxy,
        ffmpeg=ffmpeg,
        ffmpeg_args=ffmpeg_args,
        ytdlp_args=ytdlp_args,
        detect_formats=detect_formats,
        max_filename_length=max_filename_length,
        id3_separator=id3_separator,
        skip_explicit=skip_explicit,
        playlist_numbering=playlist_numbering,
        retain_track_cover=retain_track_cover,
        scan=scan,
        add_unavailable=add_unavailable,
        create_skip_file=create_skip_file,
        respect_skip_file=respect_skip_file,
    )
    return ResolvedDownload(
        submits=submits,
        settings_env=env,
        save_file=save_file,
        save_errors=save_errors,
        print_errors=print_errors,
        offline=offline,
    )


def _settings_env(*, cfg: Any, library_override: str | None, **flags: Any) -> dict[str, str]:
    """Map engine/session knobs to the embedded server's ``SPOTDL_*`` env (Seam 1).

    Note (documented, not a bug): a value that comes from the *config file's
    defaults* (e.g. ``threads`` → ``SPOTDL_DOWNLOAD_CONCURRENCY``) still lands in
    this dict, and ``_open_client`` writes it over any same-named ``SPOTDL_*`` the
    caller already exported. That is the intended CONTRACT D precedence (CLI/config
    outrank ambient env for the embedded engine), but it does mean a bare
    ``SPOTDL_DOWNLOAD_CONCURRENCY`` in the environment is shadowed by the config
    default rather than honored.
    """
    env: dict[str, str] = {}

    def put(var: str, value: Any) -> None:
        if value is not None:
            env[var] = str(value)

    def put_bool(var: str, value: Any) -> None:
        if value is not None:
            env[var] = "true" if value else "false"

    put("SPOTDL_LIBRARY_PATH", library_override)
    put("SPOTDL_DOWNLOAD_RESTRICT", _pick(flags["restrict"], cfg, "restrict"))
    put("SPOTDL_DOWNLOAD_CONCURRENCY", _pick(flags["threads"], cfg, "threads"))
    put("SPOTDL_DOWNLOAD_COOKIE_FILE", _pick(flags["cookie_file"], cfg, "cookie_file"))
    put("SPOTDL_DOWNLOAD_PROXY", _pick(flags["proxy"], cfg, "proxy"))
    put("SPOTDL_FFMPEG_PATH", _pick(flags["ffmpeg"], cfg, "ffmpeg"))
    put("SPOTDL_FFMPEG_ARGS", _pick(flags["ffmpeg_args"], cfg, "ffmpeg_args"))
    put("SPOTDL_YTDLP_ARGS", _pick(flags["ytdlp_args"], cfg, "ytdlp_args"))
    put("SPOTDL_DOWNLOAD_ID3_SEPARATOR", _pick(flags["id3_separator"], cfg, "id3_separator"))
    put("SPOTDL_DOWNLOAD_MAX_FILENAME_LENGTH", flags["max_filename_length"])
    if flags["detect_formats"]:
        env["SPOTDL_DOWNLOAD_DETECT_FORMATS"] = json.dumps(list(flags["detect_formats"]))
    if flags["archive"] is not None:
        env["SPOTDL_DOWNLOAD_ARCHIVE_FILE"] = str(flags["archive"])
    put_bool("SPOTDL_DOWNLOAD_SKIP_EXPLICIT", flags["skip_explicit"])
    put_bool("SPOTDL_DOWNLOAD_PLAYLIST_NUMBERING", flags["playlist_numbering"])
    put_bool("SPOTDL_DOWNLOAD_RETAIN_TRACK_COVER", flags["retain_track_cover"])
    put_bool("SPOTDL_DOWNLOAD_SCAN_EXISTING", flags["scan"])
    put_bool("SPOTDL_DOWNLOAD_ADD_UNAVAILABLE", flags["add_unavailable"])
    put_bool("SPOTDL_DOWNLOAD_CREATE_SKIP_FILE", flags["create_skip_file"])
    put_bool("SPOTDL_DOWNLOAD_RESPECT_SKIP_FILE", flags["respect_skip_file"])
    return env


@asynccontextmanager
async def _open_client(
    *, offline: bool, settings_env: dict[str, str]
) -> AsyncIterator[SpotdlClient]:
    """Boot the embedded-download client (production seam; patched in tests).

    Applies the per-invocation ``SPOTDL_*`` overrides to the process env (the
    documented precedence path, CONTRACT D) and wires the client via
    ``SpotdlClient.from_config`` over ``load_config``. Both land on sibling tracks
    (Tasks 3/4/5); until then this raises, and tests inject a fake client here.
    """
    from importlib import import_module

    os.environ.update(settings_env)
    config = import_module("spotdl_cli.config")
    cfg = config.load_config()
    async with SpotdlClient.from_config(cfg, offline=offline, need_downloads=True) as client:
        yield client


async def _drive(client: SpotdlClient, resolved: ResolvedDownload, console: Console) -> ExitCode:
    """Submit every query, stream progress, collect failures, render, return exit."""
    batch_ids: set[str] = set()
    submit_failures: list[FailedJob] = []

    async with client.progress() as stream:
        for submit in resolved.submits:
            try:
                batch = await client.submit_download(submit)
            except ApiError as exc:
                _, exit_code = _format(exc)
                if exit_code is not ExitCode.DOWNLOAD_FAILURES:
                    raise
                submit_failures.append(
                    FailedJob(
                        job_id=submit.query,
                        track_name=submit.query,
                        step="resolve",
                        error=exc.message,
                    )
                )
                continue
            batch_ids.add(batch.batch_id)

        with RichProgressReporter(console) as reporter:
            outcome = await consume_progress(stream, batch_ids, on_event=reporter.handle)
            names = reporter.names

    outcome.failed.extend(submit_failures)
    outcome.failed_count += len(submit_failures)

    if resolved.save_file is not None:
        await _write_save_file(client, batch_ids, resolved.save_file)
    if resolved.save_errors is not None:
        write_error_report(resolved.save_errors, outcome, names)

    render_summary(console, outcome, names=names, print_errors=resolved.print_errors)
    return ExitCode.DOWNLOAD_FAILURES if outcome.has_failures else ExitCode.OK


async def _write_save_file(client: SpotdlClient, batch_ids: set[str], path: Path) -> None:
    """Fetch every batch's ``.spotdl`` v2 and write one merged file (``--save-file``).

    Multiple queries (or a single ``.spotdl`` re-download, which fans out to one
    batch per song) produce multiple batches. Writing only the first would
    silently drop the rest, so all batches' songs are concatenated into a single
    :class:`SaveFileV2`. The collection-level metadata (``kind`` / ``name`` /
    ``source`` / ``created_at`` / ``matcher_version``) is taken from the first
    batch by sorted id — the plan's CONTRACT keeps ``kind`` per batch, and there
    is no single collection identity across independently-submitted batches.
    """
    from uuid import UUID

    merged: Any = None
    for batch_id in sorted(batch_ids):
        save = await client.fetch_save_file(UUID(batch_id))
        if merged is None:
            merged = save
        else:
            merged.songs.extend(save.songs)
    if merged is not None:
        path.write_text(dump_save_file(merged), encoding="utf-8")


def _format(exc: ApiError) -> tuple[str, ExitCode]:
    from spotdl_cli.errors import format_api_error

    return format_api_error(exc)


async def _run(resolved: ResolvedDownload, console: Console) -> ExitCode:
    async with _open_client(offline=resolved.offline, settings_env=resolved.settings_env) as client:
        return await _drive(client, resolved, console)


def download(  # noqa: PLR0913 - the full Plan 4 option surface (spec §7)
    queries: Annotated[
        list[str], typer.Argument(help="URLs, provider:type:id refs, free text, or *.spotdl files")
    ],
    output: Annotated[
        str | None,
        typer.Option("-o", "--output", help="Output template (may include a directory prefix)"),
    ] = None,
    output_format: Annotated[
        str | None, typer.Option("-f", "--format", help=f"Audio format ({'/'.join(_FORMATS)})")
    ] = None,
    bitrate: Annotated[str | None, typer.Option("-b", "--bitrate")] = None,
    overwrite: Annotated[
        str | None, typer.Option("--overwrite", help=f"{'/'.join(_OVERWRITE)}")
    ] = None,
    restrict: Annotated[
        str, typer.Option("--restrict", help=f"Restrict filenames ({'/'.join(_RESTRICT)})")
    ] = "none",
    m3u: Annotated[
        str | None, typer.Option("--m3u", help="Generate an m3u8 playlist (optional template)")
    ] = None,
    save_file: Annotated[
        Path | None, typer.Option("--save-file", help="Write a .spotdl v2 file")
    ] = None,
    archive: Annotated[Path | None, typer.Option("--archive", help="Download archive file")] = None,
    embed_lyrics: Annotated[bool, typer.Option("--embed-lyrics/--no-embed-lyrics")] = True,
    generate_lrc: Annotated[bool, typer.Option("--generate-lrc")] = False,
    sponsor_block: Annotated[bool, typer.Option("--sponsor-block")] = False,
    threads: Annotated[
        int | None, typer.Option("-t", "--threads", help="Download concurrency")
    ] = None,
    cookie_file: Annotated[Path | None, typer.Option("--cookie-file")] = None,
    proxy: Annotated[str | None, typer.Option("--proxy")] = None,
    ffmpeg: Annotated[str | None, typer.Option("--ffmpeg", help="ffmpeg executable path")] = None,
    ffmpeg_args: Annotated[str | None, typer.Option("--ffmpeg-args")] = None,
    ytdlp_args: Annotated[str | None, typer.Option("--yt-dlp-args")] = None,
    detect_formats: Annotated[list[str] | None, typer.Option("--detect-formats")] = None,
    max_filename_length: Annotated[int | None, typer.Option("--max-filename-length")] = None,
    id3_separator: Annotated[str | None, typer.Option("--id3-separator")] = None,
    skip_explicit: Annotated[
        bool | None, typer.Option("--skip-explicit/--no-skip-explicit")
    ] = None,
    playlist_numbering: Annotated[
        bool | None, typer.Option("--playlist-numbering/--no-playlist-numbering")
    ] = None,
    retain_track_cover: Annotated[
        bool | None, typer.Option("--retain-track-cover/--no-retain-track-cover")
    ] = None,
    scan: Annotated[bool | None, typer.Option("--scan/--no-scan")] = None,
    add_unavailable: Annotated[
        bool | None, typer.Option("--add-unavailable/--no-add-unavailable")
    ] = None,
    create_skip_file: Annotated[
        bool | None, typer.Option("--create-skip-file/--no-create-skip-file")
    ] = None,
    respect_skip_file: Annotated[
        bool | None, typer.Option("--respect-skip-file/--no-respect-skip-file")
    ] = None,
    save_errors: Annotated[Path | None, typer.Option("--save-errors")] = None,
    print_errors: Annotated[bool, typer.Option("--print-errors")] = False,
    offline: Annotated[bool, typer.Option("--offline")] = False,
) -> None:
    """Download tracks, albums, or playlists (spec §7)."""
    console = Console()
    try:
        resolved = _resolve(
            queries,
            cfg=_maybe_load_config(),
            output=output,
            output_format=output_format,
            bitrate=bitrate,
            overwrite=overwrite,
            restrict=None if restrict == "none" else restrict,
            m3u=m3u,
            save_file=save_file,
            archive=archive,
            embed_lyrics=embed_lyrics,
            generate_lrc=generate_lrc,
            sponsor_block=sponsor_block,
            threads=threads,
            cookie_file=cookie_file,
            proxy=proxy,
            ffmpeg=ffmpeg,
            ffmpeg_args=ffmpeg_args,
            ytdlp_args=ytdlp_args,
            detect_formats=detect_formats,
            max_filename_length=max_filename_length,
            id3_separator=id3_separator,
            skip_explicit=skip_explicit,
            playlist_numbering=playlist_numbering,
            retain_track_cover=retain_track_cover,
            scan=scan,
            add_unavailable=add_unavailable,
            create_skip_file=create_skip_file,
            respect_skip_file=respect_skip_file,
            save_errors=save_errors,
            print_errors=print_errors,
            offline=offline,
        )
        code = asyncio.run(_run(resolved, console))
    except ApiError as exc:
        code = render_api_error(exc)
    raise typer.Exit(int(code))


def _maybe_load_config() -> Any:
    """Load the CLI config if Task 3's ``config`` module has landed, else ``None``."""
    try:
        from importlib import import_module

        return import_module("spotdl_cli.config").load_config()
    except Exception:  # noqa: BLE001 - config is an optional sibling seam here
        return None


def register(app: typer.Typer) -> None:
    """Register ``download`` on ``app`` (additive; Task 13 finalizes bare-query sugar)."""
    app.command("download")(download)


__all__ = ["ResolvedDownload", "download", "register", "split_output_template"]
