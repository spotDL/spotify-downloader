import re

from typing import List, Optional
from pathlib import Path

from spotdl.types import Song

VARS = [
    "{title}",
    "{artists}",
    "{artist}",
    "{album}",
    "{album-artist}",
    "{genre}",
    "{disc-number}",
    "{disc-count}",
    "{duration}",
    "{year}",
    "{original-date}",
    "{track-number}",
    "{tracks-count}",
    "{isrc}",
    "{track-id}",
    "{publisher}",
    "{list-length}",
    "{list-position}",
    "{output-ext}",
]


def create_song_title(song_name: str, song_artists: List[str]) -> str:
    """
    Create the song title.
    """

    joined_artists = ", ".join(song_artists)
    if len(song_artists) >= 1:
        return f"{joined_artists} - {song_name}"

    return song_name


def sanitize_string(string: str) -> str:
    """
    Sanitize the filename to be used in the file system.
    """

    output = string

    # this is windows specific (disallowed chars)
    output = "".join(char for char in output if char not in "/?\\*|<>")

    # double quotes (") and semi-colons (:) are also disallowed characters but we would
    # like to retain their equivalents, so they aren't removed in the prior loop
    output = output.replace('"', "'").replace(":", "-")

    return output


def format_query(
    song: Song,
    template: str,
    santitize: bool,
    file_extension: Optional[str] = None,
    short: bool = False,
    song_list: List[Song] = None,
) -> str:
    """
    Replace template variables with the actual values.
    """

    if "{output-ext}" in template and file_extension is None:
        raise ValueError("file_extension is None, but template contains {output-ext}")

    artists = ", ".join(song.artists)
    position = (
        str(song_list.index(song) + 1).zfill(len(str(len(song_list))))
        if song_list
        else ""
    )

    formats = {
        "{title}": song.name,
        "{artists}": song.artists[0] if short is True else artists,
        "{artist}": song.artists[0],
        "{album}": song.album_name,
        "{album-artist}": song.album_artist,
        "{genre}": song.genres[0] if len(song.genres) > 0 else "",
        "{disc-number}": song.disc_number,
        "{disc-count}": song.disc_count,
        "{duration}": song.duration,
        "{year}": song.year,
        "{original-date}": song.date,
        "{track-number}": song.track_number,
        "{tracks-count}": song.tracks_count,
        "{isrc}": song.isrc,
        "{track-id}": song.song_id,
        "{publisher}": song.publisher,
        "{list-position}": position,
        "{list-length}": len(song_list) if song_list else "",
        "{output-ext}": file_extension,
    }

    if santitize:
        # sanitize the values in formats dict
        for key, value in formats.items():
            if value is None:
                continue

            formats[key] = sanitize_string(str(value))

    # Replace all the keys with the values
    for key, value in formats.items():
        template = template.replace(key, str(value))

    return template


def create_search_query(
    song: Song,
    template: str,
    santitize: bool,
    file_extension: Optional[str] = None,
    short: bool = False,
) -> str:
    """
    Create the search query for the song.
    """

    # If template does not contain any of the keys,
    # append {artist} - {title} at the beggining of the template
    if not any(key in template for key in VARS):
        template = "{artist} - {title}" + template

    return format_query(song, template, santitize, file_extension, short)


def create_file_name(
    song: Song,
    template: str,
    file_extension: str,
    short: bool = False,
    song_list: List[Song] = None,
) -> Path:
    """
    Create the file name for the song.
    Replaces template variables with the actual values.
    """

    # If template does not contain any of the keys,
    # append {artists} - {title}.{output-ext} to it
    if not any(key in template for key in VARS):
        template += "/{artists} - {title}.{output-ext}"

    # If template ends with a slash. Does not have a file name with extension
    # at the end of the template, append {artists} - {title}.{output-ext} to it
    if template.endswith("/") or template.endswith(r"\\") or template.endswith("\\\\"):
        template += "/{artists} - {title}.{output-ext}"

    # If template does not end with {output-ext}, append it to the end of the template
    if not template.endswith(".{output-ext}"):
        template += ".{output-ext}"

    formatted_string = format_query(
        song, template, True, file_extension, short, song_list=song_list
    )

    # Parse template as Path object
    file = Path(formatted_string)

    santitized_parts = []
    for part in file.parts:
        match = re.search(r"[^\.*](.*)[^\.*$]", part)
        if match:
            santitized_parts.append(match.group(0))
        else:
            santitized_parts.append(part)

    # Join the parts of the path
    file = Path(*santitized_parts)

    # Check if the file name length is greater than 255
    if len(file.name) > 255:
        return create_file_name(
            song, template, file_extension, short=True, song_list=song_list
        )

    return file


def parse_duration(duration: Optional[str]) -> float:
    """
    Convert string value of time (duration: "25:36:59") to a float value of seconds (92219.0)
    """

    if duration is None:
        return 0.0

    try:
        # {(1, "s"), (60, "m"), (3600, "h")}
        mapped_increments = zip([1, 60, 3600], reversed(duration.split(":")))
        seconds = sum(multiplier * int(time) for multiplier, time in mapped_increments)
        return float(seconds)

    # This usually occurs when the wrong string is mistaken for the duration
    except (ValueError, TypeError, AttributeError):
        return 0.0
