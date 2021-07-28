import requests

from typing import List
from rapidfuzz import fuzz
from bs4 import BeautifulSoup


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
        return fuzz.partial_ratio(str1, str2, score_cutoff=score_cutoff)

    # ! we build new strings that contain only alphanumerical characters and spaces
    # ! and return the partial_ratio of that
    except:  # noqa:E722
        new_str1 = ""

        for each_letter in str1:
            if each_letter.isalnum() or each_letter.isspace():
                new_str1 += each_letter

        new_str2 = ""

        for each_letter in str2:
            if each_letter.isalnum() or each_letter.isspace():
                new_str2 += each_letter

        return fuzz.partial_ratio(new_str1, new_str2, score_cutoff=score_cutoff)


def _parse_duration(duration: str) -> float:
    """
    Convert string value of time (duration: "25:36:59") to a float value of seconds (92219.0)
    """
    try:
        # {(1, "s"), (60, "m"), (3600, "h")}
        mapped_increments = zip([1, 60, 3600], reversed(duration.split(":")))
        seconds = 0
        for multiplier, time in mapped_increments:
            seconds += multiplier * int(time)

        return float(seconds)

    # ! This usually occurs when the wrong string is mistaken for the duration
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _create_song_title(song_name: str, song_artists: List[str]) -> str:
    joined_artists = ", ".join(song_artists)
    return f"{joined_artists} - {song_name}".lower()


def _get_song_lyrics(song_name: str, song_artists: List[str]) -> str:
    """
    `str` `song_name` : name of song

    `list<str>` `song_artists` : list containing name of contributing artists

    RETURNS `str`: Lyrics of the song.

    Gets the metadata of the song.
    """

    headers = {
        "Authorization": "Bearer alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG",
    }
    api_search_url = "https://api.genius.com/search"
    search_query = f'{song_name} {", ".join(song_artists)}'

    try:
        api_response = requests.get(
            api_search_url, params={"q": search_query}, headers=headers
        ).json()

        song_id = api_response["response"]["hits"][0]["result"]["id"]
        song_api_url = f"https://api.genius.com/songs/{song_id}"

        api_response = requests.get(song_api_url, headers=headers).json()

        song_url = api_response["response"]["song"]["url"]

        genius_page = requests.get(song_url)
        soup = BeautifulSoup(genius_page.text, "html.parser")
        lyrics_div = soup.select_one("div.lyrics")

        if lyrics_div is not None:
            return lyrics_div.get_text().strip()

        return ""
    except:  # noqa: E722
        return ""
