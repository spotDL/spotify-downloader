"""
CSV Import module for loading songs from Exportify CSV exports.

Exportify (https://exportify.net) exports Spotify playlists and liked songs
as CSV files. This module parses those CSVs and creates Song objects that
spotDL can download, bypassing the Spotify Web API's /me/tracks endpoint
which requires Premium on the app owner's account.

Exportify CSV columns (in order):
    Spotify ID, Artist IDs, Track Name, Album Name, Artist Name(s),
    Release Date, Duration (ms), Popularity, Added By, Added At,
    Genres, Record Label, Danceability, Energy, Key, Loudness, Mode,
    Speechiness, Acousticness, Instrumentalness, Liveness, Valence,
    Tempo, Time Signature, Spotify URL
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from spotdl.types.song import Song, SongList

__all__ = ["CSVImport", "CSVImportError"]

logger = logging.getLogger(__name__)

# Expected Exportify column headers (case-insensitive matching)
EXPORTIFY_COLUMNS = [
    "spotify id",
    "artist ids",
    "track name",
    "album name",
    "artist name(s)",
    "release date",
    "duration (ms)",
    "popularity",
    "added by",
    "added at",
    "genres",
    "record label",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time signature",
    "spotify url",  # Not always present in older exports
]

# Minimum required columns for a valid import
REQUIRED_COLUMNS = {"track name", "artist name(s)"}


class CSVImportError(Exception):
    """
    Base class for all exceptions related to CSV import.
    """


def _detect_encoding(file_path: Path) -> str:
    """
    Detect file encoding by checking for BOM markers.
    Falls back to utf-8.

    ### Arguments
    - file_path: Path to the CSV file.

    ### Returns
    - The detected encoding string.
    """
    with open(file_path, "rb") as f:
        raw = f.read(4)

    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    return "utf-8"


def _normalize_header(header: str) -> str:
    """
    Normalize a CSV header for matching: lowercase, strip whitespace.
    """
    return header.strip().lower()


def _parse_artists(artist_string: str) -> List[str]:
    """
    Parse the 'Artist Name(s)' field from Exportify.
    Artists are comma-separated in the CSV.

    ### Arguments
    - artist_string: The raw artist names string.

    ### Returns
    - List of individual artist names.
    """
    if not artist_string or not artist_string.strip():
        return []

    # Exportify separates multiple artists with ", "
    artists = [a.strip() for a in artist_string.split(",")]
    return [a for a in artists if a]


def _parse_genres(genre_string: str) -> List[str]:
    """
    Parse the 'Genres' field from Exportify.

    ### Arguments
    - genre_string: The raw genres string.

    ### Returns
    - List of genre strings.
    """
    if not genre_string or not genre_string.strip():
        return []

    # Genres may be comma-separated or semicolon-separated
    for sep in [",", ";"]:
        if sep in genre_string:
            return [g.strip() for g in genre_string.split(sep) if g.strip()]

    return [genre_string.strip()] if genre_string.strip() else []


def _safe_int(value: str, default: Optional[int] = None) -> Optional[int]:
    """Safely convert a string to int, returning default on failure."""
    if not value or not value.strip():
        return default
    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return default


def _build_spotify_url(song_id: str) -> str:
    """Build a Spotify track URL from a track ID."""
    if song_id.startswith("http"):
        return song_id
    return f"https://open.spotify.com/track/{song_id}"


def parse_csv_file(file_path: Path) -> Tuple[Dict[str, Any], List[Song]]:
    """
    Parse an Exportify CSV file and return metadata + Song objects.

    ### Arguments
    - file_path: Path to the CSV file.

    ### Returns
    - Tuple of (metadata dict, list of Song objects).

    ### Raises
    - CSVImportError: If the file cannot be parsed or is invalid.
    """
    if not file_path.exists():
        raise CSVImportError(f"CSV file not found: {file_path}")

    if not file_path.is_file():
        raise CSVImportError(f"Path is not a file: {file_path}")

    encoding = _detect_encoding(file_path)
    logger.info("Reading CSV file: %s (encoding: %s)", file_path, encoding)

    try:
        with open(file_path, "r", encoding=encoding, newline="") as f:
            # Sniff delimiter (Exportify uses comma, but be flexible)
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel  # Default to standard CSV

            reader = csv.reader(f, dialect)

            # Read and validate header
            try:
                raw_headers = next(reader)
            except StopIteration:
                raise CSVImportError("CSV file is empty")

            headers = [_normalize_header(h) for h in raw_headers]

            # Build column index map
            col_map = {}
            for i, header in enumerate(headers):
                col_map[header] = i

            # Check for required columns
            missing = REQUIRED_COLUMNS - set(col_map.keys())
            if missing:
                # Try fuzzy matching for common variations
                header_aliases = {
                    "track name": ["name", "title", "song name", "song title", "track"],
                    "artist name(s)": [
                        "artist",
                        "artists",
                        "artist names",
                        "artist name",
                    ],
                }
                for req_col in list(missing):
                    for alias in header_aliases.get(req_col, []):
                        if alias in col_map:
                            col_map[req_col] = col_map[alias]
                            missing.discard(req_col)
                            break

            if missing:
                raise CSVImportError(
                    f"CSV is missing required columns: {', '.join(missing)}. "
                    f"Found columns: {', '.join(headers)}. "
                    f"Make sure you're using an Exportify CSV export."
                )

            # Parse rows into Song objects
            songs: List[Song] = []
            skipped = 0
            errors_list: List[str] = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    song = _row_to_song(row, col_map, row_num)
                    if song is not None:
                        songs.append(song)
                    else:
                        skipped += 1
                except Exception as exc:
                    skipped += 1
                    error_msg = f"Row {row_num}: {exc}"
                    errors_list.append(error_msg)
                    logger.debug("Skipping row %d: %s", row_num, exc)

            if errors_list:
                logger.warning(
                    "Encountered %d errors while parsing CSV. "
                    "First error: %s",
                    len(errors_list),
                    errors_list[0],
                )

            logger.info(
                "Parsed %d songs from CSV (%d skipped)",
                len(songs),
                skipped,
            )

            if len(songs) == 0:
                raise CSVImportError(
                    "No valid songs found in CSV file. "
                    "Make sure the file is a valid Exportify export."
                )

            metadata = {
                "name": file_path.stem,
                "url": f"csv:{file_path.name}",
            }

            return metadata, songs

    except UnicodeDecodeError:
        # Retry with latin-1 as a fallback
        logger.warning("UTF-8 decode failed, retrying with latin-1 encoding")
        try:
            return _parse_with_encoding(file_path, "latin-1")
        except Exception as exc:
            raise CSVImportError(
                f"Could not decode CSV file with any supported encoding: {exc}"
            ) from exc
    except CSVImportError:
        raise
    except Exception as exc:
        raise CSVImportError(f"Failed to parse CSV file: {exc}") from exc


def _parse_with_encoding(
    file_path: Path, encoding: str
) -> Tuple[Dict[str, Any], List[Song]]:
    """
    Parse CSV with a specific encoding (fallback path).
    """
    with open(file_path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)

        raw_headers = next(reader)
        headers = [_normalize_header(h) for h in raw_headers]
        col_map = {header: i for i, header in enumerate(headers)}

        missing = REQUIRED_COLUMNS - set(col_map.keys())
        if missing:
            raise CSVImportError(
                f"CSV is missing required columns: {', '.join(missing)}"
            )

        songs = []
        for row_num, row in enumerate(reader, start=2):
            try:
                song = _row_to_song(row, col_map, row_num)
                if song is not None:
                    songs.append(song)
            except Exception as exc:
                logger.debug("Skipping row %d: %s", row_num, exc)

        metadata = {
            "name": file_path.stem,
            "url": f"csv:{file_path.name}",
        }

        return metadata, songs


def _get_col(row: list, col_map: dict, col_name: str, default: str = "") -> str:
    """
    Safely get a column value from a row.
    """
    idx = col_map.get(col_name)
    if idx is None or idx >= len(row):
        return default
    return row[idx].strip() if row[idx] else default


def _row_to_song(
    row: list, col_map: dict, row_num: int
) -> Optional[Song]:
    """
    Convert a single CSV row to a Song object.

    ### Arguments
    - row: The CSV row as a list of strings.
    - col_map: Mapping of column names to indices.
    - row_num: The row number (for error reporting).

    ### Returns
    - Song object, or None if the row should be skipped.
    """
    track_name = _get_col(row, col_map, "track name")
    artist_names_raw = _get_col(row, col_map, "artist name(s)")

    # Skip empty rows
    if not track_name:
        return None

    artists = _parse_artists(artist_names_raw)
    if not artists:
        logger.debug("Row %d: No artist found for '%s', skipping", row_num, track_name)
        return None

    # Extract all available fields
    song_id = _get_col(row, col_map, "spotify id")
    album_name = _get_col(row, col_map, "album name")
    release_date = _get_col(row, col_map, "release date")
    duration_ms_str = _get_col(row, col_map, "duration (ms)")
    popularity_str = _get_col(row, col_map, "popularity")
    genres_raw = _get_col(row, col_map, "genres")
    record_label = _get_col(row, col_map, "record label")
    spotify_url = _get_col(row, col_map, "spotify url")

    # Compute derived values
    duration_ms = _safe_int(duration_ms_str)
    duration_sec = int(duration_ms / 1000) if duration_ms else None
    popularity = _safe_int(popularity_str)
    genres = _parse_genres(genres_raw)
    year = None
    if release_date:
        try:
            year = int(release_date[:4])
        except (ValueError, IndexError):
            year = None

    # Build the URL — prefer explicit Spotify URL column, fall back to ID
    url = None
    if spotify_url and "open.spotify.com" in spotify_url:
        url = spotify_url
    elif song_id and len(song_id) >= 10:
        url = _build_spotify_url(song_id)

    if not url:
        logger.debug(
            "Row %d: No Spotify URL or ID for '%s - %s', skipping",
            row_num,
            artists[0],
            track_name,
        )
        return None

    # Create Song object with all available data
    song = Song.from_missing_data(
        name=track_name,
        artists=artists,
        artist=artists[0],
        genres=genres,
        album_name=album_name if album_name else None,
        album_artist=artists[0],  # Best guess from CSV data
        duration=duration_sec,
        year=year,
        date=release_date if release_date else None,
        song_id=song_id if song_id else None,
        explicit=None,  # Exportify doesn't export this
        publisher=record_label if record_label else None,
        url=url,
        popularity=popularity,
        isrc=None,  # Not in Exportify CSV
        cover_url=None,  # Will be fetched when reinitializing
    )

    return song


@dataclass(frozen=True)
class CSVImport(SongList):
    """
    CSVImport class for handling songs loaded from Exportify CSV files.
    Acts as a drop-in replacement for the Saved class when the API is unavailable.
    """

    @staticmethod
    def get_metadata(url: str) -> Tuple[Dict[str, Any], List[Song]]:
        """
        Returns metadata for a CSV import.

        ### Arguments
        - url: Path to the CSV file (prefixed with "csv:" or raw path).

        ### Returns
        - metadata: A dictionary containing the metadata for the import.
        - songs: A list of Song objects.
        """
        # Strip the "csv:" prefix if present
        if url.startswith("csv:"):
            file_path = Path(url[4:])
        else:
            file_path = Path(url)

        return parse_csv_file(file_path)

    @classmethod
    def from_csv_path(
        cls, csv_path: str, fetch_songs: bool = False
    ) -> "CSVImport":
        """
        Create a CSVImport object directly from a file path.

        ### Arguments
        - csv_path: Path to the Exportify CSV file.
        - fetch_songs: Whether to re-fetch song metadata from Spotify API.
                       Default False since we want to avoid API calls.

        ### Returns
        - CSVImport object containing all songs from the CSV.
        """
        file_path = Path(csv_path)
        metadata, songs = parse_csv_file(file_path)
        urls = [song.url for song in songs if song.url]

        if fetch_songs:
            from spotdl.types.song import Song as SongClass

            fetched = []
            for song in songs:
                try:
                    if song.url:
                        fetched.append(SongClass.from_url(song.url))
                    else:
                        fetched.append(song)
                except Exception as exc:
                    logger.warning(
                        "Could not fetch metadata for %s: %s",
                        song.display_name,
                        exc,
                    )
                    fetched.append(song)
            songs = fetched

        return cls(**metadata, urls=urls, songs=songs)
