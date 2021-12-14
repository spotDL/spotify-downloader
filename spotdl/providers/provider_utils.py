import re

from pathlib import Path
from typing import List

from rapidfuzz import fuzz

from spotdl.utils.song_name_utils import format_name


def _match_percentage(str1: str, str2: str, score_cutoff: float = 0) -> float:
    """
    A wrapper around `rapidfuzz.fuzz.partial_ratio` to handle UTF-8 encoded
    emojis that usually cause errors

    `str` `str1` : a random sentence
    `str` `str2` : another random sentence
    `float` `score_cutoff` : minimum score required to consider it a match
        returns 0 when similarity < score_cutoff

    RETURNS `float`
    """

    # ! this will throw an error if either string contains a UTF-8 encoded emoji
    try:
        return fuzz.partial_ratio(str1, str2, processor=None, score_cutoff=score_cutoff)

    # ! we build new strings that contain only alphanumerical characters and spaces
    # ! and return the partial_ratio of that
    except:  # noqa:E722
        new_str1 = "".join(
            each_letter
            for each_letter in str1
            if each_letter.isalnum() or each_letter.isspace()
        )

        new_str2 = "".join(
            each_letter
            for each_letter in str2
            if each_letter.isalnum() or each_letter.isspace()
        )

        return fuzz.partial_ratio(
            new_str1, new_str2, processor=None, score_cutoff=score_cutoff
        )


def _parse_duration(duration: str) -> float:
    """
    Convert string value of time (duration: "25:36:59") to a float value of seconds (92219.0)
    """
    try:
        # {(1, "s"), (60, "m"), (3600, "h")}
        mapped_increments = zip([1, 60, 3600], reversed(duration.split(":")))
        seconds = sum(multiplier * int(time) for multiplier, time in mapped_increments)
        return float(seconds)

    # ! This usually occurs when the wrong string is mistaken for the duration
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _create_song_title(song_name: str, song_artists: List[str]) -> str:
    joined_artists = ", ".join(song_artists)
    return _sanitize_filename(f"{joined_artists} - {song_name}")


def _sanitize_filename(input_str: str) -> str:
    return format_name(input_str)


def _get_smaller_file_path(input_song, output_format: str) -> Path:
    # Only use the first artist if the song path turns out to be too long
    smaller_name = f"{input_song.contributing_artists[0]} - {input_song.song_name}"

    smaller_name = _sanitize_filename(smaller_name)

    try:
        return Path(f"{smaller_name}.{output_format}").resolve()
    except OSError:
        # Expected to happen in the rare case when the saved path is too long,
        # even with the short filename
        raise OSError("Cannot save song due to path issues.")


def _get_converted_file_path(song_obj, output_format: str = None) -> Path:

    # ! we eliminate contributing artist names that are also in the song name, else we
    # ! would end up with things like 'Jetta, Mastubs - I'd love to change the world
    # ! (Mastubs REMIX).mp3' which is kinda an odd file name.

    # also make sure that main artist is included in artistStr even if they
    # are in the song name, for example
    # Lil Baby - Never Recover (Lil Baby & Gunna, Drake).mp3

    artists_filtered = []

    if output_format is None:
        output_format = "mp3"

    for artist in song_obj.contributing_artists:
        if artist.lower() not in song_obj.song_name:
            artists_filtered.append(artist)
        elif artist.lower() is song_obj.contributing_artists[0].lower():
            artists_filtered.append(artist)

    artist_str = ", ".join(artists_filtered)

    converted_file_name = _sanitize_filename(
        f"{artist_str} - {song_obj.song_name}.{output_format}"
    )

    converted_file_path = Path(converted_file_name)

    # ! Checks if a file name is too long (256 max on both linux and windows)
    try:
        if len(str(converted_file_path.resolve().name)) > 256:
            print("Path was too long. Using Small Path.")
            return _get_smaller_file_path(song_obj, output_format)
    except OSError:
        return _get_smaller_file_path(song_obj, output_format)

    return converted_file_path


def _parse_path_template(path_template, song_object, output_format, short=False):
    converted_file_name = path_template

    converted_file_name = converted_file_name.format(
        artist=_sanitize_filename(song_object.contributing_artists[0]),
        title=_sanitize_filename(song_object.song_name),
        album=_sanitize_filename(song_object.album_name),
        playlist=_sanitize_filename(song_object.playlist_name)
        if song_object.playlist_name
        else "",
        artists=_sanitize_filename(
            ", ".join(song_object.contributing_artists)
            if short is False
            else song_object.contributing_artists[0]
        ),
        ext=_sanitize_filename(output_format),
    )

    if len(converted_file_name) > 250:
        return _parse_path_template(
            path_template, song_object, output_format, short=True
        )

    converted_file_path = Path(converted_file_name)

    santitized_parts = []
    for part in converted_file_path.parts:
        match = re.search(r"[^\.*](.*)[^\.*$]", part)
        if match:
            santitized_parts.append(match.group(0))
        else:
            santitized_parts.append(part)

    # Join the parts of the path
    converted_file_path = Path(*santitized_parts)

    return converted_file_path
