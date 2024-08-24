"""
Module for formatting songs into strings.
Contains functions to create search queries and song titles
and file names.
"""

import copy
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from unicodedata import normalize

import pykakasi
from rapidfuzz import fuzz
from slugify import slugify as py_slugify
from yt_dlp.options import create_parser
from yt_dlp.options import optparse as yt_dlp_optparse
from yt_dlp.utils import sanitize_filename

from spotdl.types.song import Song

__all__ = [
    "VARS",
    "JAP_REGEX",
    "DISALLOWED_REGEX",
    "create_song_title",
    "sanitize_string",
    "slugify",
    "format_query",
    "create_search_query",
    "create_file_name",
    "parse_duration",
    "to_ms",
    "restrict_filename",
    "ratio",
    "smart_split",
    "create_path_object",
    "args_to_ytdlp_options",
]

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

KKS = pykakasi.kakasi()

JAP_REGEX = re.compile(
    "[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]"
)

DISALLOWED_REGEX = re.compile(r"[^-a-zA-Z0-9\!\@\$]+")
YT_DLP_PARSER = create_parser()

logger = logging.getLogger(__name__)


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


@lru_cache()
def slugify(string: str) -> str:
    """
    Slugify the string.

    ### Arguments
    - string: the string to slugify

    ### Returns
    - the slugified string
    """

    # Replace ambiguous characters
    if not JAP_REGEX.search(string):
        # If string doesn't have japanese characters
        # return early
        return py_slugify(string, regex_pattern=DISALLOWED_REGEX.pattern)

    # Workaround for japanese characters
    # because slugify incorrectly converts them
    # to latin characters
    normal_slug = py_slugify(
        string,
        regex_pattern=JAP_REGEX.pattern,
    )

    results = KKS.convert(normal_slug)

    result = ""
    for index, item in enumerate(results):
        result += item["hepburn"]
        if not (
            item["kana"] == item["hepburn"]
            or item["kana"] == item["hepburn"]
            or (
                item == results[-1]
                or results[index + 1]["kana"] == results[index + 1]["hepburn"]
            )
        ):
            result += "-"

    return py_slugify(result, regex_pattern=DISALLOWED_REGEX.pattern)


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

    for key, val in [
        ("{list-length}", song.list_length),
        ("{list-position}", song.list_position),
        ("{list-name}", song.list_name),
    ]:
        if not (key in template and val is None):
            continue

        logger.warning(
            "Template contains %s, but it's value is None. Replacing with empty string.",
            key,
        )

        template = template.replace(key, "")
        template = template.replace(r"//", r"/")

    # If template has only {output-ext}, fix it
    if template in ["/.{output-ext}", ".{output-ext}"]:
        template = "{artists} - {title}.{output-ext}"

    # Remove artists from the list that are already in the title
    if short:
        artists = [
            artist
            for artist in song.artists
            if slugify(artist) not in slugify(song.name)
        ]

        # Add the main artist again to the list
        if len(artists) == 0 or artists[0] != song.artists[0]:
            artists.insert(0, song.artists[0])
    else:
        artists = song.artists

    artists_str = ", ".join(artists)

    # the code below is valid, song_list is actually checked for None
    formats = {
        "{title}": song.name,
        "{artists}": song.artists[0] if short is True else artists_str,
        "{artist}": song.artists[0],
        "{album}": song.album_name,
        "{album-artist}": song.album_artist,
        "{genre}": song.genres[0] if song.genres else "",
        "{disc-number}": song.disc_number,
        "{disc-count}": song.disc_count,
        "{duration}": song.duration,
        "{year}": song.year,
        "{original-date}": song.date,
        "{track-number}": f"{int(song.track_number):02d}" if song.track_number else "",
        "{tracks-count}": song.tracks_count,
        "{isrc}": song.isrc,
        "{track-id}": song.song_id,
        "{publisher}": song.publisher,
        "{output-ext}": file_extension,
        "{list-name}": song.list_name,
        "{list-position}": str(song.list_position).zfill(len(str(song.list_length))),
        "{list-length}": song.list_length,
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
    # append {artist} - {title} at the beginning of the template
    if not any(key in template for key in VARS):
        template = "{artist} - {title}" + template

    return format_query(song, template, santitize, file_extension, short=short)


def create_file_name(
    song: Song,
    template: str,
    file_extension: str,
    restrict: Optional[str] = None,
    short: bool = False,
    file_name_length: Optional[int] = None,
) -> Path:
    """
    Create the file name for the song, by replacing template variables with the actual values.

    ### Arguments
    - song: the song object
    - template: the template string
    - file_extension: the file extension to use
    - restrict: sanitization to apply to the filename
    - short: whether to use the short version of the template
    - file_name_length: the maximum length of the file name

    ### Returns
    - the formatted string as a Path object
    """

    temp_song = copy.deepcopy(song)

    # If template does not contain any of the keys,
    # append {artists} - {title}.{output-ext} to it
    if not any(key in template for key in VARS) and template != "":
        template += "/{artists} - {title}.{output-ext}"

    if template == "":
        template = "{artists} - {title}.{output-ext}"

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

    file = create_path_object(formatted_string)

    length_limit = file_name_length or 255

    # Check if the file name length is greater than the limit
    if len(file.name) < length_limit:
        # Restrict the filename if needed
        if restrict and restrict != "none":
            return restrict_filename(file, restrict == "strict")

        return file

    if short is False:
        return create_file_name(
            song,
            template,
            file_extension,
            restrict=restrict,
            short=True,
            file_name_length=length_limit,
        )

    non_template_chars = re.findall(r"(?<!{)[^{}]+(?![^{}]*})", template)
    half_length = int((length_limit * 0.50) - (len("".join(non_template_chars)) / 2))

    # Path template is already short, but we still can't create a file
    # so we reduce it even further
    is_long_artist = len(temp_song.artist) > half_length
    is_long_title = len(temp_song.name) > half_length

    path_separator = "/" if "/" in template else "\\"
    name_template_parts = template.rsplit(path_separator, 1)
    name_template = (
        name_template_parts[1]
        if len(name_template_parts) > 1
        else name_template_parts[0]
    )

    if is_long_artist:
        logger.warning(
            "%s: Song artist is too long. Using only part of song artist.",
            temp_song.display_name,
        )

        temp_song.artist = smart_split(temp_song.artist, half_length, None)
        temp_song.artists = [temp_song.artist]

    if is_long_title:
        logger.warning(
            "%s: File name is too long. Using only part of the song title.",
            temp_song.display_name,
        )

        temp_song.name = smart_split(temp_song.name, half_length, None)

    new_file = create_path_object(
        format_query(
            song=temp_song,
            template=name_template,
            santitize=True,
            file_extension=file_extension,
            short=short,
        )
    )

    if len(new_file.name) > length_limit:
        logger.warning(
            "File name is still too long. "
            "Using default file name with shortened artist and title."
        )

        if template == "{artist} - {title}.{output-ext}":
            raise ValueError(
                "File name is still too long, "
                "but the template is already short. "
                "Please try other template, "
                "increase the file name length limit."
            )

        return create_file_name(
            temp_song,
            "{artist} - {title}.{output-ext}",
            file_extension,
            restrict=restrict,
            short=True,
            file_name_length=length_limit,
        )

    return new_file


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


def restrict_filename(pathobj: Path, strict: bool = True) -> Path:
    """
    Sanitizes the filename part of a Path object. Returns modified object.

    ### Arguments
    - pathobj: the Path object to sanitize
    - strict: whether sanitization should be strict

    ### Returns
    - the modified Path object

    ### Notes
    - Based on the `sanitize_filename` function from yt-dlp
    """
    if strict:
        result = sanitize_filename(pathobj.name, True, False)  # type: ignore
        result = result.replace("_-_", "-")
    else:
        result = (
            normalize("NFKD", pathobj.name).encode("ascii", "ignore").decode("utf-8")
        )

    if not result:
        result = "_"

    return pathobj.with_name(result)


@lru_cache()
def ratio(string1: str, string2: str) -> float:
    """
    Wrapper for fuzz.ratio
    with lru_cache

    ### Arguments
    - string1: the first string
    - string2: the second string

    ### Returns
    - the ratio
    """

    return fuzz.ratio(string1, string2)


def smart_split(
    string: str, max_length: int, separators: Optional[List[str]] = None
) -> str:
    """
    Split a string into a list of strings
    with a maximum length of max_length.
    Stops at the first separator that produces a string
    with a length less than max_length.

    ### Arguments
    - string: the string to split
    - max_length: the maximum length of string
    - separators: the separators to split the string with

    ### Returns
    - the new string
    """

    if separators is None:
        separators = ["-", ",", " ", ""]

    for separator in separators:
        parts = string.split(separator if separator != "" else None)
        new_string = separator.join(parts[:1])
        for part in parts[1:]:
            if len(new_string) + len(separator) + len(part) > max_length:
                break
            new_string += separator + part

        if len(new_string) <= max_length:
            return new_string

    return string[:max_length]


def create_path_object(string: str) -> Path:
    """
    Create a Path object from a string.
    Sanitizes the filename part of the Path object.

    ### Arguments
    - string: the string to convert

    ### Returns
    - the Path object
    """

    # Parse template as Path object
    file = Path(string)

    santitized_parts = []
    for part in file.parts:
        match = re.search(r"[^\.*](.*)[^\.*$]", part)
        if match and part != ".spotdl":
            santitized_parts.append(match.group(0))
        else:
            santitized_parts.append(part)

    # Join the parts of the path
    return Path(*santitized_parts)


def args_to_ytdlp_options(
    argument_list: List[str], defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert a list of arguments to a dictionary of options.

    ### Arguments
    - argument_list: the list of arguments
    - defaults: the default options

    ### Returns
    - the dictionary of options
    """

    new_args = YT_DLP_PARSER.parse_args(argument_list, yt_dlp_optparse.Values(defaults))

    return vars(new_args[0])
