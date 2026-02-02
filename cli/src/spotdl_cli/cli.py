"""CLI commands for SpotDL using Typer.

Non-interactive command-line interface for downloading music.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core import (
    APIError,
    DownloadManager,
    DownloadQueue,
    DownloadResult,
    Song,
    TargetPlatform,
    get_api_client,
    get_offline_matcher,
)
from spotdl_cli.core.query import QueryType, parse_query

app = typer.Typer(
    name="spotdl",
    help="Download music from Spotify, YouTube Music, Deezer, and more.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
logger = logging.getLogger(__name__)


def _truncate_album(album_name: str | None, max_len: int = 20) -> str:
    """Truncate album name for display."""
    if not album_name:
        return "-"
    if len(album_name) > max_len:
        return album_name[:max_len] + "..."
    return album_name


def setup_logging(verbose: bool) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


async def resolve_queries(
    queries: list[str],
    settings: Settings,
) -> list[Song]:
    """Resolve queries to songs."""
    songs: list[Song] = []
    api_client = get_api_client()
    offline_matcher = get_offline_matcher()

    # Check connectivity
    is_online = False
    if not settings.offline_mode:
        try:
            is_online = await api_client.is_online()
        except Exception:
            pass

    for query in queries:
        query_type, query_value = parse_query(query)

        try:
            if query_type == QueryType.URL:
                # URL resolution
                if is_online:
                    try:
                        resolved = await api_client.resolve_url(query_value)
                        songs.extend(resolved)
                        continue
                    except APIError:
                        pass

                # Try offline
                resolved = await offline_matcher.resolve_url(query_value)
                songs.extend(resolved)

            elif query_type == QueryType.ALBUM:
                # Album search
                if is_online:
                    results = await api_client.search(f"album:{query_value}")
                    songs.extend(results)
                else:
                    results = await offline_matcher.search_all(
                        f"album {query_value}", limit=50
                    )
                    songs.extend(results)

            elif query_type == QueryType.ARTIST:
                # Artist search
                if is_online:
                    results = await api_client.search(f"artist:{query_value}")
                    songs.extend(results)
                else:
                    results = await offline_matcher.search_all(
                        f"artist {query_value}", limit=50
                    )
                    songs.extend(results)

            elif query_type == QueryType.PLAYLIST:
                # Playlist search
                if is_online:
                    results = await api_client.search(f"playlist:{query_value}")
                    songs.extend(results)
                else:
                    console.print(
                        f"[yellow]Playlist search not supported offline: {query_value}[/]"
                    )

            elif query_type == QueryType.TRACK:
                # Track search
                if is_online:
                    results = await api_client.search(query_value)
                    songs.extend(results)
                else:
                    results = await offline_matcher.search_all(query_value, limit=1)
                    songs.extend(results)

            elif query_type == QueryType.SAVED:
                # User's saved tracks
                if is_online:
                    console.print("[yellow]Fetching saved tracks requires authentication[/]")
                else:
                    console.print("[yellow]Saved tracks not available offline[/]")

            else:
                # Auto-detect: URL or search
                if query_value.startswith(("http://", "https://", "spotify:", "deezer:")):
                    if is_online:
                        try:
                            resolved = await api_client.resolve_url(query_value)
                            songs.extend(resolved)
                            continue
                        except APIError:
                            pass
                    resolved = await offline_matcher.resolve_url(query_value)
                    songs.extend(resolved)
                else:
                    # Search query
                    if is_online:
                        results = await api_client.search(query_value)
                        songs.extend(results)
                    else:
                        results = await offline_matcher.search_all(query_value, limit=10)
                        songs.extend(results)

        except Exception as e:
            console.print(f"[red]Error processing '{query}': {e}[/]")

    await api_client.close()
    return songs


async def download_songs(
    songs: list[Song],
    settings: Settings,
    output: Path | None = None,
) -> tuple[int, int]:
    """Download songs and return (success_count, fail_count)."""
    if not songs:
        return 0, 0

    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Update settings output dir if custom path provided
    if output:
        settings.output_dir = output

    download_manager = DownloadManager(
        settings=settings,
        max_concurrent=settings.threads,
    )

    queue = DownloadQueue(max_concurrent=settings.threads)
    offline_matcher = get_offline_matcher()

    # Add songs to queue with matched results
    for song in songs:
        # Try to find a match if not already from a URL
        result = None
        if song.url and ("youtube.com" in song.url or "youtu.be" in song.url):
            # Create result from existing URL
            result = DownloadResult(
                name=song.name,
                artists=song.artists,
                artist=song.artist,
                duration=song.duration,
                platform=TargetPlatform.YOUTUBE,
                platform_id=song.platform_id,
                url=song.url,
                verified=False,
                score=100.0,
                cover_url=song.cover_url,
            )
        else:
            # Try to find a match
            try:
                result = await offline_matcher.get_best_match(song, min_score=60.0)
            except Exception as e:
                logger.warning(f"Failed to find match for {song.display_name}: {e}")

        await queue.add(song, result=result)

    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Downloading...",
            total=len(songs),
        )

        # Process queue
        while queue.pending_count > 0 or queue.active_count > 0:
            # Get next pending item
            next_item = await queue.get_next_pending()
            if next_item is None:
                await asyncio.sleep(0.1)
                continue

            item_id, item = next_item

            # Download using the manager (no status callback for CLI mode)
            result_path = await download_manager.download_item(
                item_id,
                item,
            )

            if result_path:
                success_count += 1
            else:
                fail_count += 1

            progress.update(task, advance=1)

    await download_manager.close()
    return success_count, fail_count


@app.command()
def download(
    queries: Annotated[
        list[str],
        typer.Argument(help="URLs or search queries to download"),
    ],
    format: Annotated[
        str,
        typer.Option("-f", "--format", help="Audio format (mp3, m4a, flac, opus, ogg, wav)"),
    ] = "mp3",
    quality: Annotated[
        str,
        typer.Option("-q", "--quality", help="Audio quality (best, 320k, 256k, 192k, 128k)"),
    ] = "best",
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output directory"),
    ] = None,
    threads: Annotated[
        int,
        typer.Option("-t", "--threads", help="Number of download threads (1-16)"),
    ] = 4,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Download songs from URLs or search queries.

    Examples:
        spotdl download "https://open.spotify.com/track/..."
        spotdl download "artist:Daft Punk"
        spotdl download "album:Random Access Memories"
        spotdl download "Daft Punk - Get Lucky"
    """
    setup_logging(verbose)

    # Validate options
    valid_formats = ("mp3", "m4a", "flac", "opus", "ogg", "wav")
    if format not in valid_formats:
        console.print(f"[red]Invalid format. Choose from: {', '.join(valid_formats)}[/]")
        raise typer.Exit(1)

    valid_qualities = ("best", "320k", "256k", "192k", "128k")
    if quality not in valid_qualities:
        console.print(f"[red]Invalid quality. Choose from: {', '.join(valid_qualities)}[/]")
        raise typer.Exit(1)

    if not 1 <= threads <= 16:
        console.print("[red]Threads must be between 1 and 16[/]")
        raise typer.Exit(1)

    # Update settings
    settings = get_settings()
    settings.audio_format = format  # type: ignore
    settings.audio_quality = quality  # type: ignore
    settings.threads = threads
    settings.overwrite = overwrite

    console.print(f"[cyan]Resolving {len(queries)} query(ies)...[/]")

    # Resolve queries to songs
    songs = asyncio.run(resolve_queries(queries, settings))

    if not songs:
        console.print("[yellow]No songs found for the given queries.[/]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(songs)} song(s)[/]")

    # Download
    success, failed = asyncio.run(download_songs(songs, settings, output))

    # Summary
    console.print()
    if success > 0:
        console.print(f"[green]Successfully downloaded {success} song(s)[/]")
    if failed > 0:
        console.print(f"[red]Failed to download {failed} song(s)[/]")

    if failed > 0:
        raise typer.Exit(1)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    platform: Annotated[
        str,
        typer.Option("-p", "--platform", help="Platform to search (spotify, deezer, youtube)"),
    ] = "spotify",
    limit: Annotated[
        int,
        typer.Option("-l", "--limit", help="Maximum number of results"),
    ] = 10,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Search for songs on various platforms.

    Examples:
        spotdl search "Daft Punk"
        spotdl search "Random Access Memories" --platform deezer --limit 20
        spotdl search "Get Lucky" --json
    """
    setup_logging(verbose)

    async def do_search() -> list[Song]:
        api_client = get_api_client()
        offline_matcher = get_offline_matcher()

        is_online = False
        try:
            is_online = await api_client.is_online()
        except Exception:
            pass

        results: list[Song] = []
        if is_online:
            try:
                results = await api_client.search(query, limit=limit)
            except APIError as e:
                console.print(f"[yellow]API error: {e}. Falling back to offline search.[/]")
                results = await offline_matcher.search_all(query, limit=limit)
        else:
            results = await offline_matcher.search_all(query, limit=limit)

        await api_client.close()
        return results

    songs = asyncio.run(do_search())

    if not songs:
        console.print("[yellow]No results found.[/]")
        raise typer.Exit(0)

    if json_output:
        # JSON output
        output_data = [
            {
                "name": song.name,
                "artist": song.artist,
                "artists": song.artists,
                "album": song.album_name,
                "duration": song.duration,
                "platform": song.platform.value,
                "url": song.url,
            }
            for song in songs[:limit]
        ]
        console.print(json.dumps(output_data, indent=2))
    else:
        # Table output
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("#", style="dim")
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="green")
        table.add_column("Album")
        table.add_column("Duration", style="dim")
        table.add_column("Platform", style="magenta")

        for i, song in enumerate(songs[:limit], 1):
            duration = f"{song.duration // 60}:{song.duration % 60:02d}"
            table.add_row(
                str(i),
                song.name[:40] + "..." if len(song.name) > 40 else song.name,
                song.artist[:25] + "..." if len(song.artist) > 25 else song.artist,
                _truncate_album(song.album_name),
                duration,
                song.platform.value,
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(songs)} result(s)[/]")


@app.command()
def info(
    url: Annotated[str, typer.Argument(help="URL to get information about")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Show information about a track, album, artist, or playlist URL.

    Examples:
        spotdl info "https://open.spotify.com/track/..."
        spotdl info "https://open.spotify.com/album/..." --json
    """
    setup_logging(verbose)

    async def get_info() -> list[Song]:
        api_client = get_api_client()
        offline_matcher = get_offline_matcher()

        is_online = False
        try:
            is_online = await api_client.is_online()
        except Exception:
            pass

        songs: list[Song] = []
        if is_online:
            try:
                songs = await api_client.resolve_url(url)
            except APIError as e:
                console.print(f"[yellow]API error: {e}. Trying offline resolution.[/]")
                songs = await offline_matcher.resolve_url(url)
        else:
            songs = await offline_matcher.resolve_url(url)

        await api_client.close()
        return songs

    songs = asyncio.run(get_info())

    if not songs:
        console.print("[yellow]Could not resolve URL.[/]")
        raise typer.Exit(1)

    if json_output:
        output_data = [
            {
                "name": song.name,
                "artist": song.artist,
                "artists": song.artists,
                "album": song.album_name,
                "duration": song.duration,
                "platform": song.platform.value,
                "platform_id": song.platform_id,
                "url": song.url,
                "cover_url": song.cover_url,
            }
            for song in songs
        ]
        console.print(json.dumps(output_data, indent=2))
    else:
        if len(songs) == 1:
            # Single track info
            song = songs[0]
            console.print(f"\n[bold cyan]{song.name}[/]")
            console.print(f"[green]Artist:[/] {song.artist}")
            if song.album_name:
                console.print(f"[green]Album:[/] {song.album_name}")
            console.print(f"[green]Duration:[/] {song.duration // 60}:{song.duration % 60:02d}")
            console.print(f"[green]Platform:[/] {song.platform.value}")
            console.print(f"[green]URL:[/] {song.url}")
            if song.cover_url:
                console.print(f"[green]Cover:[/] {song.cover_url}")
        else:
            # Multiple tracks (album/playlist)
            console.print(f"\n[bold]Found {len(songs)} tracks[/]\n")

            table = Table()
            table.add_column("#", style="dim")
            table.add_column("Title", style="cyan")
            table.add_column("Artist", style="green")
            table.add_column("Duration", style="dim")

            for i, song in enumerate(songs, 1):
                duration = f"{song.duration // 60}:{song.duration % 60:02d}"
                table.add_row(
                    str(i),
                    song.name[:45] + "..." if len(song.name) > 45 else song.name,
                    song.artist[:25] + "..." if len(song.artist) > 25 else song.artist,
                    duration,
                )

            console.print(table)

            # Total duration
            total_seconds = sum(song.duration for song in songs)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                console.print(f"\n[dim]Total duration: {hours}h {minutes}m {seconds}s[/]")
            else:
                console.print(f"\n[dim]Total duration: {minutes}m {seconds}s[/]")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
