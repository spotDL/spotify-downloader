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


def _print_cover_art(cover_url: str) -> None:
    """Fetch and print cover art for CLI output."""
    try:
        import httpx
        from PIL import Image
        from rich_pixels import Pixels

        response = httpx.get(cover_url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()

        from io import BytesIO

        img = Image.open(BytesIO(response.content)).convert("RGB")
        img.thumbnail((64, 64), Image.Resampling.LANCZOS)
        pixels = Pixels.from_image(img, resize=(32, 16))
        console.print(pixels)
    except Exception:
        pass  # Silently skip if cover art can't be rendered


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
        str,
        typer.Option("--overwrite", help="Overwrite mode: skip, force, or metadata"),
    ] = "skip",
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

    valid_overwrite = ("skip", "force", "metadata")
    if overwrite not in valid_overwrite:
        console.print(f"[red]Invalid overwrite mode. Choose from: {', '.join(valid_overwrite)}[/]")
        raise typer.Exit(1)

    # Update settings
    settings = get_settings()
    settings.audio_format = format  # type: ignore
    settings.audio_quality = quality  # type: ignore
    settings.threads = threads
    settings.overwrite = overwrite  # type: ignore

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

            # Render cover art if available
            if song.cover_url:
                _print_cover_art(song.cover_url)

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


