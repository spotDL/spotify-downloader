"""``spotdl search`` / ``url`` / ``save`` / ``meta`` — the read-ish operations.

The four v4 metadata operations that don't fetch audio into the library:

* ``search`` — a ranked track search rendered as a Rich table.
* ``url`` — resolve each query and print the top audio-target URL per track (the
  playable link the downloader would pull), over the **resolution** transport.
* ``save`` — resolve/expand and write the batch ``.spotdl`` v2 save-file.
* ``meta`` — re-tag local audio files via a metadata-only re-submit (no audio
  fetch) through the embedded download surface.

``save``/``meta`` go through the **embedded** download/batch endpoints; ``search``/
``url`` only need the resolution transport. Both reach the server through the one
:class:`~spotdl_cli.client.SpotdlClient` façade.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import typer
from rich.table import Table

from spotdl_cli.client import SpotdlClient
from spotdl_cli.commands import _support
from spotdl_cli.errors import ExitCode
from spotdl_cli.views import BatchView, DownloadSubmit, EntityView, TrackView


def _fmt_duration(duration_ms: int) -> str:
    """Render a track duration as ``m:ss`` (or ``h:mm:ss`` past an hour)."""
    total_seconds = max(0, duration_ms) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _entity_tracks(entity: EntityView) -> list[TrackView]:
    """Flatten a resolved entity to the ordered track list it downloads to."""
    if entity.track is not None:
        return [entity.track]
    if entity.album is not None:
        return list(entity.album.tracks)
    if entity.playlist is not None:
        return list(entity.playlist.tracks)
    if entity.artist is not None:
        return list(entity.artist.tracks)
    return []


def _file_query(path: Path) -> str:
    """Derive a resolve query for a local audio file from its filename stem.

    The v4 ``meta`` operation reads the embedded Spotify URL when present; that
    tag read is a follow-up (it needs a tag library the CLI does not yet depend
    on). The filename stem — v4's own fallback — is a safe, dependency-free query.
    """
    return path.stem


async def _search(q: str, *, limit: int, offline: bool) -> list[TrackView]:
    async with _support.open_client(offline=offline) as client:
        return await client.search(q, limit=limit)


async def _urls(queries: list[str], *, offline: bool) -> list[tuple[TrackView, str | None]]:
    resolved: list[tuple[TrackView, str | None]] = []
    async with _support.open_client(offline=offline) as client:
        for query in queries:
            entity = await client.resolve(query)
            for track in _entity_tracks(entity):
                resolved.append((track, await _top_target_url(client, track)))
    return resolved


async def _top_target_url(client: SpotdlClient, track: TrackView) -> str | None:
    """The top-ranked audio-target URL for ``track`` (``None`` if unmatched)."""
    try:
        track_id = UUID(track.id)
    except ValueError:
        return None
    matches = await client.matches(track_id)
    return matches[0].target_url if matches else None


async def _save(url: str, *, offline: bool) -> dict[str, Any]:
    async with _support.open_client(offline=offline, need_downloads=True) as client:
        batch = await client.submit_download(DownloadSubmit(query=url, generate_save_file=True))
        model = await client.fetch_save_file(UUID(batch.batch_id))
        return model.model_dump()


async def _meta(
    files: list[Path], *, overwrite: str, skip_album_art: bool, offline: bool
) -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    async with _support.open_client(offline=offline, need_downloads=True) as client:
        for path in files:
            submitted = await client.submit_download(
                DownloadSubmit(query=_file_query(path), overwrite=overwrite)
            )
            terminal = await _await_batch(client, UUID(submitted.batch_id))
            status = "failed" if terminal.counts.get("failed", 0) else "ok"
            results.append((path, status))
    return results


async def _await_batch(client: SpotdlClient, batch_id: UUID) -> BatchView:
    """Poll a batch until it finalizes, returning the terminal ``BatchView``."""
    while True:
        batch = await client.get_batch(batch_id)
        if batch.finalized:
            return batch


def search(
    query: str = typer.Argument(..., help="Search query (free text)."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results to show."),
    offline: bool = typer.Option(False, "--offline", help="Use the embedded server only."),
) -> None:
    """Search for tracks and print a ranked table."""
    results = _support.run(_search(query, limit=limit, offline=offline))
    if not results:
        _support.err_console.print("no results", style="yellow")
        raise typer.Exit(int(ExitCode.OK))

    table = Table(title=f'search: "{query}"')
    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Artists — Title")
    table.add_column("Album")
    table.add_column("Duration", justify="right", no_wrap=True)
    for index, track in enumerate(results, start=1):
        artists = ", ".join(track.artists)
        album = track.album.name if track.album is not None else ""
        table.add_row(
            str(index), f"{artists} — {track.name}", album, _fmt_duration(track.duration_ms)
        )
    _support.console.print(table)


def url(
    queries: list[str] = typer.Argument(..., help="URLs / refs / queries to resolve."),
    offline: bool = typer.Option(False, "--offline", help="Use the embedded server only."),
) -> None:
    """Print the top audio-target URL for each resolved track."""
    resolved = _support.run(_urls(queries, offline=offline))
    for track, target in resolved:
        if target is None:
            _support.err_console.print(
                f"no audio match for {', '.join(track.artists)} — {track.name}",
                style="yellow",
            )
            continue
        _support.console.print(target, markup=False, highlight=False)


def save(
    url: str = typer.Argument(..., help="URL / ref / query to save."),
    save_file: str = typer.Option(
        None,
        "--save-file",
        help="Write the .spotdl file here (use - for stdout).",
    ),
    offline: bool = typer.Option(False, "--offline", help="Use the embedded server only."),
) -> None:
    """Resolve a URL and write its ``.spotdl`` v2 save-file."""
    if save_file is None:
        raise typer.BadParameter("--save-file is required", param_hint="--save-file")

    payload = _support.run(_save(url, offline=offline))
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if save_file == "-":
        sys.stdout.write(text)
    else:
        Path(save_file).write_text(text, encoding="utf-8")
        _support.console.print(f"saved {len(payload.get('songs', []))} songs to {save_file}")


def meta(
    files: list[Path] = typer.Argument(..., help="Local audio files to re-tag."),
    overwrite: str = typer.Option(
        "metadata",
        "--overwrite",
        help="Overwrite mode (force/skip/metadata).",
    ),
    skip_album_art: bool = typer.Option(
        False, "--skip-album-art", help="Don't re-embed album art."
    ),
    redownload: bool = typer.Option(
        False, "--redownload", help="Re-download the audio, not just the tags."
    ),
    offline: bool = typer.Option(False, "--offline", help="Use the embedded server only."),
) -> None:
    """Re-tag local audio files from freshly resolved metadata."""
    mode = "force" if redownload else overwrite
    results = _support.run(
        _meta(files, overwrite=mode, skip_album_art=skip_album_art, offline=offline)
    )
    failures = [path for path, status in results if status != "ok"]
    for path, status in results:
        style = "green" if status == "ok" else "red"
        _support.console.print(f"{status:>6}  {path}", style=style)
    if failures:
        raise typer.Exit(int(ExitCode.DOWNLOAD_FAILURES))


def register(app: typer.Typer) -> None:
    """Attach ``search``/``url``/``save``/``meta`` to the root Typer app."""
    app.command("search")(search)
    app.command("url")(url)
    app.command("save")(save)
    app.command("meta")(meta)
