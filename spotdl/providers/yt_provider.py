# ===============
# === Imports ===
# ===============

from pytube.__main__ import YouTube
from unidecode import unidecode
from pytube import Search

# ! Just for static typing
from typing import List, Optional

from spotdl.providers.provider_utils import (
    _match_percentage,
    _create_song_title,
)


def search_and_get_best_match(
    song_name: str,
    song_artists: List[str],
    song_duration: int,
    isrc: str,
) -> Optional[str]:
    """
    `str` `song_name` : name of song

    `list<str>` `song_artists` : list containing name of contributing artists

    `str` `song_album_name` : name of song's album

    `int` `song_duration` : duration of the song

    `str` `isrc` :  code for identifying sound recordings and music video recordings

    RETURNS `str` : link of the best match
    """

    # if isrc is not None then we try to find song with it
    if isrc is not None:
        isrc_results = Search(isrc).results

        if isrc_results and len(isrc_results) == 1:
            isrc_result = isrc_results[0]

            if isrc_result is not None and isrc_result.watch_url is not None:
                return isrc_result.watch_url

    song_title = _create_song_title(song_name, song_artists).lower()

    # Query YTM by songs only first, this way if we get correct result on the first try
    # we don't have to make another request to ytmusic api that could result in us
    # getting rate limited sooner
    results = Search(song_title).results

    if results is None:
        print("Couldn't find the song on YouTube")
        return None

    # Order results
    results = _order_yt_results(results, song_name, song_artists, song_duration)

    # No matches found
    if len(results) == 0:
        return None

    result_items = list(results.items())

    # Sort results by highest score
    sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

    # ! In theory, the first 'TUPLE' in sorted_results should have the highest match
    # ! value, we send back only the link
    return sorted_results[0][0]


def _order_yt_results(
    results: List[YouTube],
    song_name: str,
    song_artists: List[str],
    song_duration: int,
) -> dict:

    # Assign an overall avg match value to each result
    links_with_match_value = {}

    for result in results:
        # ! skip results without videoId, this happens if you are country restricted or
        # ! video is unavailabe
        if result.video_id is None:
            continue

        lower_song_name = song_name.lower()
        lower_result_name = result.title.lower()

        sentence_words = lower_song_name.replace("-", " ").split(" ")

        common_word = False

        # ! check for common word
        for word in sentence_words:
            if word != "" and word in lower_result_name:
                common_word = True

        # ! if there are no common words, skip result
        if common_word is False:
            continue

        # Find artist match
        # ! match  = (no of artist names in result) / (no. of artist names on spotify) * 100
        artist_match_number = 0

        # ! we use fuzzy matching because YouTube spellings might be mucked up
        # ! i.e if video
        for artist in song_artists:
            # ! something like _match_percentage('rionos', 'aiobahn, rionos Motivation
            # ! (remix)' would return 100, so we're absolutely corrent in matching
            # ! artists to song name.
            if _match_percentage(
                str(unidecode(artist.lower())), str(unidecode(result.title).lower()), 85
            ):
                artist_match_number += 1

        # ! Skip if there are no artists in common, (else, results like 'Griffith Swank -
        # ! Madness' will be the top match for 'Ruelle - Madness')
        if artist_match_number == 0:
            continue

        artist_match = (artist_match_number / len(song_artists)) * 100
        song_title = _create_song_title(song_name, song_artists).lower()
        name_match = round(
            _match_percentage(
                str(unidecode(result.title.lower())), str(unidecode(song_title)), 60
            ),
            ndigits=3,
        )

        # skip results with name match of 0, these are obviously wrong
        # but can be identified as correct later on due to other factors
        # such as time_match or artist_match
        if name_match == 0:
            continue

        # Find duration match
        # ! time match = 100 - (delta(duration)**2 / original duration * 100)
        # ! difference in song duration (delta) is usually of the magnitude of a few
        # ! seconds, we need to amplify the delta if it is to have any meaningful impact
        # ! wen we calculate the avg match value
        delta = result.length - song_duration  # ! check this
        non_match_value = (delta ** 2) / song_duration * 100

        time_match = 100 - non_match_value

        average_match = (artist_match + name_match + time_match) / 3

        # the results along with the avg Match
        links_with_match_value[result.watch_url] = average_match

    return links_with_match_value