@app.command()
def save(
    queries: Annotated[
        list[str],
        typer.Argument(help="Songs/playlists/albums to save"),
    ],
    output: Annotated[
        str,
        typer.Option("-o", "--output", help="Output JSON file path"),
    ] = "songs.spotdl",
    preload: Annotated[
        bool,
        typer.Option("--preload", help="Pre-search download URLs"),
    ] = False,
    with_lyrics: Annotated[
        bool,
        typer.Option("--lyrics", help="Include lyrics"),
    ] = False,
    format: Annotated[
        str | None,
        typer.Option("-f", "--format", help="Audio format"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Save song metadata to a .spotdl JSON file without downloading.

    Examples:
        spotdl save "https://open.spotify.com/playlist/..."
        spotdl save "artist:Daft Punk" -o daft_punk.spotdl --preload
        spotdl save "album:Random Access Memories" --lyrics
    """
    setup_logging(verbose)
    settings = get_settings()
    if format:
        settings.audio_format = format  # type: ignore

    console.print(f"[cyan]Resolving {len(queries)} query(ies)...[/]")
    songs = asyncio.run(resolve_queries(queries, settings))

    if not songs:
        console.print("[yellow]No songs found for the given queries.[/]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(songs)} song(s)[/]")

    async def _process_songs() -> list[dict]:
        offline_matcher = get_offline_matcher()
        processed = []
        for song in songs:
            entry: dict = song.json if hasattr(song, "json") else song.to_dict()

            if preload:
                try:
                    result = await offline_matcher.get_best_match(song, min_score=60.0)
                    if result:
                        entry["download_url"] = result.url
                except Exception:
                    pass

            if with_lyrics and not entry.get("lyrics"):
                # Try to fetch lyrics via API
                try:
                    api_client = get_api_client()
                    is_online = await api_client.is_online()
                    if is_online:
                        lyrics_data = await api_client.get_lyrics(
                            song.platform_id, song.platform.value
                        )
                        if lyrics_data.get("lyrics"):
                            entry["lyrics"] = lyrics_data["lyrics"]
                    await api_client.close()
                except Exception:
                    pass

            processed.append(entry)
        return processed

    song_data = asyncio.run(_process_songs())

    # Write output
    if output == "-":
        console.print(json.dumps(song_data, indent=2, ensure_ascii=False))
    else:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(song_data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Saved {len(song_data)} song(s) to {output_path}[/]")

    # Generate M3U if configured
    if settings.m3u:
        from spotdl_cli.core.m3u import gen_m3u_files
        gen_m3u_files(
            songs, settings.m3u, settings.output_template, settings.audio_format
        )


@app.command()
def url(
    queries: Annotated[
        list[str],
        typer.Argument(help="Songs/playlists/albums to get URLs for"),
    ],
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Print download URLs to stdout for scripting/piping.

    Examples:
        spotdl url "https://open.spotify.com/track/..."
        spotdl url "Daft Punk - Get Lucky"
    """
    setup_logging(verbose)
    settings = get_settings()

    console.print("[cyan]Resolving queries...[/]", stderr=True)
    songs = asyncio.run(resolve_queries(queries, settings))

    if not songs:
        console.print("[yellow]No songs found.[/]", stderr=True)
        raise typer.Exit(0)

    async def _find_urls() -> list[str]:
        offline_matcher = get_offline_matcher()
        urls = []
        for song in songs:
            try:
                result = await offline_matcher.get_best_match(song, min_score=60.0)
                if result:
                    urls.append(result.url)
                else:
                    logger.warning("No match found for: %s", song.display_name)
            except Exception as e:
                logger.warning("Failed to find URL for %s: %s", song.display_name, e)
        return urls

    found_urls = asyncio.run(_find_urls())

    for u in found_urls:
        print(u)


@app.command()
def sync(
    queries: Annotated[
        list[str],
        typer.Argument(help="Queries or .spotdl sync file"),
    ],
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output directory"),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option("-f", "--format", help="Audio format"),
    ] = None,
    no_delete: Annotated[
        bool,
        typer.Option("--no-delete", help="Don't delete removed songs"),
    ] = False,
    remove_lrc: Annotated[
        bool,
        typer.Option("--remove-lrc", help="Also remove LRC files for deleted songs"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Synchronize a local music library with a remote playlist.

    First run creates a sync file. Subsequent runs update the library.

    Examples:
        spotdl sync "https://open.spotify.com/playlist/..."
        spotdl sync my_playlist.spotdl
    """
    from spotdl_cli.core.sync import PlaylistSyncManager, SyncFile

    setup_logging(verbose)
    settings = get_settings()
    if format:
        settings.audio_format = format  # type: ignore
    if output:
        settings.output_dir = output
    no_delete = no_delete or settings.sync_without_deleting
    remove_lrc = remove_lrc or settings.sync_remove_lrc

    # Check if first argument is an existing .spotdl sync file
    sync_file_path = Path(queries[0]) if len(queries) == 1 else None
    is_update = sync_file_path and sync_file_path.exists() and sync_file_path.suffix == ".spotdl"

    if is_update and sync_file_path:
        # Update mode: load existing sync file and compare
        console.print(f"[cyan]Loading sync file: {sync_file_path}[/]")
        try:
            sync_data = SyncFile.load(sync_file_path)
        except (ValueError, json.JSONDecodeError) as e:
            console.print(f"[red]Invalid sync file: {e}[/]")
            raise typer.Exit(1)

        old_songs = sync_data.songs

        # Re-resolve original queries to get current state
        console.print("[cyan]Fetching current playlist state...[/]")
        new_songs = asyncio.run(resolve_queries(sync_data.query, settings))

        if not new_songs:
            console.print("[yellow]No songs found in current playlist state.[/]")
            raise typer.Exit(0)

        # Compute sync actions
        sync_manager = PlaylistSyncManager(settings)
        actions = sync_manager.compute_sync_actions(
            old_songs, new_songs, no_delete=no_delete, remove_lrc=remove_lrc
        )

        if not actions.has_changes:
            console.print("[green]Already in sync. No changes needed.[/]")
            # Update sync file with new state anyway
            sync_data.songs = new_songs
            sync_data.save(sync_file_path)
            raise typer.Exit(0)

        console.print(f"[cyan]Sync actions: {actions.summary()}[/]")

        # Execute renames
        if actions.renames:
            renamed = sync_manager.execute_renames(actions.renames)
            console.print(f"[green]Renamed {renamed} file(s)[/]")

        # Execute deletions
        if actions.deletions:
            deleted = sync_manager.execute_deletions(actions.deletions)
            console.print(f"[yellow]Deleted {deleted} file(s)[/]")

        # Download new songs
        if actions.downloads:
            console.print(f"[cyan]Downloading {len(actions.downloads)} new song(s)...[/]")
            success, failed = asyncio.run(download_songs(actions.downloads, settings))
            if success > 0:
                console.print(f"[green]Downloaded {success} song(s)[/]")
            if failed > 0:
                console.print(f"[red]Failed to download {failed} song(s)[/]")

        # Update sync file with new state
        sync_data.songs = new_songs
        sync_data.save(sync_file_path)
        console.print(f"[green]Sync file updated: {sync_file_path}[/]")

    else:
        # Create mode: resolve queries, save sync file, download
        console.print(f"[cyan]Resolving {len(queries)} query(ies)...[/]")
        songs = asyncio.run(resolve_queries(queries, settings))

        if not songs:
            console.print("[yellow]No songs found for the given queries.[/]")
            raise typer.Exit(0)

        console.print(f"[green]Found {len(songs)} song(s)[/]")

        # Save sync file
        sync_file_name = settings.save_file or "sync.spotdl"
        sync_path = Path(sync_file_name)
        sync_data = SyncFile(query=queries, songs=songs)
        sync_data.save(sync_path)
        console.print(f"[green]Created sync file: {sync_path}[/]")

        # Download all songs
        success, failed = asyncio.run(download_songs(songs, settings))

        if success > 0:
            console.print(f"[green]Downloaded {success} song(s)[/]")
        if failed > 0:
            console.print(f"[red]Failed to download {failed} song(s)[/]")

    # Generate M3U if configured
    if settings.m3u:
        from spotdl_cli.core.m3u import gen_m3u_files
        gen_m3u_files(
            new_songs if is_update else songs,
            settings.m3u,
            settings.output_template,
            settings.audio_format,
        )


@app.command()
def meta(
    paths: Annotated[
        list[str],
        typer.Argument(help="Audio files or directories to update metadata for"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Force update all metadata"),
    ] = False,
    with_lrc: Annotated[
        bool,
        typer.Option("--lrc", help="Generate LRC files"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
) -> None:
    """Update metadata on existing local audio files.

    Reads ID3 tags, searches Spotify for matching songs, and re-embeds
    corrected metadata.

    Examples:
        spotdl meta ./music/
        spotdl meta song.mp3 --force
        spotdl meta ./downloads/ --lrc
    """
    from spotdl_cli.core.downloader import Downloader
    from spotdl_cli.core.lrc import generate_lrc
    from spotdl_cli.core.metadata_reader import find_audio_files, read_file_metadata

    setup_logging(verbose)
    settings = get_settings()

    # Find all audio files
    file_paths = [Path(p) for p in paths]
    audio_files = find_audio_files(file_paths)

    if not audio_files:
        console.print("[yellow]No audio files found.[/]")
        raise typer.Exit(0)

    console.print(f"[cyan]Found {len(audio_files)} audio file(s)[/]")

    async def _process_files() -> tuple[int, int]:
        downloader = Downloader(settings)
        api_client = get_api_client()
        offline_matcher = get_offline_matcher()

        is_online = False
        try:
            is_online = await api_client.is_online()
        except Exception:
            pass

        updated = 0
        skipped = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=len(audio_files))

            for file_path in audio_files:
                try:
                    # Read existing metadata
                    existing = read_file_metadata(file_path)

                    # Skip if metadata looks complete and not forcing
                    if not force and existing.get("name") and existing.get("artists"):
                        if not with_lrc:
                            skipped += 1
                            progress.update(task, advance=1)
                            continue

                    # Try to find the song
                    song: Song | None = None

                    # If we have a Spotify URL in metadata, use it directly
                    spotify_url = existing.get("spotify_url")
                    if spotify_url:
                        try:
                            if is_online:
                                resolved = await api_client.resolve_url(spotify_url)
                                if resolved:
                                    song = resolved[0]
                            else:
                                resolved = await offline_matcher.resolve_url(spotify_url)
                                if resolved:
                                    song = resolved[0]
                        except Exception:
                            pass

                    # Otherwise search by filename/tags
                    if song is None:
                        search_term = existing.get("name", "")
                        if existing.get("artists"):
                            search_term = f"{existing['artists'][0]} {search_term}"
                        if not search_term:
                            search_term = file_path.stem

                        if search_term:
                            try:
                                if is_online:
                                    results = await api_client.search(search_term, limit=1)
                                    if results:
                                        song = results[0]
                                else:
                                    results = await offline_matcher.search_all(
                                        search_term, limit=1
                                    )
                                    if results:
                                        song = results[0]
                            except Exception:
                                pass

                    if song is None:
                        logger.warning("No match found for: %s", file_path.name)
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                    # Embed metadata
                    await downloader.embed_metadata(file_path, song)

                    # Embed lyrics
                    if song.lyrics:
                        await downloader.embed_lyrics(file_path, song.lyrics)

                    # Generate LRC if requested
                    if with_lrc:
                        generate_lrc(
                            song.name, song.artists, file_path, song.lyrics
                        )

                    updated += 1

                except Exception as e:
                    logger.error("Failed to process %s: %s", file_path.name, e)
                    skipped += 1

                progress.update(task, advance=1)

        await downloader.close()
        await api_client.close()
        return updated, skipped

    updated, skipped = asyncio.run(_process_files())

    console.print()
    if updated > 0:
        console.print(f"[green]Updated metadata for {updated} file(s)[/]")
    if skipped > 0:
        console.print(f"[yellow]Skipped {skipped} file(s)[/]")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
