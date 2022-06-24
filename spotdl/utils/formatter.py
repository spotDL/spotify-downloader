"""
Module for formatting songs into strings.
Contains functions to create search queries and song titles
and file names.
"""

import re
import warnings

from typing import List, Optional
from pathlib import Path
from slugify import slugify
from yt_dlp.utils import sanitize_filename

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
    "{list-name}",
    "{output-ext}",
]


def create_song_title(song_name: str, song_artists: List[str]) -> str:
    """
    Create the song title.

    ### Arguments
    - song_name: the name of the song
    - song_artists: the list of artists of the song

    ### Returns
    - the song title

    ### Notes
    - Example: "Artist1, Artist2 - Song Name"

    """

    joined_artists = ", ".join(song_artists)
    if len(song_artists) >= 1:
        return f"{joined_artists} - {song_name}"

    return song_name


def sanitize_string(string: str) -> str:
    """
    Sanitize the filename to be used in the file system.

    ### Arguments
    - string: the string to sanitize

    ### Returns
    - the sanitized string
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
) -> str:
    """
    Replace template variables with the actual values.

    ### Arguments
    - song: the song object
    - template: the template string
    - santitize: whether to sanitize the string
    - file_extension: the file extension to use
    - short: whether to use the short version of the template

    ### Returns
    - the formatted string
    """

    if "{output-ext}" in template and file_extension is None:
        raise ValueError("file_extension is None, but template contains {output-ext}")

    if (
        any(k in template for k in ["{list-length}", "{list-position}", "{list-name}"])
        and song.song_list is None
    ):
        # If the template contains {list-length} or {list-position} or {list-name},
        # but the song_list is None, replace them with empty strings
        for k in ["{list-length}", "{list-position}", "{list-name}"]:
            template = template.replace(k, "")
            template = template.replace(r"//", r"/")

    # If template has only {output-ext}, fix it
    # This can happen if the template consits of only list values
    # and song.song_list is None
    if template in ["/.{output-ext}", ".{output-ext}"]:
        template = "{artists} - {title}.{output-ext}"

    # Remove artists from the list that are already in the title
    artists = [
        artist for artist in song.artists if slugify(artist) not in slugify(song.name)
    ]

    # Add the main artist again to the list
    if len(artists) == 0 or artists[0] != song.artists[0]:
        artists.insert(0, song.artists[0])

    artists_str = ", ".join(artists)

    # the code below is valid, song_list is actually checked for None
    formats = {
        "{title}": song.name,
        "{artists}": song.artists[0] if short is True else artists_str,
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
        "{output-ext}": file_extension,
    }

    if song.song_list and any(
        k in template for k in ["{list-length}", "{list-position}", "{list-name}"]
    ):
        try:
            index = song.song_list.songs.index(song)
        except ValueError:
            index = song.song_list.urls.index(song.url)

        formats.update(
            {
                "{list-name}": song.song_list.name,  # type: ignore
                "{list-position}": str(index + 1).zfill(
                    len(str(song.song_list.length))
                ),
                "{list-length}": song.song_list.length,
            }
        )

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

    ### Arguments
    - song: the song object
    - template: the template string
    - santitize: whether to sanitize the string
    - file_extension: the file extension to use
    - short: whether to use the short version of the template

    ### Returns
    - the formatted string
    """

    # If template does not contain any of the keys,
    # append {artist} - {title} at the beggining of the template
    if not any(key in template for key in VARS):
        template = "{artist} - {title}" + template

    return format_query(song, template, santitize, file_extension, short=short)


def create_file_name(
    song: Song,
    template: str,
    file_extension: str,
    short: bool = False,
) -> Path:
    """
    Create the file name for the song, by replacing template variables with the actual values.

    ### Arguments
    - song: the song object
    - template: the template string
    - file_extension: the file extension to use
    - short: whether to use the short version of the template

    ### Returns
    - the formatted string as a Path object
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
        song=song,
        template=template,
        santitize=True,
        file_extension=file_extension,
        short=short,
    )

    # Parse template as Path object
    file = Path(formatted_string)

    santitized_parts = []
    for part in file.parts:
        match = re.search(r"[^\.*](.*)[^\.*$]", part)
        if match and part != ".spotdl":
            santitized_parts.append(match.group(0))
        else:
            santitized_parts.append(part)

    # Join the parts of the path
    file = Path(*santitized_parts)

    # Check if the file name length is greater than 255
    if len(file.name) > 255:
        # If the file name length is greater than 255,
        # and we are already using the short version of the template,
        # fallback to default template
        if short is True:
            warnings.warn(
                f"{song.display_name}: File name is too long. Using the default template."
            )

            return create_file_name(
                song=song,
                template="/{artist} - {title}.{output-ext}",
                file_extension=file_extension,
                short=short,
            )

        # This will probably never occur, but just in case
        if short is True and template == "/{artist} - {title}.{output-ext}":
            raise RecursionError(
                f'"{song.display_name} is too long to be shortened. File a bug report on GitHub'
            )

        return create_file_name(
            song,
            template,
            file_extension,
            short=True,
        )

    return file


def parse_duration(duration: Optional[str]) -> float:
    """
    Convert string value of time (duration: "25:36:59") to a float value of seconds (92219.0)

    ### Arguments
    - duration: the string value of time

    ### Returns
    - the float value of seconds
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


def to_ms(
    string: Optional[str] = None, precision: Optional[int] = None, **kwargs
) -> float:
    """
    Convert a string to milliseconds.

    ### Arguments
    - string: the string to convert
    - precision: the number of decimals to round to
    - kwargs: the keyword args to convert

    ### Returns
    - the milliseconds

    ### Notes
    - You can either pass a string,
    - or a set of keyword args ("hour", "min", "sec", "ms") to convert.
    - If "precision" is set, the result is rounded to the number of decimals given.
    - From: https://gist.github.com/Hellowlol/5f8545e999259b4371c91ac223409209
    """

    if string:
        hour = int(string[0:2])
        minute = int(string[3:5])
        sec = int(string[6:8])
        milliseconds = int(string[10:11])
    else:
        hour = int(kwargs.get("hour", 0))
        minute = int(kwargs.get("min", 0))
        sec = int(kwargs.get("sec", 0))
        milliseconds = int(kwargs.get("ms", 0))

    result = (
        (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + milliseconds
    )

    if precision and isinstance(precision, int):
        return round(result, precision)

    return result


def restrict_filename(pathobj: Path) -> Path:
    """
    Sanitizes the filename part of a Path object. Returns modified object.

    ### Arguments
    - pathobj: the Path object to sanitize

    ### Returns
    - the modified Path object

    ### Notes
    - Based on the `sanitize_filename` function from yt-dlp
    """

    result = sanitize_filename(pathobj.name, True, False)
    result = result.replace("_-_", "-")

    if not result:
        result = "_"

    return pathobj.with_name(result)
