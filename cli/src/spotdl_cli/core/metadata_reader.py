"""Read metadata from existing audio files.

Used by the meta command to extract ID3/Vorbis/MP4 tags from audio files,
identify them, and update their metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported audio formats for scanning
SUPPORTED_FORMATS = {".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav"}


def find_audio_files(paths: list[Path]) -> list[Path]:
    """Recursively find all audio files in the given paths.

    Args:
        paths: List of file or directory paths.

    Returns:
        List of audio file paths.
    """
    audio_files: list[Path] = []

    for path in paths:
        if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS:
            audio_files.append(path)
        elif path.is_dir():
            for ext in SUPPORTED_FORMATS:
                audio_files.extend(path.rglob(f"*{ext}"))

    return sorted(set(audio_files))


def read_file_metadata(path: Path) -> dict[str, Any]:
    """Extract metadata from an audio file.

    Reads ID3/Vorbis/MP4 tags using mutagen and returns a normalized dictionary.

    Args:
        path: Path to audio file.

    Returns:
        Dictionary with metadata fields:
        - name, artists, album, album_artist, genres, year, date
        - track_number, disc_number, duration, lyrics
        - cover_url (spotify URL from comment/WOAR frame if present)
        - isrc
    """
    suffix = path.suffix.lower()

    try:
        if suffix == ".mp3":
            return _read_mp3_metadata(path)
        elif suffix == ".m4a":
            return _read_m4a_metadata(path)
        elif suffix == ".flac":
            return _read_flac_metadata(path)
        elif suffix in (".opus", ".ogg"):
            return _read_ogg_metadata(path)
        else:
            return _read_generic_metadata(path)
    except Exception as e:
        logger.warning("Failed to read metadata from %s: %s", path, e)
        return {}


def _read_mp3_metadata(path: Path) -> dict[str, Any]:
    """Read metadata from MP3 file."""
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.mp3 import MP3

    metadata: dict[str, Any] = {}

    try:
        audio = MP3(path)
        metadata["duration"] = int(audio.info.length) if audio.info else 0
    except Exception:
        metadata["duration"] = 0

    try:
        tags = EasyID3(path)
        metadata["name"] = tags.get("title", [""])[0]
        metadata["artists"] = list(tags.get("artist", []))
        metadata["album"] = tags.get("album", [""])[0]
        metadata["album_artist"] = tags.get("albumartist", [""])[0]
        metadata["genres"] = list(tags.get("genre", []))
        metadata["date"] = tags.get("date", [""])[0]
        metadata["year"] = _extract_year(metadata["date"])
        metadata["track_number"] = _parse_track_number(
            tags.get("tracknumber", ["0"])[0]
        )
        metadata["disc_number"] = _parse_track_number(
            tags.get("discnumber", ["1"])[0]
        )
    except ID3NoHeaderError:
        pass
    except Exception as e:
        logger.debug("Failed to read EasyID3 from %s: %s", path, e)

    # Try to extract Spotify URL from full ID3 tags
    try:
        full_tags = ID3(path)

        # Check WOAR (URL) frames
        for key in full_tags:
            if key.startswith("WOAR"):
                url = str(full_tags[key])
                if "spotify" in url:
                    metadata["spotify_url"] = url
                    break

        # Check comment frames for Spotify URL
        for key in full_tags:
            if key.startswith("COMM"):
                text = str(full_tags[key])
                if "open.spotify.com" in text or "spotify:track:" in text:
                    metadata["spotify_url"] = text.strip()
                    break

        # Check USLT (lyrics)
        for key in full_tags:
            if key.startswith("USLT"):
                metadata["lyrics"] = str(full_tags[key])
                break

    except Exception:
        pass

    return metadata


def _read_m4a_metadata(path: Path) -> dict[str, Any]:
    """Read metadata from M4A file."""
    from mutagen.mp4 import MP4

    metadata: dict[str, Any] = {}

    try:
        audio = MP4(path)
        metadata["duration"] = int(audio.info.length) if audio.info else 0

        tags = audio.tags or {}
        metadata["name"] = (tags.get("\xa9nam") or [""])[0]
        metadata["artists"] = list(tags.get("\xa9ART") or [])
        metadata["album"] = (tags.get("\xa9alb") or [""])[0]
        metadata["album_artist"] = (tags.get("aART") or [""])[0]
        metadata["genres"] = list(tags.get("\xa9gen") or [])
        metadata["date"] = (tags.get("\xa9day") or [""])[0]
        metadata["year"] = _extract_year(metadata["date"])
        metadata["lyrics"] = (tags.get("\xa9lyr") or [""])[0] or None

        # Track number tuple: (track, total)
        trkn = tags.get("trkn")
        if trkn and isinstance(trkn[0], tuple):
            metadata["track_number"] = trkn[0][0]
        else:
            metadata["track_number"] = 0

        # Disc number
        disk = tags.get("disk")
        if disk and isinstance(disk[0], tuple):
            metadata["disc_number"] = disk[0][0]
        else:
            metadata["disc_number"] = 1

        # Check comment for Spotify URL
        comment = (tags.get("\xa9cmt") or [""])[0]
        if comment and ("spotify" in comment):
            metadata["spotify_url"] = comment.strip()

    except Exception as e:
        logger.debug("Failed to read M4A metadata from %s: %s", path, e)

    return metadata


def _read_flac_metadata(path: Path) -> dict[str, Any]:
    """Read metadata from FLAC file."""
    from mutagen.flac import FLAC

    metadata: dict[str, Any] = {}

    try:
        audio = FLAC(path)
        metadata["duration"] = int(audio.info.length) if audio.info else 0

        metadata["name"] = (audio.get("title") or [""])[0]
        metadata["artists"] = list(audio.get("artist") or [])
        metadata["album"] = (audio.get("album") or [""])[0]
        metadata["album_artist"] = (audio.get("albumartist") or [""])[0]
        metadata["genres"] = list(audio.get("genre") or [])
        metadata["date"] = (audio.get("date") or [""])[0]
        metadata["year"] = _extract_year(metadata["date"])
        metadata["track_number"] = _parse_track_number(
            (audio.get("tracknumber") or ["0"])[0]
        )
        metadata["disc_number"] = _parse_track_number(
            (audio.get("discnumber") or ["1"])[0]
        )
        metadata["lyrics"] = (audio.get("lyrics") or [""])[0] or None

        # Check comment for Spotify URL
        comment = (audio.get("comment") or [""])[0]
        if comment and "spotify" in comment:
            metadata["spotify_url"] = comment.strip()

    except Exception as e:
        logger.debug("Failed to read FLAC metadata from %s: %s", path, e)

    return metadata


def _read_ogg_metadata(path: Path) -> dict[str, Any]:
    """Read metadata from OGG/Opus file."""
    suffix = path.suffix.lower()

    metadata: dict[str, Any] = {}

    try:
        if suffix == ".opus":
            from mutagen.oggopus import OggOpus
            audio = OggOpus(path)
        else:
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(path)

        metadata["duration"] = int(audio.info.length) if audio.info else 0

        metadata["name"] = (audio.get("title") or [""])[0]
        metadata["artists"] = list(audio.get("artist") or [])
        metadata["album"] = (audio.get("album") or [""])[0]
        metadata["album_artist"] = (audio.get("albumartist") or [""])[0]
        metadata["genres"] = list(audio.get("genre") or [])
        metadata["date"] = (audio.get("date") or [""])[0]
        metadata["year"] = _extract_year(metadata["date"])
        metadata["track_number"] = _parse_track_number(
            (audio.get("tracknumber") or ["0"])[0]
        )
        metadata["disc_number"] = _parse_track_number(
            (audio.get("discnumber") or ["1"])[0]
        )

        # Check comment for Spotify URL
        comment = (audio.get("comment") or [""])[0]
        if comment and "spotify" in comment:
            metadata["spotify_url"] = comment.strip()

    except Exception as e:
        logger.debug("Failed to read OGG metadata from %s: %s", path, e)

    return metadata


def _read_generic_metadata(path: Path) -> dict[str, Any]:
    """Read metadata using mutagen's auto-detection."""
    import mutagen

    metadata: dict[str, Any] = {}

    try:
        audio = mutagen.File(path, easy=True)
        if audio is None:
            return metadata

        metadata["duration"] = int(audio.info.length) if audio.info else 0
        metadata["name"] = (audio.get("title") or [""])[0]
        metadata["artists"] = list(audio.get("artist") or [])
        metadata["album"] = (audio.get("album") or [""])[0]

    except Exception as e:
        logger.debug("Failed to read generic metadata from %s: %s", path, e)

    return metadata


def extract_spotify_url(path: Path) -> str | None:
    """Extract Spotify URL from a file's metadata.

    Checks various tag locations where spotdl stores the source URL.

    Args:
        path: Path to audio file.

    Returns:
        Spotify URL if found, None otherwise.
    """
    metadata = read_file_metadata(path)
    return metadata.get("spotify_url")


def _extract_year(date_str: str) -> int:
    """Extract year from a date string."""
    if not date_str:
        return 0
    try:
        # Try parsing just the year portion
        return int(date_str[:4])
    except (ValueError, IndexError):
        return 0


def _parse_track_number(value: str) -> int:
    """Parse a track number that may be in 'N/M' format."""
    if not value:
        return 0
    try:
        # Handle "3/12" format
        if "/" in value:
            return int(value.split("/")[0])
        return int(value)
    except ValueError:
        return 0
