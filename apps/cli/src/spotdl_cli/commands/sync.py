"""``spotdl sync`` — keep a library in step with a source, via a ``.spotdl`` file.

Two shapes (v4 parity):

- ``spotdl sync <url> --save-file f.spotdl`` resolves + downloads the source and
  writes/refreshes the ``.spotdl`` v2 file.
- ``spotdl sync f.spotdl`` re-resolves the file's recorded source, downloads
  newly-added tracks, and prunes local files for tracks the source dropped
  (unless ``--no-delete``); ``--remove-lrc`` also deletes their orphaned ``.lrc``.

A v4 ``.spotdl`` passed to ``sync`` is auto-migrated (CONTRACT G) and rewritten in
v2 on save, with a one-line notice. Downloads always run against the embedded
transport; the submit/progress plumbing and option resolution are shared with
``spotdl download``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import typer
from rich.console import Console
from spotdl_server.downloads.savefile import SaveFileV2

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.commands import download as dl
from spotdl_cli.errors import ApiError, ExitCode, render_api_error
from spotdl_cli.progress import (
    RichProgressReporter,
    consume_progress,
    render_summary,
)
from spotdl_cli.savefile import dump_save_file, load_save_file


def _identity(song: Any) -> str:
    """A stable per-song key for diffing a source against a save file."""
    return song.track_url or f"{song.artist or ''}|{song.name}"


def peek_is_v4(path: Path) -> bool:
    """True if ``path`` is a v4 ``.spotdl`` (a bare JSON array)."""
    try:
        return path.read_text(encoding="utf-8").lstrip().startswith("[")
    except OSError:
        return False


def prune_removed(old: SaveFileV2, new: SaveFileV2, *, remove_lrc: bool) -> list[Path]:
    """Delete local files for tracks in ``old`` that ``new`` (the source) dropped.

    Returns the deleted paths. Mirrors v4 sync: a track no longer in the source
    has its downloaded audio removed (and its ``.lrc`` when ``--remove-lrc``).
    """
    keep = {_identity(song) for song in new.songs}
    deleted: list[Path] = []
    for song in old.songs:
        if _identity(song) in keep:
            continue
        output_path = song.download.output_path
        if not output_path:
            continue
        path = Path(output_path)
        if path.exists():
            path.unlink()
            deleted.append(path)
        if remove_lrc:
            lrc = path.with_suffix(".lrc")
            if lrc.exists():
                lrc.unlink()
                deleted.append(lrc)
    return deleted


def _combine(saves: list[SaveFileV2]) -> SaveFileV2:
    """Merge per-batch save files into one (single-source sync produces one)."""
    if len(saves) == 1:
        return saves[0]
    songs = [song for save in saves for song in save.songs]
    head = saves[0]
    return SaveFileV2(
        version=2,
        kind=head.kind,
        name=head.name,
        source=head.source,
        created_at=head.created_at,
        matcher_version=head.matcher_version,
        songs=songs,
    )


def _source_queries(url: str | None, old: SaveFileV2 | None) -> list[str]:
    """The queries to (re)submit: the source URL, else each recorded track URL.

    A file with a recorded ``source`` re-resolves upstream (so removals are
    detected); a migrated v4 file (no source) falls back to its per-track URLs.
    """
    if url is not None:
        return [url]
    if old is not None and old.source:
        return [old.source]
    if old is not None:
        return [s.track_url for s in old.songs if s.track_url]
    return []


async def _run(
    *,
    queries: list[str],
    sync_file: Path,
    old: SaveFileV2 | None,
    was_v4: bool,
    no_delete: bool,
    remove_lrc: bool,
    output: str | None,
    output_format: str | None,
    bitrate: str | None,
    threads: int | None,
    offline: bool,
    console: Console,
) -> ExitCode:
    resolved = dl._resolve(
        queries,
        cfg=dl._maybe_load_config(),
        output=output,
        output_format=output_format,
        bitrate=bitrate,
        threads=threads,
        save_file=sync_file,
        offline=offline,
    )

    async with dl._open_client(
        offline=resolved.offline, settings_env=resolved.settings_env
    ) as client:
        batch_ids: set[str] = set()
        async with client.progress() as stream:
            for submit in resolved.submits:
                batch = await client.submit_download(submit)
                batch_ids.add(batch.batch_id)
            with RichProgressReporter(console) as reporter:
                outcome = await consume_progress(stream, batch_ids, on_event=reporter.handle)
                names = reporter.names

        saves = [await client.fetch_save_file(UUID(bid)) for bid in sorted(batch_ids)]

    new = _combine(saves) if saves else (old or _empty_save())

    deleted: list[Path] = []
    if old is not None and not no_delete:
        deleted = prune_removed(old, new, remove_lrc=remove_lrc)

    sync_file.write_text(dump_save_file(new), encoding="utf-8")
    if was_v4:
        console.print(
            f"note: migrated {sync_file.name} from the spotdl v4 format to v2.",
            style="yellow",
            highlight=False,
        )
    if deleted:
        console.print(f"pruned {len(deleted)} file(s) no longer in the source")

    render_summary(console, outcome, names=names)
    return ExitCode.DOWNLOAD_FAILURES if outcome.has_failures else ExitCode.OK


def _empty_save() -> SaveFileV2:
    return SaveFileV2(version=2, kind="single", created_at="", songs=[])


def sync(
    target: Annotated[
        str, typer.Argument(help="A source URL/query, or an existing .spotdl file to refresh")
    ],
    save_file: Annotated[
        Path | None,
        typer.Option("--save-file", "--out-file", help="Where to write the .spotdl file"),
    ] = None,
    no_delete: Annotated[
        bool, typer.Option("--no-delete", help="Keep local files dropped from the source")
    ] = False,
    remove_lrc: Annotated[
        bool, typer.Option("--remove-lrc", help="Also delete orphaned .lrc files when pruning")
    ] = False,
    output: Annotated[str | None, typer.Option("-o", "--output")] = None,
    output_format: Annotated[str | None, typer.Option("-f", "--format")] = None,
    bitrate: Annotated[str | None, typer.Option("-b", "--bitrate")] = None,
    threads: Annotated[int | None, typer.Option("-t", "--threads")] = None,
    offline: Annotated[bool, typer.Option("--offline")] = False,
) -> None:
    """Synchronize a library with a source through a ``.spotdl`` v2 file (spec §7)."""
    console = Console()
    target_path = Path(target)
    is_file = target.lower().endswith(".spotdl") and target_path.is_file()

    if is_file:
        sync_file = target_path
        url: str | None = None
    else:
        url = target
        if save_file is None:
            console.print(
                "error: `spotdl sync <url>` needs --save-file to record the sync state",
                style="red",
                highlight=False,
            )
            raise typer.Exit(int(ExitCode.USAGE))
        sync_file = save_file

    try:
        old = load_save_file(sync_file) if sync_file.exists() else None
        was_v4 = peek_is_v4(sync_file) if sync_file.exists() else False
        queries = _source_queries(url, old)
        if not queries:
            raise ApiError(
                ErrorCode.VALIDATION_ERROR, "nothing to sync: no source URL and an empty save file"
            )
        code = asyncio.run(
            _run(
                queries=queries,
                sync_file=sync_file,
                old=old,
                was_v4=was_v4,
                no_delete=no_delete,
                remove_lrc=remove_lrc,
                output=output,
                output_format=output_format,
                bitrate=bitrate,
                threads=threads,
                offline=offline,
                console=console,
            )
        )
    except ApiError as exc:
        code = render_api_error(exc)
    raise typer.Exit(int(code))


def register(app: typer.Typer) -> None:
    """Register ``sync`` on ``app`` (additive)."""
    app.command("sync")(sync)


__all__ = ["peek_is_v4", "prune_removed", "register", "sync"]
