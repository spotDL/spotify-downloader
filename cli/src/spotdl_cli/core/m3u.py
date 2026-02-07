"""M3U/M3U8 playlist file generation."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from spotdl_cli.core.types import Song

logger = logging.getLogger(__name__)


def create_file_name(
    song: Song,
    template: str,
    file_extension: str,
    sanitize: bool = True,
) -> Path:
    """Create a file path from a song and template.

    This is a simplified version used for M3U entries.

    Args:
        song: Song object.
        template: Output template string.
        file_extension: Audio file extension (without dot).
        sanitize: Whether to sanitize the filename.

    Returns:
        Relative path for the song file.
    """
    first_artist = song.artists[0] if song.artists else "Unknown"

    replacements = {
        "{artist}": first_artist,
        "{artists}": ", ".join(song.artists) if song.artists else "Unknown",
        "{title}": song.name,
        "{album}": song.album_name or "Unknown",
        "{album-artist}": song.album_artist or first_artist,
        "{genre}": song.genres[0] if song.genres else "",
        "{year}": str(song.year) if song.year else "Unknown",
        "{track-number}": str(song.track_number).zfill(2),
        "{track_number}": str(song.track_number).zfill(2),
        "{disc-number}": str(song.disc_number),
        "{disc_number}": str(song.disc_number),
        "{disc-count}": str(song.disc_count),
        "{duration}": str(song.duration),
        "{original-date}": song.date or "",
        "{tracks-count}": str(song.tracks_count),
        "{isrc}": song.isrc or "",
        "{track-id}": song.song_id or "",
        "{publisher}": song.publisher or "",
        "{list-length}": str(song.list_length) if song.list_length else "",
        "{list-position}": f"{song.list_position:02d}" if song.list_position else "",
        "{list-name}": song.list_name or "",
        "{output-ext}": file_extension,
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)

    # Ensure extension
    if not result.endswith(f".{file_extension}"):
        result = f"{result}.{file_extension}"

    if sanitize:
        # Remove invalid filesystem characters
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            result = result.replace(char, "_")

    return Path(result)


def create_m3u_content(
    songs: list[Song],
    template: str,
    file_extension: str,
    short: bool = False,
) -> str:
    """Generate M3U playlist content.

    Args:
        songs: List of songs.
        template: Output filename template.
        file_extension: Audio file extension.
        short: If True, use short format (no EXTINF headers).

    Returns:
        M3U file content as string.
    """
    lines = ["#EXTM3U"]

    for song in songs:
        if not short:
            duration = int(song.duration) if song.duration else -1
            artist = song.artists[0] if song.artists else "Unknown"
            lines.append(f"#EXTINF:{duration},{artist} - {song.name}")

        file_name = create_file_name(song, template, file_extension)
        lines.append(str(file_name))

    return "\n".join(lines)


def gen_m3u_files(
    songs: list[Song],
    m3u_template: str,
    output_template: str,
    file_extension: str,
    song_lists: dict[str, list[Song]] | None = None,
) -> list[Path]:
    """Generate M3U files from songs.

    Supports {list} template variable for per-playlist/album files.

    Args:
        songs: All songs to include.
        m3u_template: Path template for M3U file. Supports {list} variable.
        output_template: Template for individual song filenames.
        file_extension: Audio file extension.
        song_lists: Optional mapping of list names to their songs.

    Returns:
        List of paths to generated M3U files.
    """
    generated: list[Path] = []

    # Ensure .m3u8 extension
    if not m3u_template.endswith((".m3u", ".m3u8")):
        m3u_template += ".m3u8"

    # Handle {list} template variable
    list_pattern = re.compile(r"\{list(?:\[(\d+)\])?\}")
    has_list_var = list_pattern.search(m3u_template) is not None

    if has_list_var and song_lists:
        # Generate separate M3U per list
        list_names = list(song_lists.keys())
        for list_name, list_songs in song_lists.items():
            if not list_songs:
                continue

            # Replace {list} and {list[N]} patterns
            m3u_path_str = m3u_template
            m3u_path_str = m3u_path_str.replace("{list}", _sanitize_name(list_name))

            # Replace {list[N]} with specific list name
            for match in list_pattern.finditer(m3u_template):
                idx = match.group(1)
                if idx is not None:
                    idx_int = int(idx)
                    if idx_int < len(list_names):
                        m3u_path_str = m3u_path_str.replace(
                            match.group(0), _sanitize_name(list_names[idx_int])
                        )

            m3u_path = Path(m3u_path_str)
            content = create_m3u_content(list_songs, output_template, file_extension)

            try:
                m3u_path.parent.mkdir(parents=True, exist_ok=True)
                m3u_path.write_text(content, encoding="utf-8")
                generated.append(m3u_path)
                logger.info("Generated M3U: %s", m3u_path)
            except OSError as e:
                logger.error("Failed to write M3U %s: %s", m3u_path, e)
    else:
        # Single M3U file with all songs
        # Remove any {list} patterns from template
        m3u_path_str = list_pattern.sub("all", m3u_template)
        m3u_path = Path(m3u_path_str)

        content = create_m3u_content(songs, output_template, file_extension)

        try:
            m3u_path.parent.mkdir(parents=True, exist_ok=True)
            m3u_path.write_text(content, encoding="utf-8")
            generated.append(m3u_path)
            logger.info("Generated M3U: %s", m3u_path)
        except OSError as e:
            logger.error("Failed to write M3U %s: %s", m3u_path, e)

    return generated


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in file paths."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name.strip(". ")
