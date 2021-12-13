# ===============
# === Imports ===
# ===============

# ! Just for static typing
from ytmusicapi import YTMusic
from unidecode import unidecode
from typing import List, Optional

from spotdl.providers.provider_utils import (
    _match_percentage,
    _parse_duration,
    _create_song_title,
)


# ! YTMusic api client
ytm_client = YTMusic()


def search_and_get_best_match(
    song_name: str,
    song_artists: List[str],
    song_album_name: str,
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
        isrc_results = _query_and_simplify(isrc, "songs")

        if len(isrc_results) == 1:
            isrc_result = isrc_results[0]

            name_match = isrc_result["name"].lower() == song_name.lower()

            delta = isrc_result["length"] - song_duration
            non_match_value = (delta ** 2) / song_duration * 100

            time_match = 100 - non_match_value

            if (
                isrc_result is not None
                and "link" in isrc_result
                and name_match
                and time_match > 90
            ):
                return isrc_result["link"]

    song_title = _create_song_title(song_name, song_artists).lower()

    # Query YTM by songs only first, this way if we get correct result on the first try
    # we don't have to make another request to ytmusic api that could result in us
    # getting rate limited sooner
    song_results = _query_and_simplify(song_title, "songs")

    # Order results
    songs = _order_ytm_results(
        song_results, song_name, song_artists, song_album_name, song_duration
    )

    # song type results are always more accurate than video type, so if we get score of 80 or above
    # we are almost 100% sure that this is the correct link
    if len(songs) != 0:
        # get the result with highest score
        best_result = max(songs, key=lambda k: songs[k])

        if songs[best_result] >= 80:
            return best_result

    # We didn't find the correct song on the first try so now we get video type results
    # add them to song_results, and get the result with highest score
    video_results = _query_and_simplify(
        _create_song_title(song_name, song_artists).lower(), filter="videos"
    )

    # Order video results
    videos = _order_ytm_results(
        video_results, song_name, song_artists, song_album_name, song_duration
    )

    # Merge songs and video results
    results = {**songs, **videos}

    # No matches found
    if not results:
        return None

    result_items = list(results.items())

    # Sort results by highest score
    sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

    # ! In theory, the first 'TUPLE' in sorted_results should have the highest match
    # ! value, we send back only the link
    return sorted_results[0][0]


def _order_ytm_results(
    results: List[dict],
    song_name: str,
    song_artists: List[str],
    song_album_name: str,
    song_duration: int,
) -> dict:

    # Assign an overall avg match value to each result
    links_with_match_value = {}

    for result in results:
        # ! skip results without videoId, this happens if you are country restricted or
        # ! video is unavailabe
        if result == {}:
            continue

        # ! If there are no common words b/w the spotify and YouTube Music name, the song
        # ! is a wrong match (Like Ruelle - Madness being matched to Ruelle - Monster, it
        # ! happens without this conditional)

        # ! most song results on youtube go by $artist - $song_name, so if the spotify name
        # ! has a '-', this function would return True, a common '-' is hardly a 'common
        # ! word', so we get rid of it. Lower-caseing all the inputs is to get rid of the
        # ! troubles that arise from pythons handling of differently cased words, i.e.
        # ! 'Rhino' == 'rhino' is false though the word is same... so we lower-case both
        # ! sentences and replace any hypens(-)
        lower_song_name = song_name.lower()
        lower_result_name = result["name"].lower()

        sentence_words = lower_song_name.replace("-", " ").split(" ")

        common_word = any(
            # ! check for common word
            word != "" and word in lower_result_name
            for word in sentence_words
        )

        # ! if there are no common words, skip result
        if not common_word:
            continue

        # Find artist match
        # ! match  = (no of artist names in result) / (no. of artist names on spotify) * 100
        artist_match_number = 0.0

        # ! we use fuzzy matching because YouTube spellings might be mucked up
        if result["type"] == "song":
            for artist in song_artists:
                artist_match_number += _match_percentage(
                    str(unidecode(artist.lower())), unidecode(result["artist"].lower())
                )
        else:
            # ! i.e if video
            for artist in song_artists:
                # ! something like _match_percentage('rionos', 'aiobahn, rionos Motivation
                # ! (remix)' would return 100, so we're absolutely corrent in matching
                # ! artists to song name.
                artist_match_number += _match_percentage(
                    str(unidecode(artist.lower())), unidecode(result["name"].lower())
                )

            # we didn't find artist in the video title, so we fallback to
            # detecting song artist in the channel name
            # I am not sure if this won't create false positives
            if artist_match_number == 0:
                for artist in song_artists:
                    artist_match_number += _match_percentage(
                        str(unidecode(artist.lower())),
                        unidecode(result["artist"].lower()),
                    )

        artist_match = artist_match_number / len(song_artists)
        if artist_match < 70:
            continue

        song_title = _create_song_title(song_name, song_artists).lower()

        # Find name match and drop results below 60%
        # this needs more testing
        if result["type"] == "song":
            name_match = round(
                _match_percentage(
                    unidecode(result["name"]), str(unidecode(song_name)), 60
                ),
                ndigits=3,
            )
        else:
            name_match = round(
                _match_percentage(
                    unidecode(result["name"]), str(unidecode(song_title)), 60
                ),
                ndigits=3,
            )

        # skip results with name match of 0, these are obviously wrong
        # but can be identified as correct later on due to other factors
        # such as time_match or artist_match
        if name_match == 0:
            continue

        # Find album match
        # ! We assign an arbitrary value of 0 for album match in case of video results
        # ! from YouTube Music
        album_match = 0.0
        album = None

        if result["type"] == "song":
            album = result.get("album")
            if album:
                album_match = _match_percentage(album, song_album_name)

        # Find duration match
        # ! time match = 100 - (delta(duration)**2 / original duration * 100)
        # ! difference in song duration (delta) is usually of the magnitude of a few
        # ! seconds, we need to amplify the delta if it is to have any meaningful impact
        # ! wen we calculate the avg match value
        delta = result["length"] - song_duration
        non_match_value = (delta ** 2) / song_duration * 100

        time_match = 100 - non_match_value

        if result["type"] == "song":
            if album is None:
                # Don't add album_match to average_match if song_name == result and
                # result album name != song_album_name
                average_match = (artist_match + name_match + time_match) / 3
            elif (
                _match_percentage(album.lower(), result["name"].lower()) > 95
                and album.lower() != song_album_name.lower()
            ):
                average_match = (artist_match + name_match + time_match) / 3
                # Add album to average_match if song_name == result album
                # and result album name == song_album_name
            else:
                average_match = (
                    artist_match + album_match + name_match + time_match
                ) / 4
        else:
            average_match = (artist_match + name_match + time_match) / 3
        # Don't add album_match to average_match if we don't have information about the album
        # name in the metadata

        # the results along with the avg Match
        links_with_match_value[result["link"]] = average_match

    return links_with_match_value


def _map_result_to_song_data(result: dict) -> dict:
    song_data = {}
    artists = ", ".join(map(lambda a: a["name"], result["artists"]))
    video_id = result["videoId"]

    # Ignore results without video id
    if video_id is None:
        return {}

    song_data = {
        "name": result["title"],
        "type": result["resultType"],
        "artist": artists,
        "length": _parse_duration(result.get("duration", None)),
        "link": f"https://www.youtube.com/watch?v={video_id}",
        "position": 0,
    }

    album = result.get("album")
    if album:
        song_data["album"] = album["name"]

    return song_data


def _query_and_simplify(search_term: str, filter: str) -> List[dict]:
    """
    `str` `searchTerm` : the search term you would type into YTM's search bar
    `str` `filter` : Filter for item types

    RETURNS `list<dict>`

    For structure of dict, see comment at function declaration
    """

    # ! For dict structure, see end of this function (~ln 268, ln 283) and chill, this
    # ! function ain't soo big, there are plenty of comments and blank lines

    # build and POST a query to YTM
    search_results = ytm_client.search(search_term, filter=filter)

    return list(map(_map_result_to_song_data, search_results))
